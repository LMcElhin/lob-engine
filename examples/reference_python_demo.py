from loblab.reference import PythonOrderBook, RefSide

book = PythonOrderBook(0.01)
book.add_limit(1, RefSide.BUY, 100.00, 10)
book.add_limit(2, RefSide.BUY, 100.00, 20)
book.add_limit(3, RefSide.SELL, 100.05, 15)

for trade in book.add_limit(4, RefSide.SELL, 100.00, 12):
    print(trade)
print("best bid:", book.best_bid)
print("best ask:", book.best_ask)
