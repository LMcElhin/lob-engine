from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class Portfolio:
    cash: float
    position: int = 0
    fees_paid: float = 0.0
    trades: int = 0

    def equity(self, mark_price: float) -> float:
        return self.cash + self.position * mark_price


@dataclass(frozen=True, slots=True)
class Fill:
    action: Action
    price: float
    quantity: int
    fee: float


class PaperExecutor:
    """Simple conservative crossing model: buys at ask, sells at bid."""

    def __init__(self, starting_cash: float = 100.0, fee_bps: float = 5.0) -> None:
        if starting_cash <= 0:
            raise ValueError("starting_cash must be > 0")
        if fee_bps < 0:
            raise ValueError("fee_bps must be >= 0")
        self.portfolio = Portfolio(cash=starting_cash)
        self.fee_bps = fee_bps

    def execute(
        self,
        action: Action,
        best_bid: float | None,
        best_ask: float | None,
        quantity: int = 1,
    ) -> Fill | None:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if action is Action.HOLD:
            return None

        if action is Action.BUY:
            if best_ask is None:
                return None
            price = best_ask
            notional = price * quantity
            fee = notional * self.fee_bps / 10_000
            if self.portfolio.cash < notional + fee:
                return None
            self.portfolio.cash -= notional + fee
            self.portfolio.position += quantity
        else:
            if best_bid is None or self.portfolio.position < quantity:
                return None
            price = best_bid
            notional = price * quantity
            fee = notional * self.fee_bps / 10_000
            self.portfolio.cash += notional - fee
            self.portfolio.position -= quantity

        self.portfolio.fees_paid += fee
        self.portfolio.trades += 1
        return Fill(action, price, quantity, fee)


class ImbalanceStrategy:
    """Infrastructure-demo signal, not a profitability claim."""

    def __init__(self, buy_threshold: float = 0.60, sell_threshold: float = -0.60) -> None:
        if not -1 <= sell_threshold < buy_threshold <= 1:
            raise ValueError("thresholds must satisfy -1 <= sell < buy <= 1")
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def decide(self, imbalance: float, position: int) -> Action:
        if imbalance >= self.buy_threshold and position == 0:
            return Action.BUY
        if imbalance <= self.sell_threshold and position > 0:
            return Action.SELL
        return Action.HOLD
