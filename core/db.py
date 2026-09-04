import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

db_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)


@contextmanager
def get_cursor(commit=False):
    """Checkout a pooled connection/cursor and always return it, even on error."""
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        try:
            yield cur
            if commit:
                conn.commit()
        finally:
            cur.close()
    finally:
        db_pool.putconn(conn)
