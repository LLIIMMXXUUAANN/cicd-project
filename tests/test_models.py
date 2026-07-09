import pytest
from pydantic import ValidationError

from app.models import Quote, QuoteCreate


def test_quote_accepts_valid_fields():
    quote = Quote(id=1, text="Stay hungry", author="Steve Jobs")
    assert quote.id == 1
    assert quote.text == "Stay hungry"
    assert quote.author == "Steve Jobs"


def test_quote_rejects_empty_text():
    with pytest.raises(ValidationError):
        Quote(id=1, text="", author="Steve Jobs")


def test_quote_create_rejects_empty_author():
    with pytest.raises(ValidationError):
        QuoteCreate(text="Stay hungry", author="")
