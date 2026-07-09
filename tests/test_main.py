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
