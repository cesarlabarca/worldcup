from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from db import get_db
from auth import hash_password, verify_password, create_token
from pydantic import BaseModel

router = APIRouter()

class RegisterInput(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(data: RegisterInput):
    conn = get_db()
    
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?", (data.username,)
    ).fetchone()
    
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed = hash_password(data.password)
    
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (data.username, hashed)
    )
    conn.commit()
    conn.close()
    return {"message": "User created successfully"}


@router.post("/login")
def login(data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (data.username,)
    ).fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not verify_password(data.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_token({"sub": user["username"], "is_admin": user["is_admin"]})
    conn.close()
    return {"access_token": token, "token_type": "bearer"}