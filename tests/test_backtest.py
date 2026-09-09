import pytest
from loblab.backtest import Action, ImbalanceStrategy, PaperExecutor


def test_paper_executor_round_trip() -> None:
    executor = PaperExecutor(starting_cash=1_000, fee_bps=0)
    assert executor.execute(Action.BUY, 99.99, 100.01, 1) is not None
    assert executor.execute(Action.SELL, 100.09, 100.11, 1) is not None
    assert executor.portfolio.cash == pytest.approx(1_000.08)


def test_strategy() -> None:
    strategy = ImbalanceStrategy(0.5, -0.5)
    assert strategy.decide(0.6, 0) is Action.BUY
    assert strategy.decide(-0.6, 1) is Action.SELL
    assert strategy.decide(0.0, 0) is Action.HOLD
