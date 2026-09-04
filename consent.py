from datetime import datetime

from core.db import get_cursor
from line.line_messaging import reply_message

# ตรวจสอบว่าผู้ใช้ยินยอมแล้วหรือไม่
def check_user_consent(user_id):
    try:
        with get_cursor() as cur:
            cur.execute("SELECT consent FROM user_consent WHERE line_user_id=%s", (user_id,))
            row = cur.fetchone()

        if row is None:
            return None
        return bool(row[0])
    except Exception as e:
        print("Error checking user consent:", e)
        return None


# บันทึกการยินยอมลงฐานข้อมูล
def save_consent_to_db(user_id, consent):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO user_consent (line_user_id, consent, granted_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (line_user_id)
                DO UPDATE SET consent = EXCLUDED.consent, granted_at = EXCLUDED.granted_at
            """, (user_id, consent, datetime.now()))
    except Exception as e:
        print("Error saving consent to DB:", e)

def check_profile(user_id):
    with get_cursor() as cur:
        cur.execute("SELECT name, phone FROM user_consent WHERE line_user_id = %s", (user_id,))
        row = cur.fetchone()
    if row and row[0] and row[1]:
        return True
    return False

def save_profile(line_user_id, name, phone, student_id):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO user_consent (line_user_id, name, phone, student_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (line_user_id) DO UPDATE
                SET name = EXCLUDED.name,
                    phone = EXCLUDED.phone,
                    student_id = EXCLUDED.student_id
            """, (line_user_id, name, phone, student_id))
    except Exception as e:
        print("Save Profile Error:", e)

def handle_consent(user_id, consent_value, reply_token):
    try:
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute("SELECT consent, granted_at FROM user_consent WHERE line_user_id = %s", (user_id,))
            row = cur.fetchone()

        if row:
            last_consent, granted_at = row

            # cooldown 30 วินาที
            if granted_at and (now - granted_at).total_seconds() < 30:
                reply_message(reply_token, "คุณกดเร็วเกินไป กรุณารอสักครู่นะคะ")
                return

            # เลือกเหมือนเดิม
            if last_consent == consent_value:
                if consent_value:
                    reply_message(
                        reply_token,
                        "คุณได้ยินยอมให้เก็บข้อมูลการสนทนาไว้แล้วค่ะ "
                    )
                else:
                    reply_message(
                        reply_token,
                        "คุณได้เลือกไม่ยินยอมให้เก็บข้อมูลการสนทนาไว้แล้วค่ะ"
                    )
                return

        # บันทึกสถานะใหม่
        save_consent_to_db(user_id, consent_value)

        if consent_value:
            reply_message(
                reply_token,
                "ขอบคุณค่ะ \n\n"
                "คุณได้ยินยอมให้แชตบอตเก็บข้อมูลการสนทนา "
                "เพื่อใช้ในการปรับปรุงคุณภาพการให้คำแนะนำ "
                "และการตั้งค่าประสบการณ์การใช้งาน เช่น โทนการสนทนาและการทักทายอัตโนมัติ\n\n"

                " คุณยังสามารถใช้งานแชตบอตได้ตามปกติทุกฟีเจอร์\n"
                " สำหรับการทำแบบประเมินสุขภาพจิต (DASS-21) "
                "ระบบจะขอความยินยอมแยกต่างหากทุกครั้งก่อนเริ่มทำแบบประเมิน\n\n"

                "คุณสามารถปรับเปลี่ยนการยินยอมนี้ได้ตลอดเวลาผ่านเมนูการตั้งค่า"
            )
        else:
            reply_message(
                reply_token,
                "รับทราบค่ะ \n\n"
                "แชตบอตจะไม่ทำการบันทึกข้อมูลการสนทนาของคุณ "
                "แต่คุณยังสามารถพูดคุยกับแชตบอต "
                "และใช้งานฟีเจอร์ต่าง ๆ ได้ตามปกติ\n\n"

                " หากภายหลังคุณต้องการให้ความยินยอม "
                "สามารถเปลี่ยนแปลงได้ทุกเมื่อผ่านเมนูการตั้งค่า"
            )

    except Exception as e:
        print("Error handle_consent:", e)
        reply_message(
            reply_token,
            "ขออภัย เกิดข้อผิดพลาดในการบันทึกการยินยอม "
            "กรุณาลองใหม่อีกครั้งในภายหลังนะคะ"
        )