import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return PostgresWrapper(conn)
    else:
        conn = sqlite3.connect("worldcup.db")
        conn.row_factory = sqlite3.Row
        return conn


class PostgresWrapper:
    """Makes psycopg2 behave like sqlite3 — same .execute() interface."""
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def execute(self, query, params=None):
        # Convert SQLite ? placeholders to PostgreSQL %s
        query = query.replace("?", "%s")
        if params is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, params)
        return self.cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()