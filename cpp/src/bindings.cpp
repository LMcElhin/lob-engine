#include "lob/order_book.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(_core, m) {
    m.doc() = "C++20 limit-order-book core";

    py::enum_<lob::Side>(m, "Side")
        .value("BUY", lob::Side::Buy)
        .value("SELL", lob::Side::Sell)
        .export_values();

    py::class_<lob::Trade>(m, "Trade")
        .def_readonly("maker_id", &lob::Trade::maker_id)
        .def_readonly("taker_id", &lob::Trade::taker_id)
        .def_readonly("taker_side", &lob::Trade::taker_side)
        .def_readonly("price_ticks", &lob::Trade::price_ticks)
        .def_readonly("quantity", &lob::Trade::quantity)
        .def_readonly("timestamp_ns", &lob::Trade::timestamp_ns);

    py::class_<lob::PriceLevel>(m, "PriceLevel")
        .def_readonly("price_ticks", &lob::PriceLevel::price_ticks)
        .def_readonly("quantity", &lob::PriceLevel::quantity)
        .def_readonly("order_count", &lob::PriceLevel::order_count);

    py::class_<lob::Snapshot>(m, "Snapshot")
        .def_readonly("bids", &lob::Snapshot::bids)
        .def_readonly("asks", &lob::Snapshot::asks);

    py::class_<lob::OrderBook>(m, "OrderBook")
        .def(py::init<double>(), py::arg("tick_size") = 0.01)
        .def_property_readonly("tick_size", &lob::OrderBook::tick_size)
        .def("to_ticks", &lob::OrderBook::to_ticks)
        .def("from_ticks", &lob::OrderBook::from_ticks)
        .def("add_limit", &lob::OrderBook::add_limit, py::arg("id"), py::arg("side"),
             py::arg("price"), py::arg("quantity"), py::arg("timestamp_ns") = 0)
        .def("add_market", &lob::OrderBook::add_market, py::arg("id"), py::arg("side"),
             py::arg("quantity"), py::arg("timestamp_ns") = 0)
        .def("cancel", &lob::OrderBook::cancel)
        .def("modify", &lob::OrderBook::modify, py::arg("id"), py::arg("new_price"),
             py::arg("new_quantity"), py::arg("timestamp_ns") = 0)
        .def("contains", &lob::OrderBook::contains)
        .def_property_readonly("order_count", &lob::OrderBook::order_count)
        .def_property_readonly("total_bid_quantity", &lob::OrderBook::total_bid_quantity)
        .def_property_readonly("total_ask_quantity", &lob::OrderBook::total_ask_quantity)
        .def_property_readonly("best_bid", &lob::OrderBook::best_bid)
        .def_property_readonly("best_ask", &lob::OrderBook::best_ask)
        .def_property_readonly("midprice", &lob::OrderBook::midprice)
        .def_property_readonly("spread", &lob::OrderBook::spread)
        .def("imbalance", &lob::OrderBook::imbalance, py::arg("depth") = 1)
        .def("snapshot", &lob::OrderBook::snapshot, py::arg("depth") = 10)
        .def("clear", &lob::OrderBook::clear);
}
