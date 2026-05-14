from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from db import get_db
from routes.auth import router as auth_router
from routes.predictions import router as predictions_router
from routes.admin import router as admin_router
from routes.frontend import router as frontend_router

app = FastAPI()

# Static files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Frontend pages first so / renders the home page
app.include_router(frontend_router)

# Then your existing JSON API routes (under /api)
app.include_router(auth_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/api/matches")
def matches_api():
    conn = get_db()
    data = conn.execute("SELECT * FROM matches").fetchall()
    conn.close()
    return [dict(row) for row in data]


@app.get("/api/leaderboard")
def leaderboard_api():
    conn = get_db()
    data = conn.execute("""
        SELECT u.username, SUM(p.points_earned) AS total_points
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        GROUP BY p.user_id
        ORDER BY total_points DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in data]