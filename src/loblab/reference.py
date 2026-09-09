from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Deque


class RefSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(slots=True)
class RefOrder:
    order_id: int
    side: RefSide
    price_ticks: int
    quantity: int
    timestamp_ns: int = 0


@dataclass(frozen=True, slots=True)
class RefTrade:
    maker_id: int
    taker_id: int
    taker_side: RefSide
    price_ticks: int
    quantity: int
    timestamp_ns: int


class PythonOrderBook:
    """Readable pure-Python reference implementation.

    This intentionally optimises for clarity rather than speed. The C++ engine is
    the production/benchmark implementation.
    """

    def __init__(self, tick_size: float = 0.01) -> None:
        if not isfinite(tick_size) or tick_size <= 0:
            raise ValueError("tick_size must be finite and > 0")
        self.tick_size = tick_size
        self.bids: dict[int, Deque[RefOrder]] = {}
        self.asks: dict[int, Deque[RefOrder]] = {}
        self.orders: dict[int, RefOrder] = {}

    def to_ticks(self, price: float) -> int:
        if not isfinite(price) or price <= 0:
            raise ValueError("price must be finite and > 0")
        return round(price / self.tick_size)

    def from_ticks(self, ticks: int) -> float:
        return ticks * self.tick_size

    @property
    def best_bid(self) -> float | None:
        return None if not self.bids else self.from_ticks(max(self.bids))

    @property
    def best_ask(self) -> float | None:
        return None if not self.asks else self.from_ticks(min(self.asks))

    @property
    def midprice(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    def add_limit(
        self,
        order_id: int,
        side: RefSide,
        price: float,
        quantity: int,
        timestamp_ns: int = 0,
    ) -> list[RefTrade]:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if order_id in self.orders:
            raise ValueError(f"duplicate order id: {order_id}")

        ticks = self.to_ticks(price)
        remaining = quantity
        if side is RefSide.BUY:
            remaining, trades = self._match_buy(order_id, remaining, ticks, timestamp_ns)
        else:
            remaining, trades = self._match_sell(order_id, remaining, ticks, timestamp_ns)

        if remaining:
            order = RefOrder(order_id, side, ticks, remaining, timestamp_ns)
            book = self.bids if side is RefSide.BUY else self.asks
            book.setdefault(ticks, deque()).append(order)
            self.orders[order_id] = order
        return trades

    def add_market(
        self,
        order_id: int,
        side: RefSide,
        quantity: int,
        timestamp_ns: int = 0,
    ) -> list[RefTrade]:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if order_id in self.orders:
            raise ValueError(f"duplicate order id: {order_id}")

        if side is RefSide.BUY:
            _, trades = self._match_buy(order_id, quantity, None, timestamp_ns)
        else:
            _, trades = self._match_sell(order_id, quantity, None, timestamp_ns)
        return trades

    def cancel(self, order_id: int) -> bool:
        order = self.orders.pop(order_id, None)
        if order is None:
            return False
        book = self.bids if order.side is RefSide.BUY else self.asks
        level = book[order.price_ticks]
        book[order.price_ticks] = deque(item for item in level if item.order_id != order_id)
        if not book[order.price_ticks]:
            del book[order.price_ticks]
        return True

    def _match_buy(
        self,
        taker_id: int,
        remaining: int,
        limit_ticks: int | None,
        timestamp_ns: int,
    ) -> tuple[int, list[RefTrade]]:
        trades: list[RefTrade] = []
        while remaining and self.asks:
            best = min(self.asks)
            if limit_ticks is not None and best > limit_ticks:
                break
            level = self.asks[best]
            while remaining and level:
                maker = level[0]
                executed = min(remaining, maker.quantity)
                trades.append(RefTrade(maker.order_id, taker_id, RefSide.BUY, best, executed, timestamp_ns))
                remaining -= executed
                maker.quantity -= executed
                if maker.quantity == 0:
                    level.popleft()
                    del self.orders[maker.order_id]
            if not level:
                del self.asks[best]
        return remaining, trades

    def _match_sell(
        self,
        taker_id: int,
        remaining: int,
        limit_ticks: int | None,
        timestamp_ns: int,
    ) -> tuple[int, list[RefTrade]]:
        trades: list[RefTrade] = []
        while remaining and self.bids:
            best = max(self.bids)
            if limit_ticks is not None and best < limit_ticks:
                break
            level = self.bids[best]
            while remaining and level:
                maker = level[0]
                executed = min(remaining, maker.quantity)
                trades.append(RefTrade(maker.order_id, taker_id, RefSide.SELL, best, executed, timestamp_ns))
                remaining -= executed
                maker.quantity -= executed
                if maker.quantity == 0:
                    level.popleft()
                    del self.orders[maker.order_id]
            if not level:
                del self.bids[best]
        return remaining, trades
