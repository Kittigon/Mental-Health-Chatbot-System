from datetime import datetime

from core.db import get_cursor

# บันทึกสไตล์โทนเสียงลงฐานข้อมูล
def save_tone_to_db(user_id, tone):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO user_consent (line_user_id, tone_style, granted_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (line_user_id)
            DO UPDATE SET tone_style = EXCLUDED.tone_style, granted_at = EXCLUDED.granted_at
        """, (user_id, tone, datetime.now()))

# ดึงสไตล์โทนเสียงจากฐานข้อมูล
def get_tone_from_db(user_id):
    with get_cursor() as cur:
        cur.execute("SELECT tone_style FROM user_consent WHERE line_user_id = %s", (user_id,))
        result = cur.fetchone()
    if result and result[0]:
        return result[0]
    return "friendly"