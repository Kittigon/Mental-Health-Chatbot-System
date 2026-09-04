import os
import requests
from dotenv import load_dotenv

from core.db import get_cursor

# Load environment variables
load_dotenv()

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
    # แปลงข้อความเป็น embedding ผ่าน API
    query_embedding = get_embedding(query_text)
    query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql_query = """
        SELECT content, embedding <=> %s::vector AS similarity_score
        FROM documents
        ORDER BY similarity_score ASC
        LIMIT %s;
    """
    with get_cursor() as cur:
        cur.execute(sql_query, (query_embedding_str, k))
        result = cur.fetchall()
    return result

