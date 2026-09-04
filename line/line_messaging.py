import os
import requests
from dotenv import load_dotenv


load_dotenv()

LineToken = os.getenv("LINE_ACCESS_TOKEN")


def _headers():
    return {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
    }


# ส่ง messages (list) กลับไปยัง reply token ที่ได้จาก event
def reply(reply_token, messages):
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers=_headers(),
            json={"replyToken": reply_token, "messages": messages}
        )
    except Exception as e:
        print("Error replying message:", str(e))


# ส่งข้อความตอบกลับแบบข้อความล้วน
def reply_message(reply_token, message):
    reply(reply_token, [{"type": "text", "text": message}])


# ส่ง messages (list) แบบ push ไปหา user_id โดยตรง
def push(user_id, messages):
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=_headers(),
            json={"to": user_id, "messages": messages}
        )
    except Exception as e:
        print("Error pushing message:", str(e))


def push_message(user_id, text):
    push(user_id, [{"type": "text", "text": text}])


# ดึงข้อมูลโปรไฟล์ผู้ใช้
def get_line_profile(user_id):
    try:
        headers = {"Authorization": f"Bearer {LineToken}"}
        url = f"https://api.line.me/v2/bot/profile/{user_id}"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print("Error getting LINE profile:", str(e))
        return None


# ส่ง Loading Animation (แสดงสถานะกำลังพิมพ์)
def send_loading_animation(user_id, loading_seconds=20):
    try:
        url = "https://api.line.me/v2/bot/chat/loading/start"
        body = {
            "chatId": user_id,
            "loadingSeconds": loading_seconds  # กำหนดเวลาแสดงผล (สูงสุด 60 วินาที)
        }
        requests.post(url, headers=_headers(), json=body)
    except Exception as e:
        print("Error sending loading animation:", str(e))
