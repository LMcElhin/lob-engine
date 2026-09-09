from loblab import OrderBook, Side, features_from_book
from loblab.backtest import ImbalanceStrategy, PaperExecutor


def main() -> None:
    book = OrderBook(0.01)
    strategy = ImbalanceStrategy(buy_threshold=0.40, sell_threshold=-0.40)
    executor = PaperExecutor(starting_cash=1_000.0, fee_bps=2.0)

    book.add_limit(1, Side.BUY, 99.99, 500)
    book.add_limit(2, Side.SELL, 100.01, 100)
    f = features_from_book(book, 1)
    action = strategy.decide(f.imbalance, executor.portfolio.position)
    print("step 1:", f, action, executor.execute(action, f.best_bid, f.best_ask))

    book.cancel(1)
    book.add_limit(3, Side.BUY, 99.99, 100)
    book.cancel(2)
    book.add_limit(4, Side.SELL, 100.01, 500)
    f = features_from_book(book, 1)
    action = strategy.decide(f.imbalance, executor.portfolio.position)
    print("step 2:", f, action, executor.execute(action, f.best_bid, f.best_ask))

    mark = f.midprice or 0.0
    print("portfolio:", executor.portfolio)
    print("equity:", executor.portfolio.equity(mark))


if __name__ == "__main__":
    main()
