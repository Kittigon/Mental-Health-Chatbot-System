from flask import Flask, request, jsonify
import requests
from query_postgresql import query_postgresql
from question import DASS_21 , DASS_choices , summaryScore , save_dass_result
from dotenv import load_dotenv
import os
import google.generativeai as genai
from collections import deque
import threading
import time

# เก็บข้อความที่ส่งมาติดๆ กัน
user_message_buffer = {}
user_timers = {}

load_dotenv()

#env 
LineToken = os.getenv("LINE_ACCESS_TOKEN")
llmEndpoint = os.getenv("LOCAL_LLM_ENDPOINT")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

### เก็บ ID , score , ข้อคำถาม
user_states = {}

### ประวัติสนทนา
chat_histories = {}

# จัดรูปแบบประวัติ
def format_history(history):
    return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])

def reply_message(reply_token, message):
    headers = {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

def process_combined_messages(user_id, reply_token):
    buffer = user_message_buffer.get(user_id, deque())

    # รวมข้อความทั้งหมด ไม่จำกัดเวลา
    combined_message = "\n".join([msg for msg, _ in buffer])

    if not combined_message.strip():
        return

    # ล้าง buffer หลังใช้
    user_message_buffer[user_id] = deque()

    # ทำเหมือนเดิมจากโค้ดของคุณ
    query_text = combined_message
    print(f"Processing combined message: {query_text}")
    retrieved_docs = query_postgresql(query_text)
    context = "\n".join([doc[0] for doc in retrieved_docs]) if retrieved_docs else "ไม่มีข้อมูลที่เกี่ยวข้อง"

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    history_text = format_history(chat_histories[user_id])

    prompt = (
        "กรุณาตอบคำถามต่อไปนี้อย่างอบอุ่นและเข้าอกเข้าใจ\n"
        "เน้นตอบตรงคำถามของผู้ใช้เป็นหลัก\n"
        "หากจำเป็น ค่อยอ้างอิงจากประวัติการสนทนา หรือข้อมูลที่เกี่ยวข้อง\n\n"

        f"คำถามของผู้ใช้:\n{query_text}\n\n"
        f"บริบทเพิ่มเติม (จากฐานข้อมูล):\n{context}\n\n"
        f"ประวัติการสนทนา:\n{history_text or 'ยังไม่มีบทสนทนา'}\n\n"

        "กรุณาตอบในรูปแบบที่สุภาพ เป็นกันเอง และไม่ยาวเกินไป\n"
        "หากคุณไม่แน่ใจในคำตอบ โปรดระบุว่าไม่แน่ใจอย่างสุภาพ"
    )

    model = genai.GenerativeModel("gemma-3-27b-it")  
    response = model.generate_content([{"role": "user", "parts": [prompt]}])
    reply_text = response.text.strip() or "ขออภัย ฉันไม่สามารถตอบคำถามนี้ได้ในตอนนี้ค่ะ"

    # บันทึกประวัติ
    chat_histories[user_id].append({"role": "user", "content": query_text})
    chat_histories[user_id].append({"role": "assistant", "content": reply_text})
    chat_histories[user_id] = chat_histories[user_id][-6:]

    # ส่งกลับ
    reply_message(reply_token, reply_text)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    for event in data["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_text = event["message"]["text"].strip()
            reply_token = event["replyToken"]
            user_id = event["source"]["userId"]

            if user_text.lower() in ["ทำแบบประเมิน" , "แบบประเมิน" , "เริ่มแบบประเมิน"]:
                user_states[user_id] = {"index": 0, "scores": []}
                q = DASS_21[0]["text"]
                reply_message(reply_token,  f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nตอบโดยพิมพ์ตัวเลข:\n0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ")
                return jsonify({"status": "ok"})
            
            if user_text.lower() in ["ยกเลิก" ,"ออก", "เลิกทำแบบประเมิน "]:
                if user_id in user_states:
                    del user_states[user_id]
                    reply_message(reply_token ,"คุณได้ยกเลิกการทำแบบประเมินแล้ว หากต้องการเริ่มใหม่ พิมพ์ว่า 'ทำแบบประเมิน' ค่ะ 😊")

            if user_id in user_states:
                state = user_states[user_id]
                index = state["index"]

                if user_text in DASS_choices:
                    score = DASS_choices[user_text]

                    if index < len(DASS_21):  
                        q_type = DASS_21[index]["type"]
                        state["scores"].append({"score": score, "type": q_type})
                        index += 1
                        state["index"] = index

                    if index < len(DASS_21):
                        next_q = DASS_21[index]["text"]
                        reply_message(reply_token, f"{next_q}\n\nตอบโดยพิมพ์ตัวเลข:\n0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ")
                    else:
                        summary = summaryScore(state["scores"])
                        d, a, s = summary['D'], summary['A'], summary['S']
                        d_level, a_level, s_level = save_dass_result(user_id, d, a, s)
                        reply_message(reply_token, 
    f"""🎉 คุณทำแบบประเมิน DASS-21 ครบแล้ว!

📝 คะแนนรวมของคุณ:
• ซึมเศร้า (Depression): {d} → **{d_level}**
• วิตกกังวล (Anxiety): {a} → **{a_level}**
• เครียด (Stress): {s} → **{s_level}**

หากคุณอยากพูดคุยหรือรับคำแนะนำเพิ่มเติม  
สามารถพิมพ์ข้อความเข้ามาได้เลยนะคะ 😊"""
)

                        del user_states[user_id]
                else:
                    reply_message(reply_token, "กรุณาตอบด้วยตัวเลข:\n0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ")
                return jsonify({"status": "ok"})


            query_text = user_text
            retrieved_docs = query_postgresql(query_text)   
            # print(" Retrieved Docs:", retrieved_docs) 

            #แปลง array เป็น string
            context = "\n".join([doc[0] for doc in retrieved_docs])if retrieved_docs else "ไม่มีข้อมูลที่เกี่ยวข้อง"

            #จัดรูปประวิติสนทนา
            if user_id not in chat_histories:
                chat_histories[user_id] = []

            history_text = format_history(chat_histories[user_id])
            # print("history_Text : "+ history_text)

            prompt = (
                "กรุณาตอบคำถามต่อไปนี้อย่างอบอุ่นและเข้าอกเข้าใจ\n"
                "เน้นตอบตรงคำถามของผู้ใช้เป็นหลัก\n"
                "หากจำเป็น ค่อยอ้างอิงจากประวัติการสนทนา หรือข้อมูลที่เกี่ยวข้อง\n\n"

                f" คำถามของผู้ใช้:\n{query_text}\n\n"
                
                f" บริบทเพิ่มเติม (จากฐานข้อมูล):\n{context if context else 'ไม่มีข้อมูลที่เกี่ยวข้อง'}\n\n"
                
                f" ประวัติการสนทนา:\n{history_text if history_text else 'ยังไม่มีบทสนทนา'}\n\n"
                
                "กรุณาตอบในรูปแบบที่สุภาพ เป็นกันเอง และไม่ยาวเกินไป\n"
                "หากคุณไม่แน่ใจในคำตอบ โปรดระบุว่าไม่แน่ใจอย่างสุภาพ"
            )
            
            llm_payload = {
                "model": "test-finetune-2",
                "messages": [
                    {"role": "system", "content": (
                        "คุณคือผู้ช่วยที่อบอุ่น สุภาพ และเห็นอกเห็นใจผู้ใช้\n"
                        "โปรดใช้ภาษาที่เข้าใจง่าย ชัดเจน และให้ความรู้สึกเป็นมิตร\n"
                        "ถ้าผู้ใช้เคยพูดถึงชื่อ ความรู้สึก หรือเรื่องส่วนตัว กรุณาจำไว้และใส่ใจในการตอบ\n"
                        "หากไม่มีข้อมูลเพียงพอ ให้บอกอย่างสุภาพว่าไม่แน่ใจ แทนการคาดเดา"
                    )},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.6
            }

            # llm_response = requests.post(llmEndpoint, json=llm_payload).json()
            # reply_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            # model = genai.GenerativeModel("gemma-3-27b-it")  
            # response = model.generate_content([
            #     {"role": "user", "parts": [prompt]}
            # ])
            # reply_text = response.text.strip()

            # # บันทึกประวัติใน session
            # chat_histories[user_id].append({"role": "user", "content": query_text})
            # chat_histories[user_id].append({"role": "assistant", "content": reply_text})

            # # จำกัดบทสนทนาไม่เกิน 10 ข้อความล่าสุด (5 user  5 assistant)
            # chat_histories[user_id] = chat_histories[user_id][-6:]

            # if not reply_text:
            #     reply_text = "ขออภัย ฉันไม่สามารถตอบคำถามนี้ได้ในตอนนี้ค่ะ"
            # reply_message(reply_token, reply_text)

            #  รวมข้อความก่อนส่งให้ LLM
            if user_id not in user_message_buffer:
                user_message_buffer[user_id] = deque()
            user_message_buffer[user_id].append((user_text, time.time()))

            # ถ้ามี timer รออยู่ ให้ยกเลิกก่อน
            if user_id in user_timers and user_timers[user_id].is_alive():
                user_timers[user_id].cancel()

            # ตั้งเวลา 3 วินาที แล้วรวมข้อความทั้งหมดส่งไป LLM
            user_timers[user_id] = threading.Timer(3.0, process_combined_messages, args=[user_id, reply_token])
            user_timers[user_id].start()

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

