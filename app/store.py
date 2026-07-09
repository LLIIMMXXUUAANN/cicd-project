from app.models import Quote, QuoteCreate


class QuoteStore:
    def __init__(self) -> None:
        self._quotes: list[Quote] = []
        self._next_id = 1

    def list(self) -> list[Quote]:
        return self._quotes

    def get(self, quote_id: int) -> Quote | None:
        return next((q for q in self._quotes if q.id == quote_id), None)

    def create(self, payload: QuoteCreate) -> Quote:
        quote = Quote(id=self._next_id, text=payload.text, author=payload.author)
        self._quotes.append(quote)
        self._next_id += 1
        return quote
