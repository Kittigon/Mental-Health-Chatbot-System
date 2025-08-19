from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import psycopg2
from dotenv import load_dotenv
import os   

# Load environment variables
load_dotenv()

SupabaseUrl = os.getenv("DATABASE_URL")


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