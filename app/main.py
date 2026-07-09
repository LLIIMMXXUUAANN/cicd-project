from fastapi import Depends, FastAPI, HTTPException

from app.models import Quote, QuoteCreate
from app.store import QuoteStore

app = FastAPI()

_store = QuoteStore()


def get_store() -> QuoteStore:
    return _store


@app.get("/quotes")
def list_quotes(store: QuoteStore = Depends(get_store)) -> list[Quote]:
    return store.list()


@app.post("/quotes", status_code=201)
def create_quote(payload: QuoteCreate, store: QuoteStore = Depends(get_store)) -> Quote:
    return store.create(payload)


@app.get("/quotes/{quote_id}")
def get_quote(quote_id: int, store: QuoteStore = Depends(get_store)) -> Quote:
    quote = store.get(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
