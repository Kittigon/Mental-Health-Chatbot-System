from sentence_transformers import SentenceTransformer
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()   

SupabaseUrl = os.getenv("DATABASE_URL")

embedder = SentenceTransformer("BAAI/bge-m3")

# # สร้างตาราง postgresql
# conn = psycopg2.connect(SupabaseUrl)
# cur = conn.cursor()

# cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# cur.execute("""
#     CREATE TABLE IF NOT EXISTS documents (
#         id SERIAL PRIMARY KEY,
#         content TEXT,
#         embedding VECTOR(1024)
#     );
# """)

# conn.commit()
# cur.close()
# conn.close()
# print("Table created successfully.")

def query_postgresql(query_text , k=3) :
    conn = psycopg2.connect(SupabaseUrl)

    query_embedding = embedder.encode(query_text).tolist

    cur = conn.cursor()   
    query_embedding_str = "[" + ",".join(map(str, query_embedding() )) + "]"
    sql_query = """
        SELECT content , embedding <=> %s::vector AS similarity_score
        FROM documents
        ORDER BY similarity_score ASC
        LIMIT %s ;
    """

    cur.execute(sql_query , (query_embedding_str , k))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

# result = query_postgresql("ศูนย์ให้คำปรึกษา มพ อยู่ที่ไหน")
# print(result)

