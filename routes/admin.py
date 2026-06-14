from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class ResultInput(BaseModel):
    home_score: int
    away_score: int

class ConfirmInput(BaseModel):
    home_team_id: int
    away_team_id: int

def is_admin(current_user: dict = Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user

@router.patch("/admin/matches/{match_id}/lock")
def lock_match(match_id: int, current_user: dict = Depends(is_admin)):
    conn = get_db()
    match = conn.execute(
        "SELECT * FROM matches WHERE id = ?", (match_id,)
    ).fetchone()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    conn.execute(
        "UPDATE matches SET is_locked = 1 WHERE id = ?", (match_id,)
    )
    conn.commit()
    conn.close()
    return {"message": "Match locked"}


@router.patch("/admin/matches/{match_id}/result")
def enter_result(match_id: int, data: ResultInput, current_user: dict = Depends(is_admin)):
    conn = get_db()
    match = conn.execute(
        "SELECT * FROM matches WHERE id = ?", (match_id,)
    ).fetchone()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    conn.execute("""
        UPDATE matches SET home_score = ?, away_score = ? WHERE id = ?
    """, (data.home_score, data.away_score, match_id))

    calculate_points(conn, match_id, data.home_score, data.away_score)

    conn.commit()
    conn.close()
    return {"message": "Result entered and points calculated"}


@router.patch("/admin/matches/{match_id}/confirm")
def confirm_match(match_id: int, data: ConfirmInput, current_user: dict = Depends(is_admin)):
    conn = get_db()
    match = conn.execute(
        "SELECT * FROM matches WHERE id = ?", (match_id,)
    ).fetchone()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    conn.execute("""
        UPDATE matches 
        SET home_team_id = ?, away_team_id = ?, is_confirmed = 1,
            home_placeholder = null, away_placeholder = null
        WHERE id = ?
    """, (data.home_team_id, data.away_team_id, match_id))

    conn.commit()
    conn.close()
    return {"message": "Match confirmed"}


def calculate_points(conn, match_id: int, real_home: int, real_away: int):
    predictions = conn.execute(
        "SELECT * FROM predictions WHERE match_id = ?", (match_id,)
    ).fetchall()

    def outcome(h, a):
        return (h > a) - (h < a)   # 1 = home win, 0 = draw, -1 = away win

    for pred in predictions:
        if pred["home_score"] == real_home and pred["away_score"] == real_away:
            points = 3
        elif outcome(pred["home_score"], pred["away_score"]) == outcome(real_home, real_away):
            points = 1
        else:
            points = 0

        conn.execute(
            "UPDATE predictions SET points_earned = ? WHERE id = ?",
            (points, pred["id"])
        )
