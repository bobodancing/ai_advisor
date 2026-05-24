"""Local raw market-data adapter for AI Advisor v1.3 scanner M1."""

from ai_advisor.market_scanner.local_raw_adapter import (
    load_benchmark_daily_records,
    load_listed_stock_daily_records,
    load_local_raw_market_data_snapshot,
    load_otc_stock_daily_records,
)
from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    DailyStockRecord,
    LocalRawMarketDataSnapshot,
    RawBenchmarkLoadResult,
    RawStockLoadResult,
    SkippedRawRow,
)

__all__ = [
    "BenchmarkDailyRecord",
    "DailyStockRecord",
    "LocalRawMarketDataSnapshot",
    "RawBenchmarkLoadResult",
    "RawStockLoadResult",
    "SkippedRawRow",
    "load_benchmark_daily_records",
    "load_listed_stock_daily_records",
    "load_local_raw_market_data_snapshot",
    "load_otc_stock_daily_records",
]
