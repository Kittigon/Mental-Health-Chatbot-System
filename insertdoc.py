from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import psycopg2
from dotenv import load_dotenv
import os
import requests


# Load environment variables
load_dotenv()

#env
SupabaseUrl = os.getenv("DATABASE_URL")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")


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


def add_document(text):
    embedding = get_embedding(text)
    cur.execute("INSERT INTO documents (content , embedding) VALUES (%s , %s)", (text, embedding))
    conn.commit()


for chunk in chunks:
    add_document(chunk.page_content)

cur.close()
conn.close()
print("Documents inserted successfully.")
