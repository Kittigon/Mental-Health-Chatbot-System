from sentence_transformers import SentenceTransformer
import psycopg2

embedder = SentenceTransformer("BAAI/bge-m3")

def query_postgresql(query_text , k=3) :
    conn = psycopg2.connect(
    dbname="mydb",
    user = "admin",
    password = "1234",
    host = "localhost",
    port = "5432"
    )

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

