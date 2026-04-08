import os
import requests
from dotenv import load_dotenv


load_dotenv()

LineToken = os.getenv("LINE_ACCESS_TOKEN")


def push_message(user_id, text):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {LineToken}",
            "Content-Type": "application/json"
        }
        body = {
            "to": user_id,
            "messages": [{"type": "text", "text": text}]
        }
        requests.post(url, headers=headers, json=body)
    except Exception as e:
        print("Error pushing message:", str(e))
