import hmac
import hashlib
import base64
from flask import Flask, request, jsonify , abort
import requests
from query_postgresql import query_postgresql 
from question import DASS_21 , DASS_choices , summaryScore , save_dass_result , get_level , send_notification , check_dass_cooldown , log_dass_taken ,can_use_override , save_dass_answer 
from dotenv import load_dotenv
import os
import google.generativeai as genai
from consent import  save_consent_to_db , check_user_consent , handle_consent , save_profile , check_profile
from greeting import  save_greeting_permission , start_scheduler , get_user_to_greet
from tone import  save_tone_to_db , get_tone_from_db
from history import load_chat_history , save_message_to_db
from validation import  is_valid_fullname , is_valid_phone , is_valid_message_length , is_valid_student_id
import time
import json
from tone_config import TONE_INSTRUCTIONS, DEFAULT_TONE
from safety import detect_suicidal_risk , is_seek_professional_intent
from prompt_builder import build_prompt
from line_messaging import push_message
# from zai import ZaiClient


load_dotenv()

#env 
LineToken = os.getenv("LINE_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
llmEndpoint = os.getenv("LOCAL_LLM_ENDPOINT")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
OPEN_ROUTER_API_URL = os.getenv("OPEN_ROUTER_API_URL")
# ZAI_API_KEY = os.getenv("ZAI_API_KEY")
# ZAI_API_URL = os.getenv("ZAI_API_URL")


# zai_client = ZaiClient(api_key=ZAI_API_KEY)


app = Flask(__name__)

### เก็บ ID , score , ข้อคำถาม
user_states = {}
user_info = {}
last_warn_time = {}  # {user_id: timestamp}
WARN_COOLDOWN = 10   


### ประวัติสนทนา
chat_histories = {}

def send_dass_repeat(reply_token, message):
    headers = {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
    }

    body = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message,
                "quickReply": {
                    "items": [
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "🔁 ยืนยันทำซ้ำ",
                                "text": "ยืนยันทำซ้ำ"
                            }
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "💬 พูดคุยกับบอต",
                                "text": "อยากคุยต่อ"
                            }
                        }
                    ]
                }
            }
        ]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=body
    )

def send_dass_consent(reply_token):
    headers = {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
    }

    body = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": (
                    "ก่อนเริ่มแบบประเมิน DASS-21\n"
                    "ขอความยินยอมในการบันทึกผลประเมิน\n\n"
                    "ไม่ว่าคุณจะเลือกแบบใด สามารถทำแบบประเมินได้เหมือนเดิม\n\n"
                    "กรุณาเลือกตัวเลือกด้านล่าง:"
                ),
                "quickReply": {
                    "items": [
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "ยินยอม (บันทึกผล)",
                                "text": "ยินยอมบันทึกผล"
                            }
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "ไม่ยินยอม (ไม่บันทึก)",
                                "text": "ไม่ยินยอมบันทึกผล"
                            }
                        }
                    ]
                }
            }
        ]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=body
    )

# จัดรูปแบบประวัติ
def format_history(history):
    try:
        return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
    except Exception as e:
        print("Error formatting history:", str(e))
        return ""

# ส่งข้อความตอบกลับ
def reply_message(reply_token, message):
    try:
        headers = {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
        }
        body = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": message}]
        }
        requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)
    except Exception as e:
        print("Error replying message:", str(e))

# ดึงข้อมูลโปรไฟล์ผู้ใช้
def get_line_profile(user_id):
    try:
        headers = {
        "Authorization": f"Bearer {LineToken}"
        }
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
        headers = {
            "Authorization": f"Bearer {LineToken}",
            "Content-Type": "application/json"
        }
        body = {
            "chatId": user_id,
            "loadingSeconds": loading_seconds  # กำหนดเวลาแสดงผล (สูงสุด 60 วินาที)
        }
        requests.post(url, headers=headers, json=body)
    except Exception as e:
        print("Error sending loading animation:", str(e))

# ส่งข้อความขอความยินยอม
def send_consent_message(reply_token):
    try:
        headers = {
            "Authorization": f"Bearer {LineToken}",
            "Content-Type": "application/json"
        }

        flex_body = {
            "type": "flex",
            "altText": "การยินยอมในการเก็บข้อมูลการสนทนา",
            "contents": {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "การยินยอมในการเก็บข้อมูลการสนทนา",
                            "weight": "bold",
                            "size": "md",
                            "align": "center",
                            "color": "#1E88E5"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "wrap": True,
                            "size": "sm",
                            "color": "#333333",
                            "text": (
                                "แชตบอตขอความยินยอมในการเก็บข้อมูลการสนทนา "
                                "เพื่อใช้ในการปรับปรุงคุณภาพการให้คำแนะนำ "
                                "และการตั้งค่าประสบการณ์การใช้งาน เช่น โทนการสนทนาและการทักทายอัตโนมัติ\n\n"

                                "🔐 ข้อมูลจะถูกจัดเก็บอย่างปลอดภัย "
                                "และจะไม่ถูกเปิดเผยต่อบุคคลภายนอกโดยไม่ได้รับอนุญาต\n\n"

                                "📌 หากคุณไม่ยินยอม คุณยังสามารถ:\n"
                                "• พูดคุยกับแชตบอตได้ตามปกติ\n"
                                "• ทำแบบประเมินสุขภาพจิต DASS-21 ได้ (โดยจะมีการขอความยินยอมแยกต่างหาก)\n"
                                "• นัดหมายผู้เชี่ยวชาญด้านสุขภาพจิตได้\n\n"

                                "คุณสามารถเปลี่ยนแปลงการยินยอมนี้ได้ตลอดเวลาในเมนูการตั้งค่า"
                            )
                        },
                        {"type": "separator", "margin": "md"},
                        {
                            "type": "text",
                            "text": "กรุณาเลือก:",
                            "margin": "md",
                            "weight": "bold",
                            "size": "sm"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#4CAF50",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "ยินยอม (บันทึกแชต)",
                                "data": "consent_chat=accept"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "margin": "md",
                            "action": {
                                "type": "postback",
                                "label": "ไม่ยินยอม (ไม่บันทึก)",
                                "data": "consent_chat=decline"
                            }
                        }
                    ]
                }
            }
        }

        body = {
            "replyToken": reply_token,
            "messages": [flex_body]
        }

        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers=headers,
            json=body
        )

    except Exception as e:
        print("Error sending consent message:", str(e))

