import datetime
import os
from dotenv import load_dotenv
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

# ดึงค่าจาก .env
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


#  ทักทายตามช่วงเวลา
def greeting_by_time():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute

    if 7 <= hour < 12:
        return "สวัสดีตอนเช้า ขอให้เป็นวันที่สดใสนะ 🌤️"
    elif 12 <= hour < 18:
        return "สวัสดีตอนบ่าย ขอให้วันนี้เป็นวันที่ดีนะ 😊"
    else:
        return "สวัสดีตอนเย็น ขอให้ช่วงค่ำนี้ผ่อนคลายนะ 🌆"



# ดึงรายชื่อผู้ใช้ที่อนุญาตให้ทักทายอัตโนมัติ
def get_all_users_to_greet():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT line_user_id FROM user_consent
        WHERE allow_greeting = TRUE
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]  # คืนค่าเป็น list ของ user_id

# ตรวจสอบว่าผู้ใช้รายบุคคล อนุญาตให้ทักทายอัตโนมัติหรือไม่
def get_user_to_greet(user_id):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT allow_greeting FROM user_consent
        WHERE line_user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row[0]:
        return True
    return False


# อัปเดตเวลาที่ทักทายล่าสุด
def update_last_greeted(user_id):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""
        UPDATE user_consent
        SET last_greeted = %s
        WHERE line_user_id = %s
    """, (datetime.datetime.now(), user_id))
    conn.commit()
    cur.close()
    conn.close()


# ฟังก์ชันทักทายอัตโนมัติ
def auto_greet():
    from main import push_message  # เรียกใช้ฟังก์ชันส่งข้อความจาก main.py
    
    users = get_all_users_to_greet()
    message = greeting_by_time()
    for user_id in users:
        push_message(user_id, message)
        update_last_greeted(user_id)


# ตั้งเวลาให้ทักทายอัตโนมัติ
def start_scheduler(test_mode=False):
    scheduler = BackgroundScheduler()

    if test_mode:
        # สำหรับทดสอบ: ทำงานทุก 30 วินาที
        scheduler.add_job(auto_greet, "interval", seconds=30)
        print(" Scheduler started in TEST MODE (every 30 seconds)")
    else:
        #  สำหรับใช้งานจริง
        scheduler.add_job(auto_greet, "cron", hour="7,12,18" ,minute=0)
        print(" Scheduler started for production (7, 12, 18)")

    scheduler.start()


# บันทึกการอนุญาตทักทายอัตโนมัติ
def save_greeting_permission(user_id, allow):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""
        UPDATE user_consent
        SET allow_greeting = %s
        WHERE line_user_id = %s
    """, (allow, user_id))
    conn.commit()
    cur.close()
    conn.close()
