import sqlite3

def get_db():
  db = "worldcup.db"
  conn = sqlite3.connect(db)
  conn.row_factory =sqlite3.Row
  return conn