import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
OPEN_ROUTER_API_URL = os.getenv("OPEN_ROUTER_API_URL")

# เรียงตามลำดับที่จะลองก่อน-หลัง หากตัวก่อนหน้าล้มเหลว
MODELS = [
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o-mini",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
]

RETRIES_PER_MODEL = 3


def _call_model(model, messages):
    for attempt in range(RETRIES_PER_MODEL):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
                    "HTTP-Referer": OPEN_ROUTER_API_URL,
                    "X-Title": "Mental Health Chatbot"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.4
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"].strip()

            elif response.status_code in [429, 504]:
                time.sleep(2 ** attempt)  # backoff

        except Exception as e:
            print("LLM error:", e)
            time.sleep(2 ** attempt)

    return None


# ไล่เรียกทีละโมเดลใน MODELS จนกว่าจะได้คำตอบ คืน None ถ้าทุกโมเดลล้มเหลว
def get_llm_reply(messages):
    for model in MODELS:
        reply_text = _call_model(model, messages)
        if reply_text:
            print(f" ใช้ model: {model}")
            return reply_text
        print(f" model {model} ล้มเหลว → เปลี่ยนตัว")

    return None
