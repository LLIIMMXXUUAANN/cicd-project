from app.models import QuoteCreate
from app.store import QuoteStore


def test_new_store_is_empty():
    store = QuoteStore()
    assert store.list() == []


def test_create_assigns_sequential_ids():
    store = QuoteStore()
    first = store.create(QuoteCreate(text="First", author="A"))
    second = store.create(QuoteCreate(text="Second", author="B"))
    assert first.id == 1
    assert second.id == 2


def test_create_adds_to_list():
    store = QuoteStore()
    store.create(QuoteCreate(text="First", author="A"))
    assert len(store.list()) == 1


def test_get_returns_matching_quote():
    store = QuoteStore()
    created = store.create(QuoteCreate(text="First", author="A"))
    found = store.get(created.id)
    assert found is not None
    assert found.text == "First"


def test_get_returns_none_when_missing():
    store = QuoteStore()
    assert store.get(999) is None
