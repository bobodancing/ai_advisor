from __future__ import annotations

from collections.abc import Sequence

from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    BenchmarkRegimeSnapshot,
    DailyStockRecord,
    ScannerBenchmarkSymbol,
    StockIndicatorSnapshot,
)


def calculate_stock_indicators(
    stock_records: Sequence[DailyStockRecord],
    benchmark_records: Sequence[BenchmarkDailyRecord] | None = None,
) -> StockIndicatorSnapshot:
    records = _sort_records(stock_records)
    warnings: list[str] = []
    if not records:
        return StockIndicatorSnapshot(stock_id=None, market_type=None, as_of_date=None, warnings=["no stock records"])

    latest = records[-1]
    ma5 = moving_average([record.close for record in records], 5, warnings, "MA5")
    ma10 = moving_average([record.close for record in records], 10, warnings, "MA10")
    ma20 = moving_average([record.close for record in records], 20, warnings, "MA20")
    ma60 = moving_average([record.close for record in records], 60, warnings, "MA60")
    average_volume_20d = moving_average([float(record.volume) for record in records], 20, warnings, "20-day average volume")

    volume_ratio_20d: float | None = None
    if average_volume_20d is not None:
        if average_volume_20d > 0:
            volume_ratio_20d = latest.volume / average_volume_20d
        else:
            warnings.append("20-day average volume is zero; volume_ratio_20d unavailable")

    distance_from_ma20: float | None = None
    if ma20 is not None:
        if ma20 > 0:
            distance_from_ma20 = (latest.close - ma20) / ma20 * 100
        else:
            warnings.append("MA20 is zero; distance_from_ma20 unavailable")

    return StockIndicatorSnapshot(
        stock_id=latest.stock_id,
        market_type=latest.market_type,
        as_of_date=latest.date,
        ma5=ma5,
        ma10=ma10,
        ma20=ma20,
        ma60=ma60,
        average_volume_20d=average_volume_20d,
        volume_ratio_20d=volume_ratio_20d,
        prior_20d_high=prior_high(records, 20, warnings),
        prior_20d_low=prior_low(records, 20, warnings),
        prior_60d_high=prior_high(records, 60, warnings),
        prior_60d_low=prior_low(records, 60, warnings),
        distance_from_ma20=distance_from_ma20,
        relative_strength_20d_vs_benchmark=relative_strength_vs_benchmark(records, benchmark_records, 20, warnings),
        relative_strength_60d_vs_benchmark=relative_strength_vs_benchmark(records, benchmark_records, 60, warnings),
        warnings=warnings,
    )


def classify_benchmark_regime(records: Sequence[BenchmarkDailyRecord]) -> BenchmarkRegimeSnapshot:
    sorted_records = _sort_records(records)
    warnings: list[str] = []
    if not sorted_records:
        return BenchmarkRegimeSnapshot(
            benchmark_symbol=None,
            as_of_date=None,
            risk_state="unknown",
            warnings=["no benchmark records"],
        )

    latest = sorted_records[-1]
    closes = [record.close for record in sorted_records]
    ma20 = moving_average(closes, 20, warnings, "benchmark MA20")
    ma60 = moving_average(closes, 60, warnings, "benchmark MA60")
    risk_state = "unknown"

    if ma20 is not None and ma60 is not None:
        if latest.close > ma20 and ma20 >= ma60:
            risk_state = "risk_on"
        elif latest.close < ma20 * 0.98 or ma20 < ma60:
            risk_state = "risk_off"
        elif latest.close >= ma20 * 0.98:
            risk_state = "neutral"
        else:
            risk_state = "risk_off"
    else:
        warnings.append("insufficient benchmark data for risk_state")

    return BenchmarkRegimeSnapshot(
        benchmark_symbol=latest.benchmark_symbol,
        as_of_date=latest.date,
        ma20=ma20,
        ma60=ma60,
        risk_state=risk_state,
        warnings=warnings,
    )


def moving_average(values: Sequence[float], window: int, warnings: list[str] | None = None, label: str | None = None) -> float | None:
    if len(values) < window:
        if warnings is not None:
            warnings.append(f"insufficient data for {label or f'MA{window}'}: need {window}, got {len(values)}")
        return None
    window_values = values[-window:]
    return sum(window_values) / window


def prior_high(records: Sequence[DailyStockRecord], window: int, warnings: list[str] | None = None) -> float | None:
    prior_records = _prior_window(records, window, warnings, f"prior_{window}d_high")
    if prior_records is None:
        return None
    return max(record.high for record in prior_records)


def prior_low(records: Sequence[DailyStockRecord], window: int, warnings: list[str] | None = None) -> float | None:
    prior_records = _prior_window(records, window, warnings, f"prior_{window}d_low")
    if prior_records is None:
        return None
    return min(record.low for record in prior_records)


def relative_strength_vs_benchmark(
    stock_records: Sequence[DailyStockRecord],
    benchmark_records: Sequence[BenchmarkDailyRecord] | None,
    window: int,
    warnings: list[str] | None = None,
) -> float | None:
    records = _sort_records(stock_records)
    required = window + 1
    if len(records) < required:
        _warn(warnings, f"insufficient stock data for relative_strength_{window}d_vs_benchmark: need {required}, got {len(records)}")
        return None
    if not benchmark_records:
        _warn(warnings, f"missing benchmark records for relative_strength_{window}d_vs_benchmark")
        return None

    stock_window = records[-required:]
    start_stock = stock_window[0]
    end_stock = stock_window[-1]
    benchmark_by_date = {record.date: record for record in _sort_records(benchmark_records)}
    start_benchmark = benchmark_by_date.get(start_stock.date)
    end_benchmark = benchmark_by_date.get(end_stock.date)
    if start_benchmark is None or end_benchmark is None:
        _warn(
            warnings,
            f"benchmark records missing matching start/end dates for relative_strength_{window}d_vs_benchmark",
        )
        return None

    stock_return = _return_pct(start_stock.close, end_stock.close, warnings, f"stock {window}d return")
    benchmark_return = _return_pct(
        start_benchmark.close,
        end_benchmark.close,
        warnings,
        f"benchmark {window}d return",
    )
    if stock_return is None or benchmark_return is None:
        return None
    return stock_return - benchmark_return


def _prior_window(
    records: Sequence[DailyStockRecord],
    window: int,
    warnings: list[str] | None,
    label: str,
) -> list[DailyStockRecord] | None:
    sorted_records = _sort_records(records)
    required = window + 1
    if len(sorted_records) < required:
        _warn(warnings, f"insufficient data for {label}: need {required}, got {len(sorted_records)}")
        return None
    return sorted_records[-required:-1]


def _return_pct(start: float, end: float, warnings: list[str] | None, label: str) -> float | None:
    if start <= 0:
        _warn(warnings, f"{label} start close <= 0; return unavailable")
        return None
    return (end - start) / start * 100


def _sort_records(records: Sequence[DailyStockRecord] | Sequence[BenchmarkDailyRecord]):
    return sorted(records, key=lambda record: record.date)


def _warn(warnings: list[str] | None, message: str) -> None:
    if warnings is not None:
        warnings.append(message)
