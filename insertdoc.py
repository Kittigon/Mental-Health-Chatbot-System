from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import psycopg2
from dotenv import load_dotenv
import os   

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid
import requests


# Load environment variables
load_dotenv()

#env
SupabaseUrl = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# # สร้างตาราง
# conn = psycopg2.connect(
#     dbname = DB_NAME,
#     user = DB_USER,
#     password = DB_PASSWORD ,
#     host = DB_HOST ,
#     port  = DB_PORT
# )

# cur = conn.cursor()
# cur.execute("""
#     CREATE TABLE documents (
#     id SERIAL PRIMARY KEY,
#     content TEXT,
#     embedding vector(1024)  
#     );
# """)
# conn.commit()
# cur.close()
# conn.close()

# print("ตาราง Document ถูกสร้างเรียบร้อยแล้ว")

def get_embedding(text: str) -> list[float]:
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    )

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {"text": [text]}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    return data["result"]["data"][0]


loader = CSVLoader("./public/Data.csv", encoding="utf-8")
rows = loader.load()


docs = []
for row in rows:
    metadata = row.metadata
    content = row.page_content.strip()
    docs.append(Document(page_content=content, metadata=metadata))

    
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = text_splitter.split_documents(docs)

conn = psycopg2.connect(SupabaseUrl)

cur = conn.cursor()

# embedder = SentenceTransformer("BAAI/bge-m3")

def add_document(text):
    embedding = get_embedding(text)
    cur.execute("INSERT INTO documents (content , embedding) VALUES (%s , %s)" , (text, embedding))
    conn.commit()


for i, chunk in enumerate(chunks):
    # print(f"chunk : {i+1} , {chunk.page_content}")
    add_document(chunk.page_content)


cur.close()
conn.close()
print("Documents inserted successfully.")

#===========================================================================================

# client = QdrantClient(
#     url=os.getenv("QDRANT_API_URL"),
#     api_key=os.getenv("QDRANT_API_KEY")  
# )


# # client.recreate_collection(
# #     collection_name="documents",
# #     vectors_config=VectorParams(
# #         size=1024,        
# #         distance=Distance.COSINE
# #     )
# # )

# loader = CSVLoader("./public/Data (1).csv", encoding="utf-8")
# docs = loader.load()

# # =========================
# # Chunk
# # =========================
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=500,
#     chunk_overlap=100
# )

# chunks = []
# for d in docs:
#     chunks.extend(text_splitter.split_text(d.page_content))

# print(f"Total chunks: {len(chunks)}")

# # =========================
# # Insert into Qdrant
# # =========================
# points = []

# for chunk in chunks:
#     embedding = get_embedding(chunk)

#     points.append(
#         PointStruct(
#             id=str(uuid.uuid4()),
#             vector=embedding,
#             payload={
#                 "content": chunk,
#                 "source": "csv",
#                 "lang": "th",
#                 "category": "general"
#             }
#         )
#     )

# client.upsert(
#     collection_name="documents",
#     points=points
# )

# print(f"Inserted {len(points)} vectors into Qdrant")