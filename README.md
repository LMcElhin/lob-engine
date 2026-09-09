# LOB Engine

A C++20 limit-order-book and matching engine with Python bindings, a readable
pure-Python reference implementation, market-microstructure features and a
small paper-execution framework.

> Research/engineering software, not investment advice. The included imbalance
> strategy is an infrastructure demo and makes no claim of profitability.

## Highlights

- C++20 price-time-priority matching engine
- integer price ticks instead of floating-point book keys
- O(1)-style resting-order lookup/cancel using ID locators + stable list iterators
- market and marketable limit orders
- cancel/modify semantics
- pybind11 bindings
- pure-Python reference implementation
- spread, midprice, depth imbalance and microprice
- simple fee-aware paper executor
- pytest suite + native C++ test
- Windows/Linux GitHub Actions
- native benchmark executable

## Architecture

```text
market events
     |
     v
+---------------------+
| C++20 OrderBook     |
| price-time priority |
+----------+----------+
           |
        pybind11
           |
           v
+---------------------+
| Python research     |
| features / signals  |
+----------+----------+
           |
           v
+---------------------+
| paper executor      |
| risk / P&L layer    |
+---------------------+
```

## Layout

```text
lob-engine/
├── cpp/
│   ├── include/lob/order_book.hpp
│   ├── src/order_book.cpp
│   ├── src/bindings.cpp
│   ├── tests/test_order_book.cpp
│   └── benchmarks/benchmark.cpp
├── src/loblab/
│   ├── reference.py
│   ├── features.py
│   ├── backtest.py
│   └── cli.py
├── examples/
├── tests/
├── .github/workflows/ci.yml
├── CMakeLists.txt
└── pyproject.toml
```

## Matching rules

A buy limit order consumes asks while `best_ask <= limit_price`. A sell consumes
bids while `best_bid >= limit_price`. Within one price level, execution is FIFO.
Unfilled market-order quantity is discarded rather than rested.

Modification policy:

- reducing size at the same price preserves queue priority;
- increasing size or changing price is treated as cancel/replace and loses priority.

## Windows / PowerShell setup

Install Python 3.10+ and Visual Studio Build Tools 2022 with **Desktop development
with C++**.

```powershell
cd lob-engine
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
lob-demo
python examples\backtest_demo.py
```

The Python build uses scikit-build-core + CMake + pybind11, so `pip install -e .`
compiles the C++ extension automatically.

## Python usage

```python
from loblab import OrderBook, Side, features_from_book

book = OrderBook(0.01)
book.add_limit(1, Side.BUY, 99.99, 100)
book.add_limit(2, Side.SELL, 100.01, 75)

print(book.best_bid, book.best_ask, book.midprice, book.spread)
print(features_from_book(book, depth=5))

trades = book.add_market(10, Side.BUY, 25)
for trade in trades:
    print(trade.maker_id, book.from_ticks(trade.price_ticks), trade.quantity)
```

## Why use integer ticks?

Prices are converted once using `round(price / tick_size)` and internal map keys
are integers. That avoids relying on binary floating-point equality/order for
book price levels.

## Features

For bid depth `Vb` and ask depth `Va`:

```text
imbalance = (Vb - Va) / (Vb + Va)
```

Top-of-book microprice is:

```text
microprice = (ask * bid_volume + bid * ask_volume) / (bid_volume + ask_volume)
```

## Native benchmark

```powershell
cmake -S . -B build-native -DLOB_BUILD_PYTHON=OFF -DLOB_BUILD_BENCHMARK=ON -DLOB_BUILD_TESTS=ON
cmake --build build-native --config Release
ctest --test-dir build-native -C Release
.\build-native\Release\lob_benchmark.exe 1000000
```

Do not publish a throughput number until you measure it on your own hardware and
record CPU/compiler/build configuration.

## Recommended development roadmap

### v0.2 — Level-2 event replay

Normalize historical data to something like:

```text
timestamp_ns,event_type,order_id,side,price,quantity
```

Replay it deterministically and measure events/s plus p50/p95/p99 processing
latency.

### v0.3 — Microstructure research

Study whether the following have out-of-sample short-horizon predictive value:

- order-book imbalance
- microprice displacement
- order-flow imbalance
- spread
- short-term realized volatility

Use chronological splits and explicitly guard against leakage.

### v0.4 — Realistic execution backtester

Add maker/taker commissions, spread, slippage, latency, partial fills,
queue-position assumptions, inventory limits, maximum loss and a kill switch.

### v0.5 — Broker paper adapter

Separate these interfaces:

```text
MarketDataAdapter
Strategy
RiskManager
ExecutionAdapter
```

Connect a paper account first. Keep live credentials and broker-specific code out
of the core matching library.

### v1.0 — Simulation-to-live validation report

Compare historical simulation, paper fills and deliberately tiny live validation.
The strongest research story is often explaining *why* simulation and real fills
disagree, rather than showing a headline return.

## High-value extensions

- randomized differential tests between Python and C++ engines
- property-based testing
- deterministic binary event logs
- ASan/UBSan CI
- profiling/flamegraphs
- order-flow-imbalance features
- queue-position model
- latency histograms
- WebSocket market-data adapter
- broker paper-trading adapter
- experiment report with confidence intervals and transaction-cost sensitivity

## License

MIT.
