from consent import save_consent_to_db, check_user_consent, handle_consent
from greeting import save_greeting_permission, get_user_to_greet
from tone import save_tone_to_db, get_tone_from_db
from tone_config import DEFAULT_TONE
from line.line_messaging import reply_message
from line.line_ui import send_consent_message, send_settings_main, send_toggle_settings, send_style_menu

TONE_LABEL_MAP = {
    "formal": "ทางการ",
    "semi_formal": "กึ่งทางการ",
    "friendly": "เป็นกันเอง",
    "teen": "วัยรุ่น",
    "empathetic": "อบอุ่นและเข้าอกเข้าใจ"
}

STYLE_TEXT_TO_TONE = {
    "ทางการ": "formal",
    "กึ่งทางการ": "semi_formal",
    "เป็นกันเอง": "friendly",
    "วัยรุ่น": "teen",
    "อบอุ่นและเข้าอกเข้าใจ": "empathetic"
}

HELP_MESSAGE = (
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


# postback ของปุ่มยินยอม/ไม่ยินยอมตอน follow บอทครั้งแรก
def handle_consent_postback(data_postback, user_id, reply_token):
    if data_postback == "consent_chat=accept":
        handle_consent(user_id, True, reply_token)
        return True
    elif data_postback == "consent_chat=decline":
        handle_consent(user_id, False, reply_token)
        return True
    return False


# เมนูการตั้งค่า / สไตล์การสนทนา / toggle consent-greeting / คู่มือ / consent ข้อความล้วน / นัดหมาย
# คืนค่า True ถ้าข้อความนี้ถูกจัดการแล้ว (ผู้เรียกควร return ทันที), False ถ้าไม่เกี่ยวกับ settings flow
def handle_settings_message(user_id, user_text, reply_token, user_states):
    if user_text == "การตั้งค่า":
        send_settings_main(reply_token)
        return True

    if user_text == "การยินยอม":
        status = check_user_consent(user_id)
        send_toggle_settings(reply_token, "การยินยอม", status, "สลับสถานะการยินยอม")
        return True

    if user_text == "ทักทายอัตโนมัติ":
        status = get_user_to_greet(user_id)
        send_toggle_settings(reply_token, "ทักทายอัตโนมัติ", status, "สลับสถานะทักทายอัตโนมัติ")
        return True

    if user_text == "สไตล์การสนทนา":
        tone_key = get_tone_from_db(user_id) or DEFAULT_TONE
        current_style = TONE_LABEL_MAP.get(tone_key, "ค่าเริ่มต้น")
        send_style_menu(reply_token, current_style)
        return True

    # เมื่อเลือกสไตล์
    if user_text in STYLE_TEXT_TO_TONE:
        english_style = STYLE_TEXT_TO_TONE[user_text]
        save_tone_to_db(user_id, english_style)
        reply_message(reply_token, f"อัปเดตสไตล์การสนทนาแล้ว ({user_text}) ")
        return True

    # สลับการตั้งค่าการยินยอม
    if user_text == "สลับสถานะการยินยอม":
        current_status = check_user_consent(user_id)
        new_status = not current_status
        handle_consent(user_id, new_status, reply_token)
        reply_message(reply_token, "อัปเดตสถานะการยินยอมแล้ว")
        return True

    # สลับการตั้งค่าทักทายอัตโนมัติ
    if user_text == "สลับสถานะทักทายอัตโนมัติ":
        current_status = get_user_to_greet(user_id)
        new_status = not current_status
        save_greeting_permission(user_id, new_status)
        reply_message(reply_token, "อัปเดตโหมดทักทายอัตโนมัติแล้ว")
        return True

    if user_text.lower() in ["คู่มือการใช้งาน", "help", "menu"]:
        reply_message(reply_token, HELP_MESSAGE)
        return True

    # การตั้งค่าทักทายอัตโนมัติ (ถามยืนยันแบบ 1/2)
    if user_text.lower() in ["ทักทายอัตโนมัติ", "ตั้งค่าทักทายอัตโนมัติ"]:
        if not check_user_consent(user_id):
            reply_message(reply_token, "ก่อนอื่นคุณต้องให้ความยินยอมในการเก็บข้อมูลส่วนบุคคลก่อน🙏")
            return True
        user_states[user_id] = {"ask_greeting": True}
        reply_message(
            reply_token,
            "คุณต้องการให้แชตบอตทักทายคุณโดยอัตโนมัติเมื่อเริ่มสนทนาหรือไม่?\n"
            "กรุณาพิมพ์:\n 1 = ใช่\n 2 = ไม่"
        )
        return True

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
        return True

    # การยินยอมและถอนความยินยอม
    if user_text.lower() in ["การยินยอม", "consent", "ข้อตกลงในการใช้งาน"]:
        send_consent_message(reply_token)
        return True
    if user_text.lower() in ["ถอนความยินยอม", "ยกเลิกการยินยอม"]:
        save_consent_to_db(user_id, False)
        reply_message(reply_token, "คุณได้ถอนความยินยอมแล้ว ข้อมูลของคุณจะไม่ถูกเก็บต่อไป 🩵")
        return True

    if user_text.lower() in ["นัดหมายผู้เชี่ยวชาญ", "จองคิว", "นัดหมาย"]:
        reply_message(reply_token, "คุณสามารถนัดหมายผู้เชี่ยวชาญได้ที่นี่: https://appointment-website-nine.vercel.app/login")
        return True

    return False
