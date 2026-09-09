import pytest
from loblab import OrderBook, Side, features_from_book


def test_features() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 99.99, 300)
    book.add_limit(2, Side.SELL, 100.01, 100)
    f = features_from_book(book, depth=1)
    assert f.midprice == pytest.approx(100.00)
    assert f.spread == pytest.approx(0.02)
    assert f.imbalance == pytest.approx(0.5)
    assert f.microprice == pytest.approx(100.005)
