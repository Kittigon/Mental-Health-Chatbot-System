from line.line_messaging import push_message
from core.db import get_cursor


def check_dass_reminder():
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

    with get_cursor(commit=True) as cur:
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