from loblab.reference import PythonOrderBook, RefSide


def test_python_reference_fifo() -> None:
    book = PythonOrderBook(0.01)
    book.add_limit(1, RefSide.BUY, 100.00, 10)
    book.add_limit(2, RefSide.BUY, 100.00, 20)
    trades = book.add_limit(3, RefSide.SELL, 100.00, 12)
    assert [(t.maker_id, t.quantity) for t in trades] == [(1, 10), (2, 2)]
