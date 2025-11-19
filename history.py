from dotenv import load_dotenv
import os
from psycopg2 import pool
# from qdrant_client import QdrantClient
# from qdrant_client.models import VectorParams, Distance


load_dotenv()

#env
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# QDRANT_API_URL = os.getenv("QDRANT_API_URL")
# QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

## สร้างตาราง
# conn = psycopg2.connect(
#     dbname = DB_NAME,
#     user = DB_USER,
#     password = DB_PASSWORD ,
#     host = DB_HOST ,
#     port  = DB_PORT
# )

# cur = conn.cursor()
# cur.execute("""
#     CREATE TABLE chat_history(
#         id SERIAL PRIMARY KEY,
#         chat_id TEXT NOT NUll ,
#         role TEXT NOT NUll,
#         content TEXT NOT NUll,
#         timestamp TIMESTAMPTZ DEFAULT NOW()
#     )
# """)
# conn.commit()
# cur.close()
# conn.close()

# print("ตาราง chat_history ถูกสร้างเรียบร้อยแล้ว")

# QdrantClient = QdrantClient(
#     url=QDRANT_API_URL, 
#     api_key=QDRANT_API_KEY
# );



# สร้าง connection pool ตอนเริ่มต้น
db_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)


def save_message_to_db(user_id, role, content ):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_history (line_user_id , role, content ) VALUES ( %s, %s , %s)",
            (user_id, role, content )
        )
        conn.commit()
        cur.close()
    finally:
        db_pool.putconn(conn)  # คืน connection กลับ pool

def load_chat_history(user_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT role, content FROM chat_history WHERE line_user_id = %s ORDER BY id ASC LIMIT 10",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [{"role": row[0], "content": row[1]} for row in rows]
    finally:
        db_pool.putconn(conn)



