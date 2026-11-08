import os
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="items-api")

DB_PATH = os.environ.get("DB_PATH", "items.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
        )


init_db()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class ItemIn(BaseModel):
    name: str


class ItemOut(BaseModel):
    id: int
    name: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items", response_model=list[ItemOut])
def list_items():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, name FROM items").fetchall()
    return [dict(r) for r in rows]


@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemIn):
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO items (name) VALUES (?)", (item.name,))
        return {"id": cur.lastrowid, "name": item.name}
