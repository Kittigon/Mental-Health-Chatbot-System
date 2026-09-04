from core.db import get_cursor


def save_message_to_db(user_id, role, content):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO chat_history (line_user_id , role, content ) VALUES ( %s, %s , %s)",
            (user_id, role, content)
        )

def load_chat_history(user_id):
    with get_cursor() as cur:
        cur.execute(
            "SELECT role, content FROM chat_history WHERE line_user_id = %s ORDER BY id ASC LIMIT 10",
            (user_id,)
        )
        rows = cur.fetchall()
    return [{"role": row[0], "content": row[1]} for row in rows]



