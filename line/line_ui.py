from line.line_messaging import reply

# ===== Theme (ใช้ร่วมกันทุกเมนู) =====
PRIMARY_COLOR = "#2C3E50"
BG_LIGHT = "#E8F0FE"
CARD_BG = "#FFFFFF"


def send_dass_repeat(reply_token, message):
    messages = [
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
    reply(reply_token, messages)


def send_dass_consent(reply_token):
    messages = [
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
    reply(reply_token, messages)


# ส่งข้อความขอความยินยอม
def send_consent_message(reply_token):
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
    reply(reply_token, [flex_body])


# ส่งเมนูการตั้งค่า
def send_settings_main(reply_token):
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
                "backgroundColor": BG_LIGHT,
                "contents": [

                    # ===== Header =====
                    {
                        "type": "text",
                        "text": "⚙️ การตั้งค่า",
                        "size": "xl",
                        "weight": "bold",
                        "color": PRIMARY_COLOR
                    },

                    # ===== Consent Description Card =====
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": CARD_BG,
                        "paddingAll": "15px",
                        "cornerRadius": "12px",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "การยินยอมให้บันทึกการสนทนา",
                                "weight": "bold",
                                "color": PRIMARY_COLOR
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
                        "color": PRIMARY_COLOR,
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
                        "color": PRIMARY_COLOR
                    },

                    # ===== Auto Greeting =====
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
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
                        "color": PRIMARY_COLOR,
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
    reply(reply_token, [flex])


# ส่งเมนูสลับการตั้งค่า
def send_toggle_settings(reply_token, label, status, toggle_cmd):
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
                "backgroundColor": BG_LIGHT,
                "contents": [
                    {
                        "type": "text",
                        "text": f"⚙️ {label}",
                        "size": "xl",
                        "weight": "bold",
                        "color": PRIMARY_COLOR
                    },
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "text",
                        "text": f"สถานะปัจจุบัน: {'เปิด 🔵' if status else 'ปิด ⚪'}",
                        "size": "lg",
                        "weight": "bold",
                        "color": PRIMARY_COLOR
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
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
    reply(reply_token, [flex])


# ส่งเมนูสไตล์การสนทนา
def send_style_menu(reply_token, current_style):
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
                "backgroundColor": BG_LIGHT,
                "contents": [

                    # ===== Header =====
                    {
                        "type": "text",
                        "text": "🎨 สไตล์การสนทนา",
                        "size": "xl",
                        "weight": "bold",
                        "color": PRIMARY_COLOR
                    },

                    # ===== Current Style Card =====
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": CARD_BG,
                        "paddingAll": "15px",
                        "cornerRadius": "12px",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "สไตล์ปัจจุบัน",
                                "weight": "bold",
                                "color": PRIMARY_COLOR
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
                        "color": PRIMARY_COLOR,
                        "action": {
                            "type": "message",
                            "label": "ทางการ",
                            "text": "ทางการ"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
                        "action": {
                            "type": "message",
                            "label": "กึ่งทางการ",
                            "text": "กึ่งทางการ"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
                        "action": {
                            "type": "message",
                            "label": "เป็นกันเอง",
                            "text": "เป็นกันเอง"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
                        "action": {
                            "type": "message",
                            "label": "วัยรุ่น",
                            "text": "วัยรุ่น"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": PRIMARY_COLOR,
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
    reply(reply_token, [flex])


# ส่งผลการประเมิน DASS-21 แบบ Flex Message
def send_dass_result_flex(reply_token, d, a, s, d_level, a_level, s_level):
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
    reply(reply_token, [flex_body])


# ส่งคำถาม DASS-21 พร้อมตัวเลือกแบบ Quick Reply
def reply_dass_question(reply_token, question_text):
    messages = [
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
    reply(reply_token, messages)
