"""Streaming order-level replay. Equal timestamps retain input row order."""
from __future__ import annotations

import argparse
import csv
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path

from . import OrderBook, Side
from .features import BookFeatures, features_from_book

COLUMNS = ("timestamp_ns", "event_type", "order_id", "side", "price", "quantity")


@dataclass(frozen=True, slots=True)
class Event:
    timestamp_ns: int
    event_type: str
    order_id: int
    side: str = ""
    price: float | None = None
    quantity: int | None = None

    def __post_init__(self) -> None:
        for name in ("timestamp_ns", "order_id"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value < 2**64:
                raise ValueError(f"{name} must be a uint64")

        if self.event_type not in {"LIMIT", "MARKET", "CANCEL", "MODIFY"}:
            raise ValueError(f"unknown event_type: {self.event_type}")

        if self.event_type in {"LIMIT", "MARKET"} and self.side not in {"BUY", "SELL"}:
            raise ValueError("LIMIT/MARKET require BUY or SELL side")

        if self.event_type in {"LIMIT", "MODIFY"}:
            if self.price is None or not isfinite(self.price) or self.price <= 0:
                raise ValueError("LIMIT/MODIFY require finite positive price")

        if self.event_type != "CANCEL":
            if type(self.quantity) is not int or not 0 < self.quantity < 2**64:
                raise ValueError("quantity must be a positive uint64")

        if self.event_type in {"CANCEL", "MODIFY"} and self.side:
            raise ValueError("CANCEL/MODIFY side must be blank")

        if self.event_type in {"CANCEL", "MARKET"} and self.price is not None:
            raise ValueError("CANCEL/MARKET price must be blank")

        if self.event_type == "CANCEL" and self.quantity is not None:
            raise ValueError("CANCEL quantity must be blank")


def read_events(path: str | Path) -> Iterator[Event]:
    """Validate rows lazily; report physical CSV line numbers on failure."""
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)

        if reader.fieldnames != list(COLUMNS):
            raise ValueError(f"CSV header must be {','.join(COLUMNS)}")

        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of columns")

                yield Event(
                    timestamp_ns=int(row["timestamp_ns"]),
                    event_type=row["event_type"],
                    order_id=int(row["order_id"]),
                    side=row["side"],
                    price=float(row["price"]) if row["price"] else None,
                    quantity=int(row["quantity"]) if row["quantity"] else None,
                )
            except (ValueError, TypeError) as exc:
                raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ReplayResult:
    event: Event
    trades: tuple
    features: BookFeatures


class Replayer:
    """Replay against a fresh matching book.

    Results describe the book AFTER each event. Previously applied events remain
    applied on failure; restart with a fresh instance to retry.
    """

    def __init__(self, tick_size: float = 0.01, depth: int = 5) -> None:
        if type(depth) is not int or depth <= 0:
            raise ValueError("depth must be a positive integer")

        self.book = OrderBook(tick_size)
        self.depth = depth
        self._last_timestamp = -1

    def apply(self, event: Event) -> ReplayResult:
        if event.timestamp_ns < self._last_timestamp:
            raise ValueError("timestamps must be nondecreasing")

        book = self.book

        if event.event_type in {"CANCEL", "MODIFY"} and not book.contains(event.order_id):
            raise ValueError(f"unknown resting order id: {event.order_id}")

        if event.event_type == "LIMIT":
            trades = book.add_limit(
                event.order_id,
                getattr(Side, event.side),
                event.price,
                event.quantity,
                event.timestamp_ns,
            )
        elif event.event_type == "MARKET":
            trades = book.add_market(
                event.order_id,
                getattr(Side, event.side),
                event.quantity,
                event.timestamp_ns,
            )
        elif event.event_type == "MODIFY":
            trades = book.modify(
                event.order_id,
                event.price,
                event.quantity,
                event.timestamp_ns,
            )
        else:
            book.cancel(event.order_id)
            trades = []

        self._last_timestamp = event.timestamp_ns

        return ReplayResult(
            event,
            tuple(trades),
            features_from_book(book, self.depth),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tick-size", type=float, default=0.01)
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()

    replay = Replayer(args.tick_size, args.depth)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    feature_columns = [
        "event_index",
        "timestamp_ns",
        *BookFeatures.__dataclass_fields__,
    ]
    trade_columns = [
        "event_index",
        "timestamp_ns",
        "maker_id",
        "taker_id",
        "side",
        "price_ticks",
        "quantity",
    ]

    with (args.output_dir / "features.csv").open("w", newline="") as fs, (
        args.output_dir / "trades.csv"
    ).open("w", newline="") as ts:
        features = csv.DictWriter(fs, feature_columns)
        trades = csv.DictWriter(ts, trade_columns)
        features.writeheader()
        trades.writeheader()

        count = 0

        for count, event in enumerate(read_events(args.input), start=1):
            try:
                result = replay.apply(event)
            except (ValueError, OverflowError) as exc:
                parser.exit(2, f"event {count}: {exc}\n")

            features.writerow({
                "event_index": count,
                "timestamp_ns": event.timestamp_ns,
                **asdict(result.features),
            })

            for trade in result.trades:
                trades.writerow({
                    "event_index": count,
                    "timestamp_ns": trade.timestamp_ns,
                    "maker_id": trade.maker_id,
                    "taker_id": trade.taker_id,
                    "side": trade.taker_side.name,
                    "price_ticks": trade.price_ticks,
                    "quantity": trade.quantity,
                })

    print(f"Replayed {count} events; outputs: {args.output_dir}")


if __name__ == "__main__":
    main()