from __future__ import annotations

from datetime import date, timedelta

import pytest

from ai_advisor.market_scanner import calculate_stock_indicators, classify_benchmark_regime
from ai_advisor.market_scanner.schemas import BenchmarkDailyRecord, DailyStockRecord, ScannerBenchmarkSymbol, ScannerMarketType


def test_stock_indicators_calculate_moving_averages_volume_and_price_ranges() -> None:
    stock_records = stock_series()
    benchmark_records = benchmark_series(symbol="TAIEX")

    indicators = calculate_stock_indicators(stock_records, benchmark_records)

    assert indicators.stock_id == "2330"
    assert indicators.market_type == "listed"
    assert indicators.as_of_date == "2024-03-01"
    assert indicators.ma5 == pytest.approx(159)
    assert indicators.ma10 == pytest.approx(156.5)
    assert indicators.ma20 == pytest.approx(151.5)
    assert indicators.ma60 == pytest.approx(131.5)
    assert indicators.average_volume_20d == pytest.approx(1515)
    assert indicators.volume_ratio_20d == pytest.approx(1610 / 1515)
    assert indicators.prior_20d_high == pytest.approx(162)
    assert indicators.prior_20d_low == pytest.approx(139)
    assert indicators.prior_60d_high == pytest.approx(162)
    assert indicators.prior_60d_low == pytest.approx(99)
    assert indicators.distance_from_ma20 == pytest.approx((161 - 151.5) / 151.5 * 100)
    assert indicators.warnings == []


def test_relative_strength_uses_matching_benchmark_window_dates() -> None:
    stock_records = stock_series()
    benchmark_records = benchmark_series(symbol="TAIEX")

    indicators = calculate_stock_indicators(stock_records, benchmark_records)

    stock_20d_return = (161 - 141) / 141 * 100
    benchmark_20d_return = (130.5 - 120.5) / 120.5 * 100
    stock_60d_return = (161 - 101) / 101 * 100
    benchmark_60d_return = (130.5 - 100.5) / 100.5 * 100
    assert indicators.relative_strength_20d_vs_benchmark == pytest.approx(stock_20d_return - benchmark_20d_return)
    assert indicators.relative_strength_60d_vs_benchmark == pytest.approx(stock_60d_return - benchmark_60d_return)


def test_insufficient_stock_data_returns_none_and_warnings_without_guessing() -> None:
    indicators = calculate_stock_indicators(stock_series(length=10), benchmark_series(symbol="TAIEX", length=10))

    assert indicators.ma5 == pytest.approx(108)
    assert indicators.ma10 == pytest.approx(105.5)
    assert indicators.ma20 is None
    assert indicators.ma60 is None
    assert indicators.average_volume_20d is None
    assert indicators.volume_ratio_20d is None
    assert indicators.prior_20d_high is None
    assert indicators.prior_60d_high is None
    assert indicators.relative_strength_20d_vs_benchmark is None
    assert indicators.relative_strength_60d_vs_benchmark is None
    assert "insufficient data for MA20: need 20, got 10" in indicators.warnings
    assert "insufficient data for prior_20d_high: need 21, got 10" in indicators.warnings
    assert any("relative_strength_60d_vs_benchmark" in warning for warning in indicators.warnings)


def test_relative_strength_20d_requires_21_stock_sessions() -> None:
    insufficient = calculate_stock_indicators(stock_series(length=20), benchmark_series(symbol="TAIEX", length=20))
    sufficient = calculate_stock_indicators(stock_series(length=21), benchmark_series(symbol="TAIEX", length=21))

    expected_stock_return = (121 - 101) / 101 * 100
    expected_benchmark_return = (110.5 - 100.5) / 100.5 * 100
    assert insufficient.relative_strength_20d_vs_benchmark is None
    assert "insufficient stock data for relative_strength_20d_vs_benchmark: need 21, got 20" in insufficient.warnings
    assert sufficient.relative_strength_20d_vs_benchmark == pytest.approx(
        expected_stock_return - expected_benchmark_return
    )


def test_benchmark_regime_classifies_listed_risk_on() -> None:
    regime = classify_benchmark_regime(benchmark_series(symbol="TAIEX"))

    assert regime.benchmark_symbol == "TAIEX"
    assert regime.as_of_date == "2024-03-01"
    assert regime.ma20 == pytest.approx(125.75)
    assert regime.ma60 == pytest.approx(115.75)
    assert regime.risk_state == "risk_on"
    assert regime.warnings == []


def test_benchmark_regime_classifies_otc_risk_off() -> None:
    regime = classify_benchmark_regime(benchmark_series(symbol="OTC", start_close=200, step=-1))

    assert regime.benchmark_symbol == "OTC"
    assert regime.ma20 == pytest.approx(148.5)
    assert regime.ma60 == pytest.approx(168.5)
    assert regime.risk_state == "risk_off"
    assert regime.warnings == []


def test_benchmark_regime_classifies_neutral_and_unknown_deterministically() -> None:
    neutral = classify_benchmark_regime(benchmark_series(symbol="TAIEX", start_close=100, step=0, length=60))
    unknown = classify_benchmark_regime(benchmark_series(symbol="OTC", length=19))

    assert neutral.risk_state == "neutral"
    assert neutral.ma20 == pytest.approx(100)
    assert neutral.ma60 == pytest.approx(100)
    assert unknown.risk_state == "unknown"
    assert unknown.ma20 is None
    assert unknown.ma60 is None
    assert "insufficient benchmark data for risk_state" in unknown.warnings


def stock_series(
    *,
    stock_id: str = "2330",
    market_type: ScannerMarketType = "listed",
    length: int = 61,
) -> list[DailyStockRecord]:
    start = date(2024, 1, 1)
    records: list[DailyStockRecord] = []
    for i in range(1, length + 1):
        close = 100 + i
        records.append(
            DailyStockRecord(
                source="indicator-fixture",
                market_type=market_type,
                date=(start + timedelta(days=i - 1)).isoformat(),
                stock_id=stock_id,
                name=f"Stock {stock_id}",
                open=close - 1,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=1000 + i * 10,
                turnover_value=20_000_000 + i,
            )
        )
    return records


def benchmark_series(
    *,
    symbol: ScannerBenchmarkSymbol,
    length: int = 61,
    start_close: float = 100,
    step: float = 0.5,
) -> list[BenchmarkDailyRecord]:
    start = date(2024, 1, 1)
    records: list[BenchmarkDailyRecord] = []
    for i in range(1, length + 1):
        close = start_close + i * step
        records.append(
            BenchmarkDailyRecord(
                source="indicator-fixture",
                benchmark_symbol=symbol,
                date=(start + timedelta(days=i - 1)).isoformat(),
                close=close,
            )
        )
    return records
