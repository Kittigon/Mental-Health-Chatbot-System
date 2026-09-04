import hmac
import hashlib
import base64
from flask import Flask, request, jsonify
from core.query_postgresql import query_postgresql
from dotenv import load_dotenv
import os
from consent import check_user_consent
from greeting import start_scheduler
from tone import get_tone_from_db
from history import load_chat_history , save_message_to_db
from validation import  is_valid_message_length
import time
from tone_config import TONE_INSTRUCTIONS, DEFAULT_TONE
from safety import detect_suicidal_risk , is_seek_professional_intent
from core.prompt_builder import build_prompt
from core.llm_client import get_llm_reply
from line.line_messaging import reply_message, send_loading_animation
from line.line_ui import send_consent_message
from flows.dass_flow import (
    handle_onboarding_and_consent,
    handle_repeat_confirmation,
    handle_start_request,
    handle_answer,
    get_assessment_context_for_prompt,
)
from flows.settings_flow import handle_consent_postback, handle_settings_message


load_dotenv()

#env
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

app = Flask(__name__)

### เก็บ ID , score , ข้อคำถาม
user_states = {}
user_info = {}
last_warn_time = {}  # {user_id: timestamp}
WARN_COOLDOWN = 10   


### ประวัติสนทนา
chat_histories = {}

# จัดรูปแบบประวัติ
def format_history(history):
    try:
        return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
    except Exception as e:
        print("Error formatting history:", str(e))
        return ""


# ตรวจสอบว่า request มาจาก LINE จริง โดยเทียบ HMAC-SHA256 ของ body กับ X-Line-Signature
def is_valid_line_signature(body, signature):
    if not LINE_CHANNEL_SECRET or not signature:
        return False

    computed_hash = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    computed_signature = base64.b64encode(computed_hash).decode('utf-8')

    return hmac.compare_digest(computed_signature, signature)


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data()

    if not is_valid_line_signature(body, signature):
        print("Invalid Signature: Request ไม่ได้มาจาก LINE")
        return jsonify({"status": "error", "message": "invalid signature"}), 400

    try:
        data = request.get_json()
        for event in data["events"]:        
            user_id = event["source"]["userId"]
            reply_token = event["replyToken"]

            if event["type"] == "follow":
                send_consent_message(reply_token)
                return jsonify({"status": "ok"})
            
            # การจัดการ postback สำหรับความยินยอม
            if event["type"] == "postback":
                    data_postback = event["postback"]["data"]
                    reply_token = event["replyToken"]

                    handle_consent_postback(data_postback, user_id, reply_token)
                    return jsonify({"status": "ok"})
            
            # การจัดการ Text Message
            user_text = ""
            if event["type"] == "message" and event["message"]["type"] == "text":
                user_text = event["message"]["text"].strip()
            # Animetion loading
            send_loading_animation(user_id)

            # ตรวจสอบผู้ใช้ได้เลือกยินยอม หรือ ไม่ยินยอม ก่อนทำการสนทนา
            consent = check_user_consent(user_id)

            if consent is None:  # แค่กรณีไม่มีข้อมูล
                now = time.time()
                last_warn = last_warn_time.get(user_id, 0)

                if now - last_warn > WARN_COOLDOWN:
                    reply_message(reply_token, "หากท่านไม่ทำการเลือกอย่างใดอย่างหนึ่ง แชตบอตจะไม่สามารถใช้งานได้")
                    last_warn_time[user_id] = now

                return jsonify({"status": "ok"})

            if not is_valid_message_length(user_text):
                reply_message(reply_token , "ข้อความของคุณยาวเกินไป กรุณาส่งข้อความที่มีความยาวไม่เกิน 200 ตัวอักษร")
                return jsonify({"status": "ok"})
            
            if handle_settings_message(user_id, user_text, reply_token, user_states):
                return jsonify({"status": "ok"})

            tone = get_tone_from_db(user_id) or DEFAULT_TONE

            if detect_suicidal_risk(user_text):
                tone = "empathetic"

            tone_instruction = TONE_INSTRUCTIONS.get(
                tone,
                TONE_INSTRUCTIONS[DEFAULT_TONE]
            )

            # การทำแบบประเมิน DASS-21 (ขั้นตอนขอความยินยอม/กรอกโปรไฟล์)
            if handle_onboarding_and_consent(user_id, user_text, reply_token, user_states, user_info):
                return jsonify({"status": "ok"})

            ## กรณีทำซ้ำแบบประเมิน
            if user_text == "ยืนยันทำซ้ำ":
                handle_repeat_confirmation(user_id, reply_token, user_states)
                return jsonify({"status": "ok"})

            # เริ่มต้นทำแบบประเมิน DASS-21
            if user_text.lower() in ["ทำแบบประเมิน", "แบบประเมิน", "เริ่มแบบประเมิน"]:
                handle_start_request(user_id, reply_token, user_states)
                return jsonify({"status": "ok"})


            # กรณียกเลิกการทำแบบประเมิน
            if user_text.lower() in ["ยกเลิก" ,"ออก", "เลิกทำแบบประเมิน "]:
                if user_id in user_states:
                    del user_states[user_id]
                    reply_message(reply_token ,"คุณได้ยกเลิกการทำแบบประเมินแล้ว หากต้องการเริ่มใหม่ พิมพ์ว่า 'ทำแบบประเมิน' ได้เลยนะ")
                    return jsonify({"status": "ok"})

            if user_id in user_states and "index" in user_states[user_id]:
                handle_answer(user_id, user_text, reply_token, user_states)
                return jsonify({"status": "ok"})

            assessment_context = get_assessment_context_for_prompt(user_id, user_states)


            query_text = user_text
            retrieved_docs = query_postgresql(query_text)

            #แปลง array เป็น string
            context = "\n".join([doc[0] for doc in retrieved_docs])if retrieved_docs else "ไม่มีข้อมูลที่เกี่ยวข้อง"

            #จัดรูปประวิติสนทนา
            if user_id not in chat_histories:
                history_from_db = load_chat_history(user_id)
                if history_from_db:
                    chat_histories[user_id] = history_from_db[-6:]  # โหลดเฉพาะบทสนทนาล่าสุดไม่เกิน 6 รายการ
                else:
                    chat_histories[user_id] = []

            history_text = format_history(chat_histories[user_id])

            PROFESSIONAL_INFO_CONTEXT = (
                "ข้อมูลสำหรับตอบคำถามเรื่องการเข้าพบผู้เชี่ยวชาญด้านสุขภาพจิต:\n"
                "- สามารถนัดหมายพูดคุยกับศูนย์ให้คำปรึกษามหาวิทยาลัยพะเยา ผ่านทางริชเมนูของ LINE\n"
                "- สายด่วนสุขภาพจิต 1323 (ให้บริการตลอด 24 ชั่วโมง)\n"
                "- โรงพยาบาลหรือสถานพยาบาลใกล้คุณ\n"
                "- ห้ามวินิจฉัยอาการของผู้ใช้\n"
                "- ห้ามบอกว่าผู้ใช้จำเป็นต้องไปพบแพทย์\n"
                "- ใช้ถ้อยคำเชิงทางเลือก ไม่บังคับ และสุภาพ"
            )

            extra_context = None

            if is_seek_professional_intent(user_text):
                extra_context = PROFESSIONAL_INFO_CONTEXT

            combined_extra_context = None

            if assessment_context and extra_context:
                combined_extra_context = assessment_context + "\n\n" + extra_context
            elif assessment_context:
                combined_extra_context = assessment_context
            elif extra_context:
                combined_extra_context = extra_context

            messages = build_prompt(
                user_question=query_text,
                tone_instruction=tone_instruction,
                context=context,
                history=history_text,
                extra_system_context=combined_extra_context
            )

            reply_text = get_llm_reply(messages)

            # fallback สุดท้าย
            if not reply_text:
                reply_text = "ขออภัย ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้งภายหลัง"

            # บันทึกประวัติใน session
            chat_histories[user_id].append({"role": "user", "content": query_text} )
            chat_histories[user_id].append({"role": "assistant", "content": reply_text})

            # ตรวจสอบความยินยอมก่อนบันทึก
            if check_user_consent(user_id):
                #  ถ้ายินยอม -> บันทึกข้อความทั้งสองฝั่ง
                save_message_to_db(user_id, "user", query_text)
                save_message_to_db(user_id, "assistant", reply_text)


            # จำกัดบทสนทนาไม่เกิน 10 ข้อความล่าสุด (5 user  5 assistant)
            chat_histories[user_id] = chat_histories[user_id][-6:]

            if not reply_text:
                reply_text = "ขออภัย ฉันไม่สามารถตอบคำถามนี้ได้ในตอนนี้"
            reply_message(reply_token, reply_text)

        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error in webhook:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    """Endpoint for cron-job to ping and keep the server awake."""
    return "OK", 200

if __name__ == "__main__":
    start_scheduler(test_mode=False)  
    app.run(host="0.0.0.0", port=5000)  

