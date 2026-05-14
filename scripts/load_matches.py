import sys
sys.path.append(".")

import json
from db import get_db

def load_matches():
    with open("data/matches.json") as f:
        matches = json.load(f)

    conn = get_db()

    for match in matches:
        # Group stage — look up real team IDs
        if match["home_team"] is not None:
            home_row = conn.execute(
                "SELECT id FROM teams WHERE name = ?", (match["home_team"],)
            ).fetchone()
            away_row = conn.execute(
                "SELECT id FROM teams WHERE name = ?", (match["away_team"],)
            ).fetchone()
            home_team_id = home_row["id"]
            away_team_id = away_row["id"]
            home_placeholder = None
            away_placeholder = None
        # Knockout stage — use placeholders, no real team IDs yet
        else:
            home_team_id = None
            away_team_id = None
            home_placeholder = match["home_placeholder"]
            away_placeholder = match["away_placeholder"]

        conn.execute("""
            INSERT INTO matches (
                match_number, stage, group_name,
                home_team_id, away_team_id,
                home_placeholder, away_placeholder,
                kickoff_at, is_confirmed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match["match_number"],
            match["stage"],
            match["group_name"],
            home_team_id,
            away_team_id,
            home_placeholder,
            away_placeholder,
            match["kickoff_at"],
            match["is_confirmed"]
        ))

    conn.commit()
    conn.close()
    print("Matches loaded!")

load_matches()