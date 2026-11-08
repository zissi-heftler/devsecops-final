import sqlite3
import pytest
from fastapi.testclient import TestClient
from main import app, DB_PATH, init_db


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe items table before each test for isolation."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM items")
    yield


@pytest.fixture()
def client():
    return TestClient(app)


# --- /health ---

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --- GET /items ---

def test_list_items_empty(client):
    r = client.get("/items")
    assert r.status_code == 200
    assert r.json() == []


def test_list_items_after_insert(client):
    client.post("/items", json={"name": "apple"})
    r = client.get("/items")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "apple"
    assert "id" in items[0]


# --- POST /items ---

def test_create_item_returns_201(client):
    r = client.post("/items", json={"name": "banana"})
    assert r.status_code == 201


def test_create_item_response_shape(client):
    r = client.post("/items", json={"name": "cherry"})
    body = r.json()
    assert body["name"] == "cherry"
    assert isinstance(body["id"], int)


def test_create_multiple_items(client):
    client.post("/items", json={"name": "a"})
    client.post("/items", json={"name": "b"})
    r = client.get("/items")
    assert len(r.json()) == 2


def test_create_item_missing_name(client):
    r = client.post("/items", json={})
    assert r.status_code == 422


def test_items_have_unique_ids(client):
    r1 = client.post("/items", json={"name": "x"})
    r2 = client.post("/items", json={"name": "y"})
    assert r1.json()["id"] != r2.json()["id"]
