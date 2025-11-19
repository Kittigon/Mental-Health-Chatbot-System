import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# env
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# บันทึกสไตล์โทนเสียงลงฐานข้อมูล
def save_tone_to_db(user_id, tone):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT    
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_consent (line_user_id, tone_style, granted_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (line_user_id)
        DO UPDATE SET tone_style = EXCLUDED.tone_style, granted_at = EXCLUDED.granted_at
    """, (user_id, tone, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

# ดึงสไตล์โทนเสียงจากฐานข้อมูล
def get_tone_from_db(user_id):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT tone_style FROM user_consent WHERE line_user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result and result[0]:
        return result[0]
    return "friendly"  