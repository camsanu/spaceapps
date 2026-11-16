import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import stats  # stats.py, in the same folder

DB = "app.db"

# This server no longer creates the database. Build it first with:
#     python generate_data.py --db app.db --reset
# (opening a missing file with sqlite3 would silently create an empty app.db)
if not Path(DB).exists():
    raise RuntimeError(f"{DB} not found. Create it first: python generate_data.py --db {DB} --reset")

stats.DB_PATH = DB  # the stats endpoints read the same database file


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],  # the dashboard sends an X-User-Id header
)

app.include_router(stats.router)  # /api/stats/summary, /metric/{key}, /heart-rate, /radiation


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(creds: LoginIn):
    print("LOGIN ATTEMPT:", repr(creds.username), repr(creds.password))
    conn = get_conn()
    row = conn.execute("SELECT id, username, password FROM userlog WHERE username = ?",
                       (creds.username,)).fetchone()
    conn.close()
    if row is None or row["password"] != creds.password:  # plain-text compare, as in your prototype
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"id": row["id"], "username": row["username"]}


class userlog_In(BaseModel):
    username: str


@app.get("/userlog")
def list_userlog():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM userlog").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/userlog")
def add_userlog(userlog: userlog_In):
    conn = get_conn()
    cur = conn.execute("INSERT INTO userlog (username) VALUES (?)", (userlog.username,))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "title": userlog.username}