# ส่งเมนูการตั้งค่า
def send_settings_main(reply_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LineToken}"
    }

    # ===== Theme =====
    primary_color = "#2C3E50"   # สีปุ่มทั้งหมด
    bg_light = "#E8F0FE"        # สีพื้นหลัง
    card_bg = "#FFFFFF"        # สีการ์ดอธิบาย

    flex = {
        "type": "flex",
        "altText": "เมนูการตั้งค่า",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "20px",
                "spacing": "lg",
                "backgroundColor": bg_light,
                "contents": [

                    # ===== Header =====
                    {
                        "type": "text",
                        "text": "⚙️ การตั้งค่า",
                        "size": "xl",
                        "weight": "bold",
                        "color": primary_color
                    },

                    # ===== Consent Description Card =====
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": card_bg,
                        "paddingAll": "15px",
                        "cornerRadius": "12px",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "การยินยอมให้บันทึกการสนทนา",
                                "weight": "bold",
                                "color": primary_color
                            },
                            {
                                "type": "text",
                                "text": (
                                    "แชตบอตจะจัดเก็บข้อความสนทนาเพื่อนำไปพัฒนา "
                                    "คุณภาพการให้บริการและการดูแลผู้ใช้งาน "
                                    "โดยข้อมูลจะถูกเก็บรักษาอย่างปลอดภัยและเป็นความลับ"
                                    "ท่านสามารถเปลี่ยนแปลงการยินยอมนี้ได้ตลอดเวลา"
                                ),
                                "size": "sm",
                                "wrap": True,
                                "color": "#555555"
                            }
                        ]
                    },

                    # ===== Separator =====
                    {
                        "type": "separator"
                    },

                    # ===== Consent Button =====
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "การยินยอม",
                            "text": "การยินยอม"
                        }
                    },

                    # ===== Separator =====
                    {
                        "type": "separator",
                        "margin": "lg"
                    },

                    # ===== Other Settings Header =====
                    {
                        "type": "text",
                        "text": "การตั้งค่าอื่น ๆ",
                        "weight": "bold",
                        "color": primary_color
                    },

                    # ===== Auto Greeting =====
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "ทักทายอัตโนมัติ",
                            "text": "ทักทายอัตโนมัติ"
                        }
                    },

                    # ===== Chat Style =====
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "สไตล์การสนทนา",
                            "text": "สไตล์การสนทนา"
                        }
                    }
                ]
            }
        }
    }

    payload = {
        "replyToken": reply_token,
        "messages": [flex]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=payload
    )

# ส่งเมนูสลับการตั้งค่า
def send_toggle_settings(reply_token, label, status, toggle_cmd):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LineToken}"
    }

    primary_color = "#2C3E50"
    bg_light = "#E8F0FE"

    flex = {
        "type": "flex",
        "altText": label,
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "20px",
                "spacing": "lg",
                "backgroundColor": bg_light,
                "contents": [
                    {
                        "type": "text",
                        "text": f"⚙️ {label}",
                        "size": "xl",
                        "weight": "bold",
                        "color": primary_color
                    },
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "text",
                        "text": f"สถานะปัจจุบัน: {'เปิด 🔵' if status else 'ปิด ⚪'}",
                        "size": "lg",
                        "weight": "bold",
                        "color": primary_color
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "สลับสถานะ",
                            "text": toggle_cmd
                        }
                    }
                ]
            }
        }
    }

    payload = {"replyToken": reply_token, "messages": [flex]}
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

# ส่งเมนูสไตล์การสนทนา
def send_style_menu(reply_token, current_style):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LineToken}"
    }

    # ===== Theme (ตรงกับ settings อื่น) =====
    primary_color = "#2C3E50"
    bg_light = "#E8F0FE"
    card_bg = "#FFFFFF"

    flex = {
        "type": "flex",
        "altText": "สไตล์การสนทนา",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "lg",
                "paddingAll": "20px",
                "backgroundColor": bg_light,
                "contents": [

                    # ===== Header =====
                    {
                        "type": "text",
                        "text": "🎨 สไตล์การสนทนา",
                        "size": "xl",
                        "weight": "bold",
                        "color": primary_color
                    },

                    # ===== Current Style Card =====
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": card_bg,
                        "paddingAll": "15px",
                        "cornerRadius": "12px",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "สไตล์ปัจจุบัน",
                                "weight": "bold",
                                "color": primary_color
                            },
                            {
                                "type": "text",
                                "text": f"🗣️ {current_style}",
                                "size": "lg",
                                "weight": "bold",
                                "color": "#555555"
                            }
                        ]
                    },

                    # ===== Separator =====
                    {
                        "type": "separator"
                    },

                    # ===== Style Buttons =====
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "ทางการ",
                            "text": "ทางการ"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "กึ่งทางการ",
                            "text": "กึ่งทางการ"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "เป็นกันเอง",
                            "text": "เป็นกันเอง"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "วัยรุ่น",
                            "text": "วัยรุ่น"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": primary_color,
                        "action": {
                            "type": "message",
                            "label": "อบอุ่นและเข้าอกเข้าใจ",
                            "text": "อบอุ่นและเข้าอกเข้าใจ"
                        }
                    }
                ]
            }
        }
    }

    payload = {
        "replyToken": reply_token,
        "messages": [flex]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=payload
    )

