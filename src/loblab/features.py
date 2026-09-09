from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class LevelLike(Protocol):
    price_ticks: int
    quantity: int


class SnapshotLike(Protocol):
    bids: Sequence[LevelLike]
    asks: Sequence[LevelLike]


@dataclass(frozen=True, slots=True)
class BookFeatures:
    best_bid: float | None
    best_ask: float | None
    midprice: float | None
    spread: float | None
    imbalance: float
    microprice: float | None
    bid_depth: int
    ask_depth: int


def features_from_snapshot(snapshot: SnapshotLike, tick_size: float) -> BookFeatures:
    bids = snapshot.bids
    asks = snapshot.asks
    best_bid = bids[0].price_ticks * tick_size if bids else None
    best_ask = asks[0].price_ticks * tick_size if asks else None

    bid_depth = sum(level.quantity for level in bids)
    ask_depth = sum(level.quantity for level in asks)
    total_depth = bid_depth + ask_depth
    imbalance = 0.0 if total_depth == 0 else (bid_depth - ask_depth) / total_depth

    midprice = spread = microprice = None
    if best_bid is not None and best_ask is not None:
        midprice = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        top_bid_qty = bids[0].quantity
        top_ask_qty = asks[0].quantity
        top_total = top_bid_qty + top_ask_qty
        if top_total:
            microprice = (best_ask * top_bid_qty + best_bid * top_ask_qty) / top_total

    return BookFeatures(
        best_bid=best_bid,
        best_ask=best_ask,
        midprice=midprice,
        spread=spread,
        imbalance=imbalance,
        microprice=microprice,
        bid_depth=bid_depth,
        ask_depth=ask_depth,
    )


def features_from_book(book: object, depth: int = 5) -> BookFeatures:
    snapshot = book.snapshot(depth)
    return features_from_snapshot(snapshot, book.tick_size)
