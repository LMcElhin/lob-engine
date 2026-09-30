from pathlib import Path

import pytest

from loblab.replay import Event, Replayer, read_events


def test_fifo_partial_fill_and_modify() -> None:
    replay = Replayer()
    replay.apply(Event(1, "LIMIT", 1, "BUY", 100, 10))
    replay.apply(Event(1, "LIMIT", 2, "BUY", 100, 20))
    replay.apply(Event(2, "MODIFY", 1, price=100, quantity=5))

    result = replay.apply(Event(3, "MARKET", 3, "SELL", quantity=6))

    assert [(t.maker_id, t.quantity) for t in result.trades] == [(1, 5), (2, 1)]
    assert result.features.bid_depth == 19
    assert result.features.best_ask is None


def test_timestamp_failure_does_not_mutate_book() -> None:
    replay = Replayer()
    replay.apply(Event(10, "LIMIT", 1, "BUY", 100, 10))

    with pytest.raises(ValueError, match="nondecreasing"):
        replay.apply(Event(9, "CANCEL", 1))

    assert replay.book.contains(1)

    replay.apply(Event(10, "CANCEL", 1))
    assert replay.book.order_count == 0


@pytest.mark.parametrize("kind", ["CANCEL", "MODIFY"])
def test_unknown_order_rejected(kind: str) -> None:
    event = Event(
        0,
        kind,
        99,
        price=100 if kind == "MODIFY" else None,
        quantity=1 if kind == "MODIFY" else None,
    )

    with pytest.raises(ValueError, match="unknown resting"):
        Replayer().apply(event)


@pytest.mark.parametrize("kwargs", [
    {"quantity": 0},
    {"quantity": 2**64},
    {"price": float("nan")},
    {"side": "BID"},
    {"timestamp_ns": -1},
])
def test_invalid_event(kwargs: dict) -> None:
    fields = dict(
        timestamp_ns=0,
        event_type="LIMIT",
        order_id=1,
        side="BUY",
        price=100,
        quantity=1,
    )
    fields.update(kwargs)

    with pytest.raises(ValueError):
        Event(**fields)


def test_csv_errors_have_line_number(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    source.write_text(
        "timestamp_ns,event_type,order_id,side,price,quantity\n"
        "0,LIMIT,1,BUY,100,nope\n"
    )

    with pytest.raises(ValueError, match="CSV line 2"):
        list(read_events(source))


def test_replay_is_deterministic() -> None:
    source = Path(__file__).parents[1] / "examples/data/orders.csv"
    outputs = []

    for _ in range(2):
        replay = Replayer()
        records = []

        for event in read_events(source):
            result = replay.apply(event)
            records.append((
                result.features,
                [(t.maker_id, t.price_ticks, t.quantity) for t in result.trades],
            ))

        outputs.append(records)

    assert outputs[0] == outputs[1]
    assert outputs[0][-1][0].best_ask is None


def test_cli_exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import csv
    import sys

    from loblab.replay import main

    source = Path(__file__).parents[1] / "examples/data/orders.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        ["lob-replay", str(source), "--output-dir", str(tmp_path)],
    )

    main()

    with (tmp_path / "features.csv").open() as stream:
        features = list(csv.DictReader(stream))

    with (tmp_path / "trades.csv").open() as stream:
        trades = list(csv.DictReader(stream))

    assert len(features) == 8
    assert [(t["maker_id"], t["quantity"], t["side"]) for t in trades] == [
        ("1", "10", "SELL"),
        ("2", "2", "SELL"),
        ("5", "8", "BUY"),
    ]
    assert features[-1]["best_ask"] == ""


def test_marketable_modify_trade_side() -> None:
    replay = Replayer()
    replay.apply(Event(1, "LIMIT", 1, "BUY", 100, 10))
    replay.apply(Event(2, "LIMIT", 2, "SELL", 101, 10))

    result = replay.apply(Event(3, "MODIFY", 1, price=101, quantity=4))

    assert result.trades[0].taker_side.name == "BUY"
    assert result.trades[0].quantity == 4
    assert result.features.ask_depth == 6