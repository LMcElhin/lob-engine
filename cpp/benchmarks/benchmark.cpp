#include "lob/order_book.hpp"
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>

int main(int argc, char** argv) {
    std::uint64_t n = 1'000'000;
    if (argc > 1) n = std::stoull(argv[1]);

    lob::OrderBook book(0.01);
    std::mt19937_64 rng(42);
    std::uniform_int_distribution<int> side_dist(0, 1);
    std::uniform_int_distribution<int> offset_dist(0, 10);
    std::uniform_int_distribution<int> qty_dist(1, 100);

    const auto start = std::chrono::steady_clock::now();
    for (std::uint64_t i = 1; i <= n; ++i) {
        const auto side = side_dist(rng) == 0 ? lob::Side::Buy : lob::Side::Sell;
        const double price = side == lob::Side::Buy
            ? 99.99 - static_cast<double>(offset_dist(rng)) * 0.01
            : 100.01 + static_cast<double>(offset_dist(rng)) * 0.01;
        book.add_limit(i, side, price, static_cast<lob::Quantity>(qty_dist(rng)), i);
    }
    const auto end = std::chrono::steady_clock::now();
    const double seconds = std::chrono::duration<double>(end - start).count();

    std::cout << std::fixed << std::setprecision(2)
              << "events=" << n << '\n'
              << "seconds=" << seconds << '\n'
              << "events_per_second=" << static_cast<double>(n) / seconds << '\n'
              << "resting_orders=" << book.order_count() << '\n';
}
