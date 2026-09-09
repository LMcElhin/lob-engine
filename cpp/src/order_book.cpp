#include "lob/order_book.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace lob {

OrderBook::OrderBook(double tick_size) : tick_size_(tick_size) {
    if (!std::isfinite(tick_size_) || tick_size_ <= 0.0) {
        throw std::invalid_argument("tick_size must be finite and > 0");
    }
}

double OrderBook::tick_size() const noexcept { return tick_size_; }

PriceTicks OrderBook::to_ticks(double price) const {
    if (!std::isfinite(price) || price <= 0.0) {
        throw std::invalid_argument("price must be finite and > 0");
    }
    return static_cast<PriceTicks>(std::llround(price / tick_size_));
}

double OrderBook::from_ticks(PriceTicks ticks) const noexcept {
    return static_cast<double>(ticks) * tick_size_;
}

std::vector<Trade> OrderBook::add_limit(OrderId id, Side side, double price, Quantity quantity,
                                        TimestampNs timestamp_ns) {
    if (quantity == 0) throw std::invalid_argument("quantity must be > 0");
    if (contains(id)) throw std::invalid_argument("duplicate order id: " + std::to_string(id));

    const PriceTicks price_ticks = to_ticks(price);
    Quantity remaining = quantity;
    auto trades = side == Side::Buy
        ? match_buy(id, remaining, price_ticks, timestamp_ns)
        : match_sell(id, remaining, price_ticks, timestamp_ns);

    if (remaining > 0) rest_order(id, side, price_ticks, remaining, timestamp_ns);
    return trades;
}

std::vector<Trade> OrderBook::add_market(OrderId id, Side side, Quantity quantity,
                                         TimestampNs timestamp_ns) {
    if (quantity == 0) throw std::invalid_argument("quantity must be > 0");
    if (contains(id)) throw std::invalid_argument("duplicate order id: " + std::to_string(id));

    Quantity remaining = quantity;
    return side == Side::Buy
        ? match_buy(id, remaining, std::nullopt, timestamp_ns)
        : match_sell(id, remaining, std::nullopt, timestamp_ns);
}

bool OrderBook::cancel(OrderId id) {
    const auto found = locators_.find(id);
    if (found == locators_.end()) return false;

    const Locator locator = found->second;
    const Quantity qty = locator.iterator->quantity;

    if (locator.side == Side::Buy) {
        auto level = bids_.find(locator.price_ticks);
        if (level == bids_.end()) throw std::logic_error("corrupt bid locator");
        level->second.erase(locator.iterator);
        total_bid_quantity_ -= qty;
        if (level->second.empty()) bids_.erase(level);
    } else {
        auto level = asks_.find(locator.price_ticks);
        if (level == asks_.end()) throw std::logic_error("corrupt ask locator");
        level->second.erase(locator.iterator);
        total_ask_quantity_ -= qty;
        if (level->second.empty()) asks_.erase(level);
    }

    locators_.erase(found);
    return true;
}

std::vector<Trade> OrderBook::modify(OrderId id, double new_price, Quantity new_quantity,
                                     TimestampNs timestamp_ns) {
    if (new_quantity == 0) {
        cancel(id);
        return {};
    }

    const auto found = locators_.find(id);
    if (found == locators_.end()) throw std::invalid_argument("cannot modify unknown order id");

    const PriceTicks new_ticks = to_ticks(new_price);
    const Locator old = found->second;
    const Quantity old_qty = old.iterator->quantity;

    if (new_ticks == old.price_ticks && new_quantity <= old_qty) {
        const Quantity reduction = old_qty - new_quantity;
        old.iterator->quantity = new_quantity;
        if (timestamp_ns != 0) old.iterator->timestamp_ns = timestamp_ns;
        if (old.side == Side::Buy) total_bid_quantity_ -= reduction;
        else total_ask_quantity_ -= reduction;
        return {};
    }

    const Side side = old.side;
    cancel(id);
    return add_limit(id, side, new_price, new_quantity, timestamp_ns);
}

bool OrderBook::contains(OrderId id) const noexcept { return locators_.contains(id); }
std::size_t OrderBook::order_count() const noexcept { return locators_.size(); }
Quantity OrderBook::total_bid_quantity() const noexcept { return total_bid_quantity_; }
Quantity OrderBook::total_ask_quantity() const noexcept { return total_ask_quantity_; }

std::optional<double> OrderBook::best_bid() const {
    if (bids_.empty()) return std::nullopt;
    return from_ticks(bids_.begin()->first);
}

std::optional<double> OrderBook::best_ask() const {
    if (asks_.empty()) return std::nullopt;
    return from_ticks(asks_.begin()->first);
}

std::optional<double> OrderBook::midprice() const {
    const auto bid = best_bid();
    const auto ask = best_ask();
    if (!bid || !ask) return std::nullopt;
    return (*bid + *ask) / 2.0;
}

