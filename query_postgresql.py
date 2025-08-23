import psycopg2
from dotenv import load_dotenv
import os
import requests
# import json

# Load environment variables
load_dotenv()   

# SupabaseUrl = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

def get_embedding(text: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    data = {"text": [text]}
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    result = resp.json()
    
    return result["result"]["data"][0] 

def query_postgresql(query_text, k=3):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    # แปลงข้อความเป็น embedding ผ่าน API
    query_embedding = get_embedding(query_text)
    query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql_query = """
        SELECT content, embedding <=> %s::vector AS similarity_score
        FROM documents
        ORDER BY similarity_score ASC
        LIMIT %s;
    """
    cur.execute(sql_query, (query_embedding_str, k))
    result = cur.fetchall()

    cur.close()
    conn.close()
    return result


# result = query_postgresql("ศูนย์ให้คำปรึกษา มพ อยู่ที่ไหน")
# print(result)

