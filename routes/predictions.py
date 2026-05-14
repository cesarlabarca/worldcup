from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class PredictionInput(BaseModel):
    match_id: int
    home_score: int
    away_score: int

@router.post("/predictions")
def prediction(data: PredictionInput, current_user: dict = Depends(get_current_user)):
    conn = get_db()

    matchinfo = conn.execute(
        "SELECT * FROM matches WHERE id = ?", (data.match_id,)
    ).fetchone()

    if not matchinfo:
        raise HTTPException(status_code=404, detail="Match not found")

    if matchinfo["is_locked"] == 1:
        raise HTTPException(status_code=400, detail="Match locked")

    if matchinfo["is_confirmed"] == 0:
        raise HTTPException(status_code=400, detail="Match not confirmed yet")

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (current_user["sub"],)
    ).fetchone()

    existing = conn.execute(
        "SELECT id FROM predictions WHERE user_id = ? AND match_id = ?",
        (user["id"], data.match_id)
    ).fetchone()

    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Already predicted this match")

    conn.execute("""
        INSERT INTO predictions (user_id, match_id, home_score, away_score)
        VALUES (?, ?, ?, ?)
    """, (user["id"], data.match_id, data.home_score, data.away_score))

    conn.commit()
    conn.close()
    return {"message": "Prediction submitted!"}

@router.get("/predictions/me")
def my_predictions(current_user: dict = Depends(get_current_user)):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (current_user["sub"],)
    ).fetchone()

    data = conn.execute("""
        SELECT p.*, m.match_number, m.stage, m.kickoff_at, 
               m.home_team_id, m.away_team_id,
               m.home_placeholder, m.away_placeholder
        FROM predictions p
        JOIN matches m ON p.match_id = m.id
        WHERE p.user_id = ?
    """, (user["id"],)).fetchall()

    conn.close()
    return [dict(row) for row in data]