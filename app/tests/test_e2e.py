"""
E2e smoke tests — run against a live service, not the TestClient.

Requires the app to be reachable at E2E_BASE_URL (default http://localhost:8080).
In cd.yml this is satisfied by `kubectl port-forward svc/items-api -n dev 8080:80`.
These tests are marked `e2e` and excluded from the normal `pytest` run via pytest.ini.
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8080")


@pytest.mark.e2e
def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.e2e
def test_create_item():
    r = requests.post(f"{BASE_URL}/items", json={"name": "smoke-test-item"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "smoke-test-item"
    assert isinstance(body["id"], int)


@pytest.mark.e2e
def test_list_items():
    # Seed one item then confirm the list endpoint returns a non-empty list.
    requests.post(f"{BASE_URL}/items", json={"name": "smoke-list-item"})
    r = requests.get(f"{BASE_URL}/items")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1
