import sys
sys.path.append(".")

import json
from db import get_db

def load_teams():
  with open("data/teams.json") as f:
    teams = json.load(f)
  conn = get_db()
  for team in teams:
    conn.execute("""
    
    INSERT INTO teams (name, group_name, flag_url)
    VALUES (?, ?, ?)
""", (team["name"], team["group_name"], team["flag_url"]))
  conn.commit()
  conn.close()

load_teams()