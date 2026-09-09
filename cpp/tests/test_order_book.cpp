#include "lob/order_book.hpp"
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    lob::OrderBook book(0.01);
    book.add_limit(1, lob::Side::Buy, 100.00, 10, 1);
    book.add_limit(2, lob::Side::Buy, 100.00, 20, 2);
    book.add_limit(3, lob::Side::Sell, 100.05, 15, 3);

    assert(book.order_count() == 3);
    assert(std::abs(*book.best_bid() - 100.00) < 1e-9);
    assert(std::abs(*book.best_ask() - 100.05) < 1e-9);

    const auto trades = book.add_limit(4, lob::Side::Sell, 100.00, 12, 4);
    assert(trades.size() == 2);
    assert(trades[0].maker_id == 1 && trades[0].quantity == 10);
    assert(trades[1].maker_id == 2 && trades[1].quantity == 2);
    assert(!book.contains(1));
    assert(book.contains(2));

    std::cout << "C++ tests passed\n";
}