# ส่งผลการประเมิน DASS-21 แบบ Flex Message
def send_dass_result_flex(reply_token, d, a, s, d_level, a_level, s_level): 
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LineToken}"
    }

    # ระดับ → emoji + สี
    LEVEL_STYLE = {
        "ปกติ":      {"emoji": "🟢", "color": "#2ECC71"},
        "เล็กน้อย":  {"emoji": "🟡", "color": "#F1C40F"},
        "ปานกลาง":   {"emoji": "🟠", "color": "#E67E22"},
        "รุนแรง":    {"emoji": "🔴", "color": "#E74C3C"},
        "รุนแรงมาก": {"emoji": "🟣", "color": "#8E44AD"}
    }

    # ข้อความแนะนำตามระดับ (ใช้ภาษาที่ไม่ตีตรา)
    def advice_by_level(level):
        if level == "ปกติ":
            return "ระดับนี้ถือว่าอยู่ในเกณฑ์ปกติ ดูแลตัวเองต่อเนื่องแบบนี้ถือว่าดีมากนะ"
        elif level == "เล็กน้อย":
            return "อาจมีความตึงเครียดเล็กน้อย ลองพักผ่อนหรือหากิจกรรมผ่อนคลายดูนะ"
        elif level == "ปานกลาง":
            return "หากรู้สึกไม่สบายใจบ่อยขึ้น การได้พูดคุยกับใครสักคนอาจช่วยได้นะ"
        elif level == "รุนแรง":
            return "ระดับนี้อาจส่งผลกับชีวิตประจำวัน หากสะดวก ลองพิจารณาขอคำปรึกษาจากผู้เชี่ยวชาญดูนะ"
        else:  # รุนแรงมาก
            return "คุณไม่จำเป็นต้องรับมือกับเรื่องนี้คนเดียว หากพร้อม การพูดคุยกับผู้เชี่ยวชาญสามารถช่วยได้มาก"

    # สร้างแถวผลแต่ละหมวด
    def result_row(label, score, level):
        style = LEVEL_STYLE.get(level, {"emoji": "", "color": "#000000"})
        return {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "flex": 4,
                    "size": "sm",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": str(score),
                    "flex": 1,
                    "size": "sm",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": f"{style['emoji']} {level}",
                    "flex": 3,
                    "size": "sm",
                    "align": "end",
                    "weight": "bold",
                    "color": style["color"]
                }
            ]
        }

    # เช็คว่ามีระดับรุนแรงหรือไม่
    has_severe = any(lv in ["รุนแรง", "รุนแรงมาก"] for lv in [d_level, a_level, s_level])

    # กล่องเตือน (แสดงเฉพาะกรณีรุนแรง)
    warning_box = {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#FDEDEC",
        "paddingAll": "12px",
        "margin": "md",
        "contents": [
            {
                "type": "text",
                "text": "⚠️ ข้อควรทราบ",
                "weight": "bold",
                "color": "#C0392B"
            },
            {
                "type": "text",
                "wrap": True,
                "size": "sm",
                "text": (
                    "ผลการประเมินนี้เป็นเพียงการประเมินเบื้องต้น "
                    "ไม่ใช่การวินิจฉัยทางการแพทย์ "
                    "หากคุณรู้สึกไม่สบายใจ การพูดคุยกับผู้เชี่ยวชาญอาจช่วยได้"
                )
            }
        ]
    }

    # Flex message หลัก
    contents = [
        {
            "type": "text",
            "text": "📊 ผลการประเมิน DASS-21",
            "size": "xl",
            "weight": "bold"
        },
        {"type": "separator"},
        result_row("ซึมเศร้า (Depression)", d, d_level),
        result_row("วิตกกังวล (Anxiety)", a, a_level),
        result_row("ความเครียด (Stress)", s, s_level),
        {"type": "separator"},
        {
            "type": "text",
            "wrap": True,
            "size": "sm",
            "color": "#555555",
            "text": f"💬 คำแนะนำโดยรวม:\n{advice_by_level(max([d_level, a_level, s_level], key=lambda x: ['ปกติ','เล็กน้อย','ปานกลาง','รุนแรง','รุนแรงมาก'].index(x)))}"
        }
    ]

    if has_severe:
        contents.append(warning_box)

    flex_body = {
        "type": "flex",
        "altText": "ผลการประเมิน DASS-21",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#2C3E50",
                        "action": {
                            "type": "message",
                            "label": "💬 พูดคุยกับบอตต่อ",
                            "text": "อยากคุยต่อ"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "uri",
                            "label": "📅 นัดผู้เชี่ยวชาญ",
                            "uri": "https://appointment-website-nine.vercel.app/login"
                        }
                    }
                ]
            }
        }
    }

    payload = {
        "replyToken": reply_token,
        "messages": [flex_body]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=payload
    )

# ส่งคำถาม DASS-21 พร้อมตัวเลือกแบบ Quick Reply
def reply_dass_question(reply_token, question_text):
    headers = {
        "Authorization": f"Bearer {LineToken}",
        "Content-Type": "application/json"
    }

    body = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": f"{question_text}\n\nกรุณาเลือกคำตอบ:",
                "quickReply": {
                    "items": [
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "0 ไม่เคย",
                                "text": "0"
                            }
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "1 บางครั้ง",
                                "text": "1"
                            }
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "2 บ่อยครั้ง",
                                "text": "2"
                            }
                        },
                        {
                            "type": "action",
                            "action": {
                                "type": "message",
                                "label": "3 เป็นประจำ",
                                "text": "3"
                            }
                        }
                    ]
                }
            }
        ]
    }

    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=body
    )