std::optional<double> OrderBook::spread() const {
    const auto bid = best_bid();
    const auto ask = best_ask();
    if (!bid || !ask) return std::nullopt;
    return *ask - *bid;
}

double OrderBook::imbalance(std::size_t depth) const {
    if (depth == 0) throw std::invalid_argument("depth must be > 0");
    Quantity bid_qty = 0, ask_qty = 0;
    std::size_t i = 0;
    for (const auto& [price, level] : bids_) {
        (void)price;
        if (i++ >= depth) break;
        bid_qty += sum_level(level);
    }
    i = 0;
    for (const auto& [price, level] : asks_) {
        (void)price;
        if (i++ >= depth) break;
        ask_qty += sum_level(level);
    }
    const long double total = static_cast<long double>(bid_qty) + static_cast<long double>(ask_qty);
    if (total == 0.0L) return 0.0;
    return static_cast<double>((static_cast<long double>(bid_qty) - static_cast<long double>(ask_qty)) / total);
}

Snapshot OrderBook::snapshot(std::size_t depth) const {
    if (depth == 0) throw std::invalid_argument("depth must be > 0");
    Snapshot out;
    std::size_t i = 0;
    for (const auto& [price, level] : bids_) {
        if (i++ >= depth) break;
        out.bids.push_back(PriceLevel{price, sum_level(level), level.size()});
    }
    i = 0;
    for (const auto& [price, level] : asks_) {
        if (i++ >= depth) break;
        out.asks.push_back(PriceLevel{price, sum_level(level), level.size()});
    }
    return out;
}

void OrderBook::clear() {
    bids_.clear();
    asks_.clear();
    locators_.clear();
    total_bid_quantity_ = 0;
    total_ask_quantity_ = 0;
}

std::vector<Trade> OrderBook::match_buy(OrderId taker_id, Quantity& remaining,
                                        std::optional<PriceTicks> limit_price,
                                        TimestampNs timestamp_ns) {
    std::vector<Trade> trades;
    while (remaining > 0 && !asks_.empty()) {
        auto level_it = asks_.begin();
        const PriceTicks best_price = level_it->first;
        if (limit_price && best_price > *limit_price) break;
        auto& level = level_it->second;

        while (remaining > 0 && !level.empty()) {
            auto maker_it = level.begin();
            const Quantity executed = std::min(remaining, maker_it->quantity);
            trades.push_back(Trade{maker_it->id, taker_id, Side::Buy, best_price, executed, timestamp_ns});
            remaining -= executed;
            maker_it->quantity -= executed;
            total_ask_quantity_ -= executed;
            if (maker_it->quantity == 0) {
                locators_.erase(maker_it->id);
                level.erase(maker_it);
            }
        }
        if (level.empty()) asks_.erase(level_it);
    }
    return trades;
}

std::vector<Trade> OrderBook::match_sell(OrderId taker_id, Quantity& remaining,
                                         std::optional<PriceTicks> limit_price,
                                         TimestampNs timestamp_ns) {
    std::vector<Trade> trades;
    while (remaining > 0 && !bids_.empty()) {
        auto level_it = bids_.begin();
        const PriceTicks best_price = level_it->first;
        if (limit_price && best_price < *limit_price) break;
        auto& level = level_it->second;

        while (remaining > 0 && !level.empty()) {
            auto maker_it = level.begin();
            const Quantity executed = std::min(remaining, maker_it->quantity);
            trades.push_back(Trade{maker_it->id, taker_id, Side::Sell, best_price, executed, timestamp_ns});
            remaining -= executed;
            maker_it->quantity -= executed;
            total_bid_quantity_ -= executed;
            if (maker_it->quantity == 0) {
                locators_.erase(maker_it->id);
                level.erase(maker_it);
            }
        }
        if (level.empty()) bids_.erase(level_it);
    }
    return trades;
}

void OrderBook::rest_order(OrderId id, Side side, PriceTicks price_ticks, Quantity quantity,
                           TimestampNs timestamp_ns) {
    Order order{id, side, price_ticks, quantity, timestamp_ns};
    if (side == Side::Buy) {
        auto [level_it, inserted] = bids_.try_emplace(price_ticks);
        (void)inserted;
        level_it->second.push_back(order);
        auto order_it = std::prev(level_it->second.end());
        locators_.emplace(id, Locator{side, price_ticks, order_it});
        total_bid_quantity_ += quantity;
    } else {
        auto [level_it, inserted] = asks_.try_emplace(price_ticks);
        (void)inserted;
        level_it->second.push_back(order);
        auto order_it = std::prev(level_it->second.end());
        locators_.emplace(id, Locator{side, price_ticks, order_it});
        total_ask_quantity_ += quantity;
    }
}

Quantity OrderBook::sum_level(const Level& level) noexcept {
    Quantity total = 0;
    for (const auto& order : level) total += order.quantity;
    return total;
}

}  // namespace lob
