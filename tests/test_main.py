import pytest
from fastapi.testclient import TestClient

from app.main import app, get_store
from app.store import QuoteStore


@pytest.fixture
def client():
    fresh_store = QuoteStore()
    app.dependency_overrides[get_store] = lambda: fresh_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_quotes_empty(client):
    response = client.get("/quotes")
    assert response.status_code == 200
    assert response.json() == []


def test_create_quote_returns_201_and_assigns_id(client):
    response = client.post("/quotes", json={"text": "Just do it", "author": "Nike"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["text"] == "Just do it"
    assert body["author"] == "Nike"


def test_created_quote_appears_in_list(client):
    client.post("/quotes", json={"text": "Move fast", "author": "Meta"})
    response = client.get("/quotes")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_quote_by_id_found(client):
    create_response = client.post("/quotes", json={"text": "Ship it", "author": "Amazon"})
    quote_id = create_response.json()["id"]
    response = client.get(f"/quotes/{quote_id}")
    assert response.status_code == 200
    assert response.json()["text"] == "Ship it"


def test_get_quote_by_id_not_found(client):
    response = client.get("/quotes/999")
    assert response.status_code == 404


def test_create_quote_rejects_empty_text(client):
    response = client.post("/quotes", json={"text": "", "author": "Nike"})
    assert response.status_code == 422


def test_create_quote_rejects_missing_author(client):
    response = client.post("/quotes", json={"text": "Just do it"})
    assert response.status_code == 422