@app.route("/webhook", methods=["POST"])
def webhook():

    # signature = request.headers.get('X-Line-Signature', '')
    # body = request.get_data(as_text=True) 

    # # print("Body:", body)
    # # print("Signature:", signature)

    # try:
    #     hash = hmac.new(
    #         LINE_CHANNEL_SECRET.encode('utf-8'),
    #         body.encode('utf-8'),
    #         hashlib.sha256
    #     ).digest()
    #     check_signature = base64.b64encode(hash).decode('utf-8')

    #     if check_signature != signature:
    #         print("Invalid Signature: Request ไม่ได้มาจาก LINE")
    #         abort(400) # ตัดการทำงานทันที
    # except Exception as e:
    #     print("Signature Error:", e)
    #     abort(400)

    try:
        data = request.json
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

                    if data_postback == "consent_chat=accept":
                        handle_consent(user_id, True, reply_token)
                    elif data_postback == "consent_chat=decline":
                        handle_consent(user_id, False, reply_token)
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
            
            if user_text == "การตั้งค่า":
                send_settings_main(reply_token)
                return "ok"

            elif user_text == "การยินยอม":
                status = check_user_consent(user_id)
                send_toggle_settings(reply_token, "การยินยอม", status, "สลับสถานะการยินยอม")
                return "ok"

            elif user_text == "ทักทายอัตโนมัติ":
                status = get_user_to_greet(user_id)
                send_toggle_settings(reply_token, "ทักทายอัตโนมัติ", status, "สลับสถานะทักทายอัตโนมัติ")
                return "ok"

            elif user_text == "สไตล์การสนทนา":
                tone_key = get_tone_from_db(user_id) or DEFAULT_TONE

                tone_label_map = {
                    "formal": "ทางการ",
                    "semi_formal": "กึ่งทางการ",
                    "friendly": "เป็นกันเอง",
                    "teen": "วัยรุ่น",
                    "empathetic": "อบอุ่นและเข้าอกเข้าใจ"
                }

                current_style = tone_label_map.get(tone_key, "ค่าเริ่มต้น")
                send_style_menu(reply_token, current_style)
                return "ok"
            
            style_map = {
                "ทางการ": "formal",
                "กึ่งทางการ": "semi_formal",
                "เป็นกันเอง": "friendly",
                "วัยรุ่น": "teen",
                "อบอุ่นและเข้าอกเข้าใจ": "empathetic"
            }

            # เมื่อเลือกสไตล์
            if user_text in style_map:
                english_style = style_map[user_text]
                save_tone_to_db(user_id, english_style)
                reply_message(reply_token, f"อัปเดตสไตล์การสนทนาแล้ว ({user_text}) ")
                return "ok"

            
            # สลับการตั้งค่าการยินยอม
            elif user_text == "สลับสถานะการยินยอม":
                current_status = check_user_consent(user_id)
                new_status = not current_status
                handle_consent(user_id, new_status , reply_token)
                reply_message(reply_token, "อัปเดตสถานะการยินยอมแล้ว")
                return "ok"
            
            # สลับการตั้งค่าทักทายอัตโนมัติ
            elif user_text == "สลับสถานะทักทายอัตโนมัติ":
                current_status = get_user_to_greet(user_id)
                new_status = not current_status
                save_greeting_permission(user_id, new_status)
                reply_message(reply_token, "อัปเดตโหมดทักทายอัตโนมัติแล้ว")
                return "ok"


            if user_text.lower() in ["คู่มือการใช้งาน", "help", "menu"]:
                help_message = (
                    "คู่มือการใช้งานแชตบอตสุขภาพจิต\n\n" 
                    
                    "ข้อควรทราบฉุกเฉิน\n"
                    "หากพบว่าตนเองมีความเสี่ยงหรือกำลังอยู่ในอันตราย กรุณาติดต่อสายด่วนสุขภาพจิต 1323 "
                    "หรือโรงพยาบาลใกล้บ้านทันที ระบบนี้ไม่สามารถให้ความช่วยเหลือในภาวะฉุกเฉินได้\n\n"

                    "1. การพูดคุยทั่วไป\n"
                    "💬 สามารถพิมพ์เพื่อพูดคุย ระบายความรู้สึก หรือปรึกษาปัญหาเบื้องต้นได้\n"
                    "🌱 ระบบจะพยายามทำความเข้าใจและให้คำแนะนำอย่างอ่อนโยนในระดับเบื้องต้น\n"
                    "⚠️ หมายเหตุ: ระบบนี้ไม่สามารถทดแทนการวินิจฉัยหรือคำปรึกษาจากผู้เชี่ยวชาญได้\n\n"

                    "2. การยินยอมในการเก็บข้อมูล\n"
                    "📝 พิมพ์ 'การยินยอม' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง เพื่อดูรายละเอียดและให้ความยินยอม\n"
                    "🔒 หากยินยอม ระบบจะสามารถใช้ฟีเจอร์เพิ่มเติม เช่น จดจำข้อมูลผู้ใช้งาน บันทึกผลประเมิน "
                    "และตั้งค่าโทนการสนทนาเฉพาะบุคคล\n"
                    "🚫 หากไม่ยินยอม ยังสามารถใช้งานทั่วไปได้ แต่ระบบจะไม่บันทึกข้อมูลใดๆ\n\n"

                    "3. การถอนความยินยอม\n"
                    "❌ พิมพ์ 'ถอนความยินยอม' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง ได้ทุกเมื่อ\n"
                    "🗑️ ระบบจะลบข้อมูลส่วนบุคคลที่เคยบันทึก เช่น ประวัติสนทนาและผลการประเมินDASS-21"
                    "🔄 พร้อมปิดการใช้งานฟีเจอร์ส่วนบุคคลทั้งหมด\n\n"

                    "4. การทำแบบประเมิน DASS-21\n"
                    "🧠 พิมพ์ 'ทำแบบประเมิน' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง เพื่อเริ่มต้น\n"
                    "📊 แบบประเมินนี้มี 21 ข้อ สำหรับประเมินระดับความเครียด ความวิตกกังวล และภาวะซึมเศร้า "
                    "ในระดับเบื้องต้น\n"
                    "💾 หากยินยอม ผลจะถูกบันทึกไว้เพื่อติดตามภายหลัง\n"
                    "👀 หากไม่ยินยอม ระบบจะแสดงผลให้ทันที แต่จะไม่บันทึกไว้\n\n"

                    "5. การตั้งค่าโทนเสียงของบอท (ต้องยินยอม)\n"
                    "🎨 พิมพ์ 'ตั้งค่าโทน' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง เพื่อเลือกโทนการสนทนา เช่น อบอุ่น เป็นกันเอง หรือเป็นทางการ\n"
                    "💾 การตั้งค่าจะถูกบันทึกไว้หากมีการยินยอม\n\n"

                    "6. การทักทายอัตโนมัติ (ต้องยินยอม)\n"
                    "🤖 พิมพ์ 'ทักทายอัตโนมัติ' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง เพื่อเปิดหรือปิดฟังก์ชันนี้\n"
                    "👋 หากเปิด ระบบจะทักทายผู้ใช้งานเมื่อกลับมาใช้งานอีกครั้ง\n\n"

                    "7. การนัดหมายผู้เชี่ยวชาญ\n"
                    "📅 พิมพ์ 'นัดหมายผู้เชี่ยวชาญ' หรือเลือกการตั้งค่าแชตบอตจากเมนูด้านล่าง เพื่อเริ่มกระบวนการ\n"
                    "🧑‍⚕️ ระบบจะขอข้อมูลที่จำเป็น เช่น ชื่อ นามสกุล หมายเลขติดต่อ และวันเวลาที่สะดวก\n"
                    "📞 หลังกรอกข้อมูล เจ้าหน้าที่จะติดต่อกลับเพื่อยืนยันการนัดหมาย\n\n"

                )
                reply_message(reply_token, help_message)
                return jsonify({"status": "ok"})

            # การตั้งค่าโทนเสียง
            # if user_text.lower() in ["ตั้งค่าโทน", "เปลี่ยนโทนเสียง", "เลือกโทน"]:
            #     if not check_user_consent(user_id):
            #         reply_message(reply_token, "ก่อนอื่น คุณต้องให้ความยินยอมในการเก็บข้อมูลส่วนบุคคลก่อน 🙏")
            #         return jsonify({"status": "ok"})
                
            #     reply_message(reply_token, 
            #             "กรุณาเลือกโทนภาษาที่ต้องการให้ฉันพูดด้วย\n\n"
            #             "1. ทางการ\n"
            #             "2. กึ่งทางการ\n"
            #             "3. เป็นกันเอง\n"
            #             "4. วัยรุ่น\n"
            #             "5. อบอุ่นและเข้าอกเข้าใจ"
            #         )
            #     user_states[user_id] = {"set_tone": True}
            #     return jsonify({"status": "ok"})

            # if user_id in user_states and user_states[user_id].get("set_tone"):
            #     tone_map = {
            #         "1": "formal",  
            #         "2": "semi_formal",
            #         "3": "friendly",
            #         "4": "teen",
            #         "5": "empathetic"
            #     }

            #     tone_name_map = {
            #         "1": "ทางการ",
            #         "2": "กึ่งทางการ",
            #         "3": "เป็นกันเอง",
            #         "4": "วัยรุ่น",
            #         "5": "อบอุ่นและเข้าอกเข้าใจ"
            #         }
                
            #     if user_text in tone_map:
            #         selected_tone = tone_map[user_text]
            #         selected_tone_name = tone_name_map[user_text]
            #         save_tone_to_db(user_id, selected_tone)
            #         reply_message(reply_token, f"ตั้งค่าโทนเสียงเป็น '{selected_tone_name}' เรียบร้อยแล้ว ")
            #         user_states[user_id].pop("set_tone", None)
            #     else:
            #         reply_message(reply_token, "กรุณาพิมพ์หมายเลข 1 ถึง 5 เพื่อเลือกโทนภาษา ")
            #     return jsonify({"status": "ok"})

            tone = get_tone_from_db(user_id) or DEFAULT_TONE

            if detect_suicidal_risk(user_text):
                tone = "empathetic"

            tone_instruction = TONE_INSTRUCTIONS.get(
                tone,
                TONE_INSTRUCTIONS[DEFAULT_TONE]
            )

            # การตั้งค่าทักทายอัตโนมัติ
            if user_text.lower() in ["ทักทายอัตโนมัติ", "ตั้งค่าทักทายอัตโนมัติ"]:
                if not check_user_consent(user_id):
                    reply_message(reply_token, "ก่อนอื่นคุณต้องให้ความยินยอมในการเก็บข้อมูลส่วนบุคคลก่อน🙏")
                    # send_consent_message(reply_token)
                    return jsonify({"status": "ok"})
                else:
                    user_states[user_id] = {"ask_greeting": True}
                    reply_message(reply_token, 
                        "คุณต้องการให้แชตบอตทักทายคุณโดยอัตโนมัติเมื่อเริ่มสนทนาหรือไม่?\n"
                        "กรุณาพิมพ์:\n 1 = ใช่\n 2 = ไม่")
                    return jsonify({"status": "ok"})
            if user_id in user_states and user_states[user_id].get("ask_greeting"):
                if user_text in ["1", "ใช่", "yes"]:
                    save_greeting_permission(user_id, True)
                    reply_message(reply_token, "คุณได้อนุญาตให้แชตบอตทักทายคุณเรียบร้อยแล้ว💛")
                    user_states[user_id].pop("ask_greeting", None)
                elif user_text in ["2", "ไม่", "no"]:
                    save_greeting_permission(user_id, False)
                    reply_message(reply_token, "คุณไม่ได้อนุญาตให้แชตบอตทักทายคุณ 💙")
                    user_states[user_id].pop("ask_greeting", None)
                else:
                    reply_message(reply_token, "กรุณาตอบด้วย 1 = ใช่ หรือ 2 = ไม่")
                return jsonify({"status": "ok"})
            
            # การยินยอมและถอนความยินยอม
            if user_text.lower() in ["การยินยอม", "consent" , "ข้อตกลงในการใช้งาน"]:
                send_consent_message(reply_token)
                return jsonify({"status": "ok"})
            if user_text.lower() in ["ถอนความยินยอม", "ยกเลิกการยินยอม"]:
                save_consent_to_db(user_id, False)
                reply_message(reply_token, "คุณได้ถอนความยินยอมแล้ว ข้อมูลของคุณจะไม่ถูกเก็บต่อไป 🩵")
                return jsonify({"status": "ok"})
            
            if user_text.lower() in ["นัดหมายผู้เชี่ยวชาญ", "จองคิว", "นัดหมาย"]:
                reply_message(reply_token, "คุณสามารถนัดหมายผู้เชี่ยวชาญได้ที่นี่: https://appointment-website-nine.vercel.app/login")
                return jsonify({"status": "ok"})
            
            # การทำแบบประเมิน DASS-21 
            if user_id in user_states:
                if user_id in user_states and user_states[user_id].get("awaiting_dass_consent"):
                    if user_text == "ยินยอมบันทึกผล":  # ยินยอมบันทึก DASS
                        user_states[user_id].pop("awaiting_dass_consent", None)
                        user_states[user_id]["dass_consent"] = True

                        if not check_profile(user_id):
                            user_states[user_id]["awaiting_name"] = True
                            reply_message(
                                reply_token,
                                "ก่อนเริ่มแบบประเมิน กรุณากรอกข้อมูลเล็กน้อย\n\nพิมพ์ชื่อ-นามสกุลของคุณ:"
                            )
                        # ต้องกรอกข้อมูลส่วนตัวก่อน
                            return jsonify({"status": "ok"})

                        # ถ้ามี profile แล้ว → เริ่ม DASS ได้เลย
                        user_states[user_id].update({"index": 0, "scores": []})

                        #  แสดงคำถามข้อแรกทันที
                        q = DASS_21[0]["text"]
                        # reply_message(
                        #     reply_token,
                        #     f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\n"
                        #     "0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ\n\n"
                        #     "หากต้องการยกเลิก พิมพ์ว่า 'ยกเลิก'"
                        # )

                        reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")

                        return jsonify({"status": "ok"})

                    elif user_text == "ไม่ยินยอมบันทึกผล":  # ไม่ยินยอมบันทึก
                        user_states[user_id].pop("awaiting_dass_consent", None)
                        user_states[user_id]["dass_consent"] = False
                        user_states[user_id]["index"] = 0
                        user_states[user_id]["scores"] = []

                        #  แสดงคำถามข้อแรกทันที
                        q = DASS_21[0]["text"]
                        # reply_message(
                        #     reply_token,
                        #     f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\n"
                        #     "0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ\n\n"
                        #     "หากต้องการยกเลิก พิมพ์ว่า 'ยกเลิก'"
                        # )

                        reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")

                        return jsonify({"status": "ok"})
                    else:
                        reply_message(reply_token, "กรุณาเลือกจากปุ่มที่แสดงด้านล่างเท่านั้น")
                        return jsonify({"status": "ok"})
                    
                # --- อยู่ในสถานะรอชื่อ ---
                if user_states[user_id].get("awaiting_name"):
                    if not is_valid_fullname(user_text):
                        reply_message(
                            reply_token,
                            "กรุณากรอกชื่อและนามสกุลให้ถูกต้อง (ตัวอักษรไทย และต้องมีอย่างน้อย 2 คำ ตัวอย่าง: สมชาย ใจดี)"
                        )
                        return jsonify({"status": "ok"})
                    user_info[user_id] = {"name": user_text.strip()}
                    user_states[user_id].pop("awaiting_name", None)
                    user_states[user_id]["awaiting_student_id"] = True
                    reply_message(reply_token, "กรุณากรอกรหัสนักศึกษา 8 หลัก: ")
                    return jsonify({"status": "ok"})
                
                # --- อยู่ในสถานะรอรหัสนักศึกษา ---
                if user_states[user_id].get("awaiting_student_id"):
                    if not is_valid_student_id(user_text):
                        reply_message(reply_token, "กรุณากรอกรหัสนักศึกษาให้ถูกต้อง (ต้องเป็นตัวเลข 8 หลัก)")
                        return jsonify({"status": "ok"})

                    # บันทึกรหัสนักศึกษา
                    user_info[user_id]["student_id"] = user_text.strip()

                    # ไปต่อ → ขอเบอร์โทร
                    user_states[user_id].pop("awaiting_student_id", None)
                    user_states[user_id]["awaiting_phone"] = True
                    reply_message(reply_token, "กรุณาพิมพ์เบอร์โทรศัพท์ของคุณ (ตัวเลขเท่านั้น):")
                    return jsonify({"status": "ok"})

                # --- อยู่ในสถานะรอเบอร์ ---
                if user_states[user_id].get("awaiting_phone"):
                    if not is_valid_phone(user_text):
                        reply_message(reply_token, "กรุณากรอกเบอร์โทรให้ถูกต้อง (ตัวเลข 10 หลัก และขึ้นต้นด้วย 0 ตัวอย่าง: 0812345678)")
                        return jsonify({"status":"ok"})
                    if not user_text.isdigit() or len(user_text) < 9:
                        reply_message(reply_token, "กรุณากรอกเบอร์โทรให้ถูกต้อง (10 หลัก)")
                        return jsonify({"status": "ok"})
                
                    # บันทึกข้อมูล
                    user_info[user_id]["phone"] = user_text.strip()
                    save_profile(user_id, user_info[user_id]["name"],
                                user_info[user_id]["phone"],
                                user_info[user_id]["student_id"])

                    # เคลียร์สถานะรับข้อมูลส่วนตัว
                    user_states[user_id]["index"] = 0
                    user_states[user_id]["scores"] = []

                    # ลบเฉพาะ flag ที่ไม่ใช้แล้ว
                    user_states[user_id].pop("awaiting_phone", None)
                    user_states[user_id].pop("awaiting_student_id", None)
                    user_states[user_id].pop("awaiting_name", None)

                    # เริ่มทำแบบประเมิน
                    q = DASS_21[0]["text"]
                    # reply_message(reply_token,  f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nตอบโดยพิมพ์ตัวเลข:\n0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
                    reply_dass_question(reply_token, f"เริ่มแบบประเมิน DASS-21\n\n{q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
                    return jsonify({"status": "ok"})
            
            ## กรณีทำซ้ำแบบประเมิน
            if user_text == "ยืนยันทำซ้ำ":
                cooldown, _ = check_dass_cooldown(user_id)

                if not cooldown:
                    reply_message(reply_token, "ขณะนี้คุณสามารถทำแบบประเมินได้ตามปกติ สามารถเลือกที่ริชเมนู 'ทำแบบประเมิน' ได้เลย")
                    return jsonify({"status": "ok"})

                if not can_use_override(user_id):
                    reply_message(
                        reply_token,
                        "คุณได้ใช้สิทธิ์ทำซ้ำไปแล้ว\n"
                        "สามารถทำซ้ำได้อีกครั้งใน 24 ชั่วโมง"    
                    )
                    return jsonify({"status": "ok"})

                # อนุญาต override
                user_states[user_id] = {"awaiting_dass_consent": True}
                send_dass_consent(reply_token)
                return jsonify({"status": "ok"})

            cooldown, days_left = check_dass_cooldown(user_id)
                    
            # เริ่มต้นทำแบบประเมิน DASS-21
            if user_text.lower() in ["ทำแบบประเมิน", "แบบประเมิน", "เริ่มแบบประเมิน"]:
                if cooldown:
                    send_dass_repeat(
                        reply_token,
                            f"คุณเพิ่งทำแบบประเมินไป\n"
                            f"สามารถทำซ้ำได้อีกครั้งในอีก {days_left} วัน\n"
                            "แนะนำให้เว้นระยะอย่างน้อย 1 สัปดาห์\n\n"
                            "คุณต้องการทำอย่างไรต่อ?"
                                            )
                    return jsonify({"status": "ok"})
                    
                user_states[user_id] = {
                    "awaiting_dass_consent": True
                }
                send_dass_consent(reply_token)
                return jsonify({"status": "ok"})


            # กรณียกเลิกการทำแบบประเมิน
            if user_text.lower() in ["ยกเลิก" ,"ออก", "เลิกทำแบบประเมิน "]:
                if user_id in user_states:
                    del user_states[user_id]
                    reply_message(reply_token ,"คุณได้ยกเลิกการทำแบบประเมินแล้ว หากต้องการเริ่มใหม่ พิมพ์ว่า 'ทำแบบประเมิน' ได้เลยนะ")
                    return jsonify({"status": "ok"})

            if user_id in user_states and "index" in user_states[user_id]:
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
                        # reply_message(reply_token, f"{next_q}\n\nตอบโดยพิมพ์ตัวเลข:\n0 = ไม่เคย\n1 = เป็นบางครั้ง\n2 = เป็นบ่อยครั้ง\n3 = เป็นประจำ\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
                        reply_dass_question(reply_token, f"{next_q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
                    else:
                        summary = summaryScore(state["scores"])
                        d, a, s = summary['D'], summary['A'], summary['S']
                        # print(f"Message from {display_name} ({user_id}): {user_text}")
                        
                        # ถ้ามีค่า dass_ consent ใน state แสดงว่าผู้ใช้ได้ตอบเรื่องการยินยอมไว้แล้ว → ใช้ค่านั้นในการตัดสินใจว่าจะบันทึกผลหรือไม่ 
                        dass_consent = state.get("dass_consent", False)

                        if dass_consent:
                            try:
                                result_id , d_level, a_level, s_level = save_dass_result(user_id, d, a, s)

                                for i, answer in enumerate(state["scores"]):
                                    save_dass_answer(
                                        result_id=result_id,
                                        question_number=i+1,
                                        question_type=answer["type"],
                                        score=answer["score"]
                                    )
                                send_notification(user_id, d_level, a_level, s_level)

                            except Exception as e:
                                print("Error saving DASS answers:", e)
                        else:
                            d_level = get_level("D", d)
                            a_level = get_level("A", a)
                            s_level = get_level("S", s)


                            user_states[user_id]["assessment_context"] = {
                                    "D": d,
                                    "A": a,
                                    "S": s,
                                    "D_level": d_level,
                                    "A_level": a_level,
                                    "S_level": s_level,
                                    "timestamp": time.time()
                                }

                        send_dass_result_flex(
                            reply_token,
                            d, a, s,
                            d_level, a_level, s_level
                            )

                        try:
                            log_dass_taken(user_id)
                        except Exception as e:
                            print("Log error:", e)

                        #  ล้าง state ให้ครบก่อน
                        user_states[user_id].pop("index", None)
                        user_states[user_id].pop("scores", None)
                        user_states[user_id].pop("dass_consent", None)

                        return jsonify({"status": "ok"})
                else:
                    current_q = DASS_21[state["index"]]["text"]
                    # reply_message(
                    #     reply_token,
                    #     f"กรุณาตอบเป็นตัวเลขที่กำหนดเท่านั้นนะ\n\n"
                    #     f" คำถาม:\n{current_q}\n\n"
                    #     f" 0 = ไม่เคย\n"
                    #     f" 1 = เป็นบางครั้ง\n"
                    #     f" 2 = เป็นบ่อยครั้ง\n"
                    #     f" 3 = เป็นประจำ\n\n"
                    #     f"ถ้าพิมพ์นอกเหนือแชตบอตจะไม่ตอบกลับ หากต้องการยกเลิกแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'"
                    # )
                    reply_dass_question(reply_token, f"กรุณาตอบเป็นตัวเลขที่กำหนดเท่านั้นนะ\n\nคำถาม:\n{current_q}\n\nหากต้องการยกเลิกการทำแบบประเมิน พิมพ์ว่า 'ยกเลิก' หรือ 'ออก'")
                return jsonify({"status": "ok"})
            
            assessment_context = None

            state = user_states.get(user_id)
            if state and "assessment_context" in state:
                ac = state["assessment_context"]

                # TTL: ล้าง context ถ้าเก่าเกิน 1 ชั่วโมง
                if time.time() - ac["timestamp"] > 3600:
                    user_states[user_id].pop("assessment_context", None)
                    assessment_context = None
                else:
                    assessment_context = (
                        "ผลการประเมิน DASS-21 ล่าสุดของผู้ใช้ (ใช้เพื่อช่วยตอบเท่านั้น):\n"
                        f"- ซึมเศร้า: {ac['D_level']}\n"
                        f"- วิตกกังวล: {ac['A_level']}\n"
                        f"- ความเครียด: {ac['S_level']}\n"
                        "ข้อกำหนด:\n"
                        "- ห้ามวินิจฉัย\n"
                        "- ใช้น้ำเสียงอ่อนโยน ไม่ตีตรา\n"
            )

            
            query_text = user_text
            retrieved_docs = query_postgresql(query_text)   
            # print(" Retrieved Docs:", retrieved_docs) 

            #แปลง array เป็น string
            context = "\n".join([doc[0] for doc in retrieved_docs])if retrieved_docs else "ไม่มีข้อมูลที่เกี่ยวข้อง"
            # context = "\n".join(
            #     [doc["content"] for doc in retrieved_docs if doc["score"] ]
            # )

            # print("Context for user", user_id, ":", context)

            #จัดรูปประวิติสนทนา
            if user_id not in chat_histories:
                history_from_db = load_chat_history(user_id)
                if history_from_db:
                    chat_histories[user_id] = history_from_db[-6:]  # โหลดเฉพาะบทสนทนาล่าสุดไม่เกิน 6 รายการ
                else:
                    chat_histories[user_id] = []

            history_text = format_history(chat_histories[user_id])
            # print("history_Text : "+ history_text)

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

            # print("Messages for LLM:", messages)

            
            # model = genai.GenerativeModel("models/gemma-3-27b-it")  
            # response = model.generate_content([{"role": "user", "parts": [prompt]}],
            #     generation_config={
            #         "temperature": 0.5,           
            #         "top_p": 0.8,
            #         "top_k": 3,
            #         "max_output_tokens": 200
            #     }
            # )

            
            reply_text = "ขออภัย ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้งภายหลัง"

            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
                        "HTTP-Referer": OPEN_ROUTER_API_URL,
                        "X-Title": "Mental Health Chatbot"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-001",
                        "messages": messages,
                        "temperature": 0.4
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        reply_text = choices[0]["message"].get("content", reply_text).strip()
                else:
                    print("OpenRouter error:", response.status_code, response.text)

            except Exception as e:
                print("LLM error:", e)


            # response = zai_client.chat.completions.create(
            #     model="glm-4.7-flash",
            #     messages=messages,
            #     temperature=0.4,
            #     max_tokens=300,
            #     thinking={"type": "disabled"}
            # )
            # reply_text = response.choices[0].message.content.strip()


            # บันทึกประวัติใน session
            chat_histories[user_id].append({"role": "user", "content": query_text} )
            chat_histories[user_id].append({"role": "assistant", "content": reply_text})

            # ตรวจสอบความยินยอมก่อนบันทึก
            if check_user_consent(user_id):
                #  ถ้ายินยอม -> บันทึกข้อความทั้งสองฝั่ง
                save_message_to_db(user_id, "user", query_text)
                save_message_to_db(user_id, "assistant", reply_text)
            else:
                pass


            # จำกัดบทสนทนาไม่เกิน 10 ข้อความล่าสุด (5 user  5 assistant)
            chat_histories[user_id] = chat_histories[user_id][-6:]

            if not reply_text:
                reply_text = "ขออภัย ฉันไม่สามารถตอบคำถามนี้ได้ในตอนนี้"
            reply_message(reply_token, reply_text)

        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error in webhook:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    start_scheduler(test_mode=False)  
    app.run(host="0.0.0.0", port=5000)  

