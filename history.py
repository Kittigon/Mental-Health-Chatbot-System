import psycopg2

## สร้างตาราง
# conn = psycopg2.connect(
#     dbname = "mydb",
#     user = "admin",
#     password = "1234" ,
#     host = "localhost" ,
#     port  = "5432"
# )

# cur = conn.cursor()
# cur.execute("""
#     CREATE TABLE chat_history(
#         id SERIAL PRIMARY KEY,
#         chat_id TEXT NOT NUll ,
#         role TEXT NOT NUll,
#         content TEXT NOT NUll,
#         timestamp TIMESTAMPTZ DEFAULT NOW()
#     )
# """)
# conn.commit()
# cur.close()
# conn.close()


def save_message_to_db(chat_id , role , content):
    conn = psycopg2.connect(
        dbname = "mydb",
        user = "admin",
        password = "1234" ,
        host = "localhost" ,
        port  = "5432"
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_history (chat_id , role , content) VALUES (%s ,%s ,%s)" ,
        (chat_id , role , content)
    )
    conn.commit()
    cur.close()
    conn.close()

def load_chat_history(chat_id):
    conn = psycopg2.connect(
        dbname = "mydb",
        user = "admin",
        password = "1234" ,
        host = "localhost" ,
        port  = "5432"
    )
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM chat_history WHERE chat_id = %s ORDER BY id ASC", (chat_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]




#### ไว้ดู format ของการทำ History

# from flask import Flask, request, jsonify
# import requests
# from query_postgresql import query_postgresql
# from history import load_chat_history , save_message_to_db
# from question import DASS_21
# from dotenv import load_dotenv
# import os

# load_dotenv()

# #env 
# LineToken = os.getenv("LINE_ACCESS_TOKEN")
# llmEndpoint = os.getenv("LOCAL_LLM_ENDPOINT")

# app = Flask(__name__)
# user_states = {}

# #จัดรูปแบบประวัติ
# # def format_history(history):
# #     return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])

# def reply_message(reply_token, message):
#     headers = {
#         "Authorization": f"Bearer {LineToken}",
#         "Content-Type": "application/json"
#     }
#     body = {
#         "replyToken": reply_token,
#         "messages": [{"type": "text", "text": message}]
#     }
#     requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

# @app.route("/webhook", methods=["POST"])
# def webhook():
#     data = request.json
#     for event in data["events"]:
#         if event["type"] == "message" and event["message"]["type"] == "text":
#             user_text = event["message"]["text"].strip()
#             reply_token = event["replyToken"]
#             user_id = event["source"]["userId"]

#             
#             # chat_id = user_id
#             # chat_history = load_chat_history(chat_id) 

#             query_text = user_text
#             retrieved_docs = query_postgresql(query_text)   
#             # print(" Retrieved Docs:", retrieved_docs) 

#             #แปลง array เป็น string
#             context = "\n".join([doc[0] for doc in retrieved_docs])if retrieved_docs else "ไม่มีข้อมูลที่เกี่ยวข้อง"

#             ## ประวัติการสนทนา
#             # history_text = format_history(chat_history)
#             # print("History : ",history_text)

#             prompt = f"You are an assistant for question-answering tasks.Use the following pieces of retrieved context to answer the question.If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise question :{query_text} \ncontext:{context}\n\n "
#             # prompt = (
#             # "คุณคือผู้ช่วยที่ฉลาดและเข้าอกเข้าใจผู้อื่น\n"
#             # "กรุณาตอบคำถามของผู้ใช้โดยอิงจากประวัติการสนทนา และข้อมูลที่เกี่ยวข้องเฉพาะเมื่อจำเป็นเท่านั้น\n"
#             # "คุณสามารถใช้ความเข้าใจและความรู้ของคุณเพื่อตอบคำถามอย่างสุภาพและจริงใจ\n"
#             # "หากผู้ใช้เคยบอกชื่อ ความรู้สึก หรือข้อมูลผมวนตัวอื่น ๆ มาก่อน กรุณาจดจำและแสดงความใส่ใจ\n"
#             # "หากไม่รู้คำตอบ ให้บอกอย่างสุภาพว่าไม่แน่ใจ\n\n"
#             # f"ประวัติการสนทนา:\n{history_text if history_text else 'ยังไม่มีบทสนทนา'}\n\n"
#             # f"บริบทที่เกี่ยวข้อง (หากมี):\n{context if context else 'ไม่มีข้อมูลที่เกี่ยวข้อง'}\n\n"
#             # f"ผู้ใช้: {query_text}\nผู้ช่วย:"
#             # )

#             ### LM studio Prompt
#             #     {"role": "system", "content": (
#             #     "คุณคือผู้ช่วยที่อบอุ่น ใส่ใจ และมีความเห็นอกเห็นใจ\n"
#             #     "คุณควรใช้ข้อมูลที่ผู้ใช้เคยพูดไว้ก่อนหน้านี้เพื่อตอบคำถามให้ตรงประเด็น\n"
#             #     "หากผู้ใช้เคยบอกชื่อหรือความรู้สึก กรุณาจดจำและตอบกลับด้วยความเข้าใจ\n"
#             #     "ตอบอย่างสั้น สุภาพ และเป็นมิตร"
#             # )}
            
#             llm_payload = {
#                 "model": "test-finetune-2",
#                 "messages": [
#                     {"role": "system", "content": (
#                     "คุณคือผู้ช่วยที่อบอุ่น ใส่ใจ และมีความเห็นอกเห็นใจ\n"
#                     "คุณควรใช้ข้อมูลที่ผู้ใช้เคยพูดไว้ก่อนหน้านี้เพื่อตอบคำถามให้ตรงประเด็น\n"
#                     "หากผู้ใช้เคยบอกชื่อหรือความรู้สึก กรุณาจดจำและตอบกลับด้วยความเข้าใจ\n"
#                     "ตอบอย่างสั้น สุภาพ และเป็นมิตร"
#                 )},
#                     {"role": "user", "content": prompt}
#                 ],
#                 "max_tokens": 200,
#                 "temperature": 0.6
#             }

#             llm_response = requests.post(llmEndpoint, json=llm_payload).json()
#             reply_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

#             ## บันทึกข้อมูล
#             # save_message_to_db(chat_id, "user", query_text)
#             # save_message_to_db(chat_id, "assistant", reply_text)

#             if not reply_text:
#                 reply_text = "ขออภัย ฉันไม่สามารถตอบคำถามนี้ได้ในตอนนี้ค่ะ"

#             reply_message(reply_token, reply_text)
#     return jsonify({"status": "ok"})

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)

