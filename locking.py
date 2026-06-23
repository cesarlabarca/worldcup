from datetime import datetime, timedelta
from db import get_db

LOCK_BUFFER_MINUTES = 15


def lock_due_matches() -> int:
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() + timedelta(minutes=LOCK_BUFFER_MINUTES)).isoformat(timespec="seconds")
        cursor = conn.execute(
            "UPDATE matches SET is_locked = 1 WHERE is_locked = 0 AND kickoff_at <= ?",
            (cutoff,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
