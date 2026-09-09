import pytest
from loblab import OrderBook, Side


def test_price_time_priority() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 100.00, 10, 1)
    book.add_limit(2, Side.BUY, 100.00, 20, 2)
    trades = book.add_limit(3, Side.SELL, 100.00, 12, 3)
    assert [(t.maker_id, t.quantity) for t in trades] == [(1, 10), (2, 2)]
    assert not book.contains(1)
    assert book.contains(2)
    assert book.total_bid_quantity == 18


def test_better_price_executes_first() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.SELL, 100.02, 10)
    book.add_limit(2, Side.SELL, 100.01, 10)
    trades = book.add_market(3, Side.BUY, 15)
    assert [(book.from_ticks(t.price_ticks), t.quantity) for t in trades] == [
        (100.01, 10), (100.02, 5)
    ]


def test_non_marketable_limit_rests() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.SELL, 100.05, 10)
    trades = book.add_limit(2, Side.BUY, 100.00, 12)
    assert trades == []
    assert book.best_bid == pytest.approx(100.00)
    assert book.best_ask == pytest.approx(100.05)
    assert book.order_count == 2


def test_marketable_limit_partially_rests() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.SELL, 100.00, 5)
    trades = book.add_limit(2, Side.BUY, 100.01, 8)
    assert len(trades) == 1
    assert trades[0].quantity == 5
    assert book.best_bid == pytest.approx(100.01)
    assert book.total_bid_quantity == 3


def test_cancel() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 100.00, 10)
    assert book.cancel(1)
    assert not book.cancel(1)
    assert book.best_bid is None


def test_modify_reduction_preserves_position() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 100.00, 10, 1)
    book.add_limit(2, Side.BUY, 100.00, 10, 2)
    book.modify(1, 100.00, 5, 3)
    trades = book.add_market(3, Side.SELL, 6, 4)
    assert [(t.maker_id, t.quantity) for t in trades] == [(1, 5), (2, 1)]


def test_modify_price_loses_priority() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 100.00, 10, 1)
    book.add_limit(2, Side.BUY, 100.00, 10, 2)
    book.modify(1, 99.99, 10, 3)
    book.modify(1, 100.00, 10, 4)
    trades = book.add_market(3, Side.SELL, 1, 5)
    assert trades[0].maker_id == 2


def test_duplicate_id_rejected() -> None:
    book = OrderBook()
    book.add_limit(1, Side.BUY, 100.0, 1)
    with pytest.raises(ValueError):
        book.add_limit(1, Side.SELL, 101.0, 1)
