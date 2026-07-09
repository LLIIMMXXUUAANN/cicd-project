from fastapi import Depends, FastAPI

from app.models import Quote
from app.store import QuoteStore

app = FastAPI()

_store = QuoteStore()


def get_store() -> QuoteStore:
    return _store


@app.get("/quotes")
def list_quotes(store: QuoteStore = Depends(get_store)) -> list[Quote]:
    return store.list()
