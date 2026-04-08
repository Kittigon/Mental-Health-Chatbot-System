import os
from dotenv import load_dotenv
from datetime import datetime 
from psycopg2 import pool
import psycopg2
from datetime import datetime, timedelta

load_dotenv()

#env
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# # สร้างตาราง user_consent ถ้ายังไม่มี
# try:
#     conn = psycopg2.connect(
#         dbname=DB_NAME,
#         user=DB_USER,
#         password=DB_PASSWORD,
#         host=DB_HOST,
#         port=DB_PORT
#     )
#     cur = conn.cursor()

#     # เพิ่มคอลัมน์ last_dass_reminder ถ้ายังไม่มี
#     cur.execute("""
#         ALTER TABLE user_consent
#         ADD COLUMN last_dass_reminder TIMESTAMPTZ;
#     """)

    # ตาราง user_consent
    # cur.execute("""
    #     CREATE TABLE IF NOT EXISTS user_consent (
    #         line_user_id VARCHAR(100) PRIMARY KEY,
    #         name TEXT,
    #         phone TEXT,
    #         student_id VARCHAR(20),
    #         consent BOOLEAN,
    #         granted_at TIMESTAMP,
    #         allow_greeting BOOLEAN DEFAULT FALSE,
    #         last_greeted TIMESTAMP,
    #         tone_style VARCHAR(20) DEFAULT 'friendly'
    #     );
    # """)

#     # ตาราง chat_history
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS chat_history (
#             id SERIAL PRIMARY KEY,
#             line_user_id VARCHAR(100) NOT NULL,
#             role TEXT NOT NULL,          
#             content TEXT NOT NULL,
#             timestamp TIMESTAMPTZ DEFAULT NOW(),
#             FOREIGN KEY (line_user_id) REFERENCES user_consent(line_user_id) ON DELETE CASCADE
#         );
#     """)

#     # ตาราง Dass_21_result
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS Dass_21_result (
#             id SERIAL PRIMARY KEY,
#             user_id VARCHAR(100),
#             depression_score INT,
#             anxiety_score INT,
#             stress_score INT,
#             depression_level TEXT,
#             anxiety_level TEXT,
#             stress_level TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (user_id) REFERENCES user_consent(line_user_id) ON DELETE CASCADE
#         );
#     """)

#     # Commit การเปลี่ยนแปลง
#     conn.commit()
#     print(" Tables created successfully!")

# except Exception as e:
#     print(" Error creating tables:", e)

# finally:
#     cur.close()
#     conn.close()

# print("ตาราง user_consent ถูกสร้างเรียบร้อยแล้ว")

db_pool = pool.SimpleConnectionPool(    
    minconn=1,
    maxconn=10,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)


# ตรวจสอบว่าผู้ใช้ยินยอมแล้วหรือไม่
def check_user_consent(user_id):
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT consent FROM user_consent WHERE line_user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        db_pool.putconn(conn)  

        if row is None:
            return None  
        return bool(row[0])  
    except Exception as e:
        print("Error checking user consent:", e)
        return None


# บันทึกการยินยอมลงฐานข้อมูล
def save_consent_to_db(user_id, consent):
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_consent (line_user_id, consent, granted_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (line_user_id)
            DO UPDATE SET consent = EXCLUDED.consent, granted_at = EXCLUDED.granted_at
        """, (user_id, consent, datetime.now()))
        conn.commit()
        cur.close()
        db_pool.putconn(conn)
    except Exception as e:
        print("Error saving consent to DB:", e)

def check_profile(user_id):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT name, phone FROM user_consent WHERE line_user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row[0] and row[1]:
        return True
    return False

def save_profile(line_user_id, name, phone, student_id):
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO user_consent (line_user_id, name, phone, student_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (line_user_id) DO UPDATE
            SET name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                student_id = EXCLUDED.student_id
        """, (line_user_id, name, phone, student_id))

        conn.commit()
        cur.close()
        db_pool.putconn(conn)

    except Exception as e:
        print("Save Profile Error:", e)

def handle_consent(user_id, consent_value, reply_token):
    from main import reply_message
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()

        cur.execute("SELECT consent, granted_at FROM user_consent WHERE line_user_id = %s", (user_id,))
        row = cur.fetchone()
        now = datetime.now()

        if row:
            last_consent, granted_at = row

            # cooldown 30 วินาที
            if granted_at and (now - granted_at).total_seconds() < 30:
                reply_message(reply_token, "คุณกดเร็วเกินไป กรุณารอสักครู่นะคะ")
                cur.close()
                db_pool.putconn(conn)
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
                cur.close()
                db_pool.putconn(conn)
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

        cur.close()
        db_pool.putconn(conn)

    except Exception as e:
        print("Error handle_consent:", e)
        reply_message(
            reply_token,
            "ขออภัย เกิดข้อผิดพลาดในการบันทึกการยินยอม "
            "กรุณาลองใหม่อีกครั้งในภายหลังนะคะ"
        )

#--------------------------------------------------------------------------------------------------------------
# if data_postback.startswith("consent="):
#     value = data_postback.split("=")[1]
#     consent = True if value == "accept" else False
#     save_consent_to_db(user_id, consent)
#     if consent:
#         reply_message(reply_token,
#                 "ขอบคุณค่ะ คุณได้ยินยอมให้เก็บข้อมูลเรียบร้อยแล้ว\n\n"
#                 "ต่อไปนี้คุณสามารถเลือกการตั้งค่าเพิ่มเติมได้เลย:\n\n"
#                 "1) หากคุณต้องการให้แชตบอตทักทายคุณโดยอัตโนมัติเมื่อเริ่มสนทนา\n"
#                 "   กรุณาพิมพ์: ทักทายอัตโนมัติ\n\n"
#                 "2) หากคุณต้องการกำหนดโทนการสนทนาของแชตบอต (เช่น อบอุ่น, เป็นทางการ, สนุกสนาน)\n"
#                 "   กรุณาพิมพ์: โทนเสียง\n\n"
#                 "3) หากคุณต้องการทำแบบประเมิน DASS-21 เพื่อตรวจระดับสภาวะเครียด วิตกกังวล และซึมเศร้า\n"
#                 "   กรุณาพิมพ์: ทำแบบประเมิน DASS-21\n\n"
#                 "คุณสามารถเลือกทำข้อใดก่อนก็ได้ค่ะ"
#             )
#     else:
#         reply_message(reply_token, "รับทราบค่ะ ระบบจะไม่เก็บข้อมูลส่วนบุคคลของคุณ 🙏 ")
#     return jsonify({"status": "ok"})