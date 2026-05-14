from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from db import get_db
from auth import hash_password, verify_password, create_token, verify_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ---------- helpers ----------

def get_user_from_cookie(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    return verify_token(token)


# ---------- auth pages ----------

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_user_from_cookie(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"user": None})


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html",
            {"user": None, "error": "Invalid username or password"}
        )

    token = create_token({"sub": user["username"], "is_admin": user["is_admin"]})
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("token", token, httponly=True, max_age=7 * 24 * 60 * 60)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if get_user_from_cookie(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"user": None})


@router.post("/register")
def register_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return templates.TemplateResponse(
            request, "register.html",
            {"user": None, "error": "Username already taken"}
        )

    hashed = hash_password(password)
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hashed)
    )
    conn.commit()
    conn.close()

    token = create_token({"sub": username, "is_admin": 0})
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("token", token, httponly=True, max_age=7 * 24 * 60 * 60)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token")
    return response


# ---------- home ----------

@router.get("/", response_class=HTMLResponse)
def home(request: Request, stage: str = "group"):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    conn = get_db()
    me = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()

    matches_raw = conn.execute("""
        SELECT m.*,
               ht.name AS home_name, ht.flag_url AS home_flag,
               at.name AS away_name, at.flag_url AS away_flag,
               p.home_score AS my_home, p.away_score AS my_away,
               p.points_earned AS points_earned
        FROM matches m
        LEFT JOIN teams ht ON m.home_team_id = ht.id
        LEFT JOIN teams at ON m.away_team_id = at.id
        LEFT JOIN predictions p ON p.match_id = m.id AND p.user_id = ?
        WHERE m.stage = ?
        ORDER BY m.match_number
    """, (me["id"], stage)).fetchall()

    matches = []
    for m in matches_raw:
        d = dict(m)
        d["home_display"] = d["home_name"] or d["home_placeholder"] or "TBD"
        d["away_display"] = d["away_name"] or d["away_placeholder"] or "TBD"
        d["real_home"] = d["home_score"]
        d["real_away"] = d["away_score"]
        d["has_prediction"] = d["my_home"] is not None
        matches.append(d)

    conn.close()

    return templates.TemplateResponse(request, "home.html", {
        "user": user["sub"],
        "active": "home",
        "stage": stage,
        "matches": matches
    })


# ---------- predict ----------

@router.post("/predict")
def predict(
    request: Request,
    match_id: int = Form(...),
    home_score: int = Form(...),
    away_score: int = Form(...)
):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    conn = get_db()
    me = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()
    match = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()

    if not match or match["is_locked"] or not match["is_confirmed"]:
        stage = match["stage"] if match else "group"
        conn.close()
        return RedirectResponse(f"/?stage={stage}", status_code=302)

    existing = conn.execute(
        "SELECT id FROM predictions WHERE user_id = ? AND match_id = ?",
        (me["id"], match_id)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE predictions SET home_score = ?, away_score = ? WHERE id = ?",
            (home_score, away_score, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO predictions (user_id, match_id, home_score, away_score) VALUES (?, ?, ?, ?)",
            (me["id"], match_id, home_score, away_score)
        )

    conn.commit()
    stage = match["stage"]
    conn.close()
    return RedirectResponse(f"/?stage={stage}", status_code=302)


# ---------- my predictions ----------

@router.get("/my-predictions", response_class=HTMLResponse)
def my_predictions(request: Request):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    conn = get_db()
    me = conn.execute("SELECT id FROM users WHERE username = ?", (user["sub"],)).fetchone()

    rows = conn.execute("""
        SELECT p.*, m.match_number, m.stage, m.kickoff_at,
               m.home_score AS real_home, m.away_score AS real_away,
               m.home_placeholder, m.away_placeholder,
               ht.name AS home_name, ht.flag_url AS home_flag,
               at.name AS away_name, at.flag_url AS away_flag
        FROM predictions p
        JOIN matches m ON p.match_id = m.id
        LEFT JOIN teams ht ON m.home_team_id = ht.id
        LEFT JOIN teams at ON m.away_team_id = at.id
        WHERE p.user_id = ?
        ORDER BY m.kickoff_at DESC
    """, (me["id"],)).fetchall()

    predictions = []
    total = exact = correct = points = 0
    for row in rows:
        d = dict(row)
        d["home_display"] = d["home_name"] or d["home_placeholder"] or "TBD"
        d["away_display"] = d["away_name"] or d["away_placeholder"] or "TBD"
        d["my_home"] = d["home_score"]
        d["my_away"] = d["away_score"]

        if d["points_earned"] is not None:
            if d["points_earned"] == 3:
                d["result_class"] = "exact"
                exact += 1
                points += 3
            elif d["points_earned"] == 1:
                d["result_class"] = "correct"
                correct += 1
                points += 1
            else:
                d["result_class"] = "wrong"
        else:
            d["result_class"] = "pending"
        total += 1
        predictions.append(d)

    conn.close()
    return templates.TemplateResponse(request, "my_predictions.html", {
        "user": user["sub"],
        "active": "mine",
        "predictions": predictions,
        "stats": {"total": total, "exact": exact, "correct": correct, "points": points}
    })


# ---------- leaderboard ----------

@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    conn = get_db()
    rows = conn.execute("""
        SELECT u.username, COALESCE(SUM(p.points_earned), 0) AS total_points
        FROM users u
        LEFT JOIN predictions p ON p.user_id = u.id
        GROUP BY u.id
        ORDER BY total_points DESC, u.username ASC
    """).fetchall()
    conn.close()

    return templates.TemplateResponse(request, "leaderboard.html", {
        "user": user["sub"],
        "active": "leaderboard",
        "rows": [dict(r) for r in rows]
    })


# ---------- standings ----------

@router.get("/standings", response_class=HTMLResponse)
def standings_page(request: Request):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    conn = get_db()

    teams = conn.execute(
        "SELECT id, name, group_name, flag_url FROM teams WHERE group_name IS NOT NULL ORDER BY group_name, name"
    ).fetchall()

    matches = conn.execute("""
        SELECT home_team_id, away_team_id, home_score, away_score
        FROM matches
        WHERE stage = 'group'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """).fetchall()

    stats = {}
    for t in teams:
        stats[t["id"]] = {
            "id": t["id"],
            "name": t["name"],
            "flag_url": t["flag_url"],
            "group": t["group_name"],
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0
        }

    for m in matches:
        h = stats.get(m["home_team_id"])
        a = stats.get(m["away_team_id"])
        if not h or not a:
            continue
        h["played"] += 1
        a["played"] += 1
        h["gf"] += m["home_score"]; h["ga"] += m["away_score"]
        a["gf"] += m["away_score"]; a["ga"] += m["home_score"]
        if m["home_score"] > m["away_score"]:
            h["wins"] += 1; h["points"] += 3
            a["losses"] += 1
        elif m["home_score"] < m["away_score"]:
            a["wins"] += 1; a["points"] += 3
            h["losses"] += 1
        else:
            h["draws"] += 1; h["points"] += 1
            a["draws"] += 1; a["points"] += 1

    for t in stats.values():
        t["gd"] = t["gf"] - t["ga"]

    groups = {}
    for t in stats.values():
        groups.setdefault(t["group"], []).append(t)

    group_list = []
    for name in sorted(groups.keys()):
        team_list = sorted(
            groups[name],
            key=lambda x: (-x["points"], -x["gd"], -x["gf"], x["name"])
        )
        group_list.append({"name": name, "teams": team_list})

    conn.close()

    return templates.TemplateResponse(request, "standings.html", {
        "user": user["sub"],
        "active": "standings",
        "groups": group_list
    })