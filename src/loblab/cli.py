from __future__ import annotations

from . import OrderBook, Side, features_from_book


def main() -> None:
    book = OrderBook(0.01)
    book.add_limit(1, Side.BUY, 99.99, 100, 1)
    book.add_limit(2, Side.BUY, 99.98, 150, 2)
    book.add_limit(3, Side.SELL, 100.01, 80, 3)
    book.add_limit(4, Side.SELL, 100.02, 120, 4)

    print("Initial book")
    print(f"best bid : {book.best_bid:.2f}")
    print(f"best ask : {book.best_ask:.2f}")
    print(f"midprice : {book.midprice:.2f}")
    print(f"spread   : {book.spread:.2f}")

    features = features_from_book(book, depth=2)
    print(f"imbalance: {features.imbalance:.3f}")
    print(f"microprice: {features.microprice:.5f}")

    trades = book.add_market(10, Side.BUY, 90, 5)
    print("\nMarket buy 90:")
    for trade in trades:
        print(
            f"maker={trade.maker_id} taker={trade.taker_id} "
            f"price={book.from_ticks(trade.price_ticks):.2f} qty={trade.quantity}"
        )


if __name__ == "__main__":
    main()
