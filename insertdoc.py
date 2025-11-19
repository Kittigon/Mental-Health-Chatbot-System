from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import psycopg2
from dotenv import load_dotenv
import os   

# Load environment variables
load_dotenv()

#env
SupabaseUrl = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


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

embedder = SentenceTransformer("BAAI/bge-m3")

def add_document(text):
    embedding = embedder.encode(text).tolist()
    cur.execute("INSERT INTO documents (content , embedding) VALUES (%s , %s)" , (text, embedding))
    conn.commit()


for i, chunk in enumerate(chunks):
    # print(f"chunk : {i+1} , {chunk.page_content}")
    add_document(chunk.page_content)


cur.close()
conn.close()
print("Documents inserted successfully.")