"""Market scanner bounded context for AI Advisor v1.3."""

from ai_advisor.market_scanner.indicators import calculate_stock_indicators, classify_benchmark_regime
from ai_advisor.market_scanner.context_writer import (
    build_stock_advice_context_data,
    deterministic_context_filename,
    write_stock_advice_context_json,
)

from ai_advisor.market_scanner.local_raw_adapter import (
    load_benchmark_daily_records,
    load_listed_stock_daily_records,
    load_local_raw_market_data_snapshot,
    load_otc_stock_daily_records,
)
from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    BenchmarkRegimeSnapshot,
    ContextWriteResult,
    DailyStockRecord,
    LocalRawMarketDataSnapshot,
    RawBenchmarkLoadResult,
    RawStockLoadResult,
    SkippedContextCandidate,
    SkippedRawRow,
    StockIndicatorSnapshot,
)

__all__ = [
    "BenchmarkDailyRecord",
    "BenchmarkRegimeSnapshot",
    "ContextWriteResult",
    "DailyStockRecord",
    "LocalRawMarketDataSnapshot",
    "RawBenchmarkLoadResult",
    "RawStockLoadResult",
    "SkippedContextCandidate",
    "SkippedRawRow",
    "StockIndicatorSnapshot",
    "build_stock_advice_context_data",
    "calculate_stock_indicators",
    "classify_benchmark_regime",
    "deterministic_context_filename",
    "load_benchmark_daily_records",
    "load_listed_stock_daily_records",
    "load_local_raw_market_data_snapshot",
    "load_otc_stock_daily_records",
    "write_stock_advice_context_json",
]
