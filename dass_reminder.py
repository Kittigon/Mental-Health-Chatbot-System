import os
from dotenv import load_dotenv
import psycopg2
from line_messaging import push_message

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


def check_dass_reminder():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    cur = conn.cursor()

    sql = """
        SELECT 
        uc.line_user_id,
        MAX(dl.taken_at) as last_taken
        FROM user_consent uc
        JOIN dass_21_log dl
            ON uc.line_user_id = dl.user_id
        GROUP BY uc.line_user_id, uc.last_dass_reminder
        HAVING NOW() - MAX(dl.taken_at) >= INTERVAL '7 days'
        AND (
            uc.last_dass_reminder IS NULL
            OR uc.last_dass_reminder < MAX(dl.taken_at)
        )
    """

    cur.execute(sql)
    users = cur.fetchall()

    for user in users:

        user_id = user[0]

        # ส่ง LINE แจ้งเตือน
        push_message(
            user_id,
            """แจ้งเตือนแบบประเมินสุขภาพจิต

        ครบ 7 วันแล้วตั้งแต่คุณทำแบบประเมินครั้งล่าสุด

        หากต้องการประเมินสุขภาพจิตของคุณอีกครั้ง
        สามารถเลือกที่ริชเมนู "แบบประเมิน" ได้เลย
        """
        )

        # update กันส่งซ้ำ
        cur.execute("""
            UPDATE user_consent
            SET last_dass_reminder = NOW()
            WHERE line_user_id = %s
        """, (user_id,))

    conn.commit()

    cur.close()
    conn.close()