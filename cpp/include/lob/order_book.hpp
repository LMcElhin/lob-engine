#pragma once

#include <cstdint>
#include <functional>
#include <list>
#include <map>
#include <optional>
#include <unordered_map>
#include <vector>

namespace lob {

using OrderId = std::uint64_t;
using Quantity = std::uint64_t;
using TimestampNs = std::uint64_t;
using PriceTicks = std::int64_t;

enum class Side { Buy, Sell };

struct Order {
    OrderId id{};
    Side side{Side::Buy};
    PriceTicks price_ticks{};
    Quantity quantity{};
    TimestampNs timestamp_ns{};
};

struct Trade {
    OrderId maker_id{};
    OrderId taker_id{};
    Side taker_side{Side::Buy};
    PriceTicks price_ticks{};
    Quantity quantity{};
    TimestampNs timestamp_ns{};
};

struct PriceLevel {
    PriceTicks price_ticks{};
    Quantity quantity{};
    std::size_t order_count{};
};

struct Snapshot {
    std::vector<PriceLevel> bids;
    std::vector<PriceLevel> asks;
};

class OrderBook {
public:
    explicit OrderBook(double tick_size = 0.01);

    [[nodiscard]] double tick_size() const noexcept;
    [[nodiscard]] PriceTicks to_ticks(double price) const;
    [[nodiscard]] double from_ticks(PriceTicks ticks) const noexcept;

    std::vector<Trade> add_limit(OrderId id, Side side, double price, Quantity quantity,
                                 TimestampNs timestamp_ns = 0);
    std::vector<Trade> add_market(OrderId id, Side side, Quantity quantity,
                                  TimestampNs timestamp_ns = 0);
    bool cancel(OrderId id);
    std::vector<Trade> modify(OrderId id, double new_price, Quantity new_quantity,
                              TimestampNs timestamp_ns = 0);

    [[nodiscard]] bool contains(OrderId id) const noexcept;
    [[nodiscard]] std::size_t order_count() const noexcept;
    [[nodiscard]] Quantity total_bid_quantity() const noexcept;
    [[nodiscard]] Quantity total_ask_quantity() const noexcept;
    [[nodiscard]] std::optional<double> best_bid() const;
    [[nodiscard]] std::optional<double> best_ask() const;
    [[nodiscard]] std::optional<double> midprice() const;
    [[nodiscard]] std::optional<double> spread() const;
    [[nodiscard]] double imbalance(std::size_t depth = 1) const;
    [[nodiscard]] Snapshot snapshot(std::size_t depth = 10) const;
    void clear();

private:
    using Level = std::list<Order>;
    using BidLevels = std::map<PriceTicks, Level, std::greater<PriceTicks>>;
    using AskLevels = std::map<PriceTicks, Level, std::less<PriceTicks>>;

    struct Locator {
        Side side;
        PriceTicks price_ticks;
        Level::iterator iterator;
    };

    double tick_size_;
    BidLevels bids_;
    AskLevels asks_;
    std::unordered_map<OrderId, Locator> locators_;
    Quantity total_bid_quantity_{0};
    Quantity total_ask_quantity_{0};

    std::vector<Trade> match_buy(OrderId taker_id, Quantity& remaining,
                                 std::optional<PriceTicks> limit_price,
                                 TimestampNs timestamp_ns);
    std::vector<Trade> match_sell(OrderId taker_id, Quantity& remaining,
                                  std::optional<PriceTicks> limit_price,
                                  TimestampNs timestamp_ns);
    void rest_order(OrderId id, Side side, PriceTicks price_ticks, Quantity quantity,
                    TimestampNs timestamp_ns);
    [[nodiscard]] static Quantity sum_level(const Level& level) noexcept;
};

}  // namespace lob
