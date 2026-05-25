from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ScannerMarketType = Literal["listed", "otc"]
ScannerBenchmarkSymbol = Literal["TAIEX", "OTC"]
InstrumentClassification = Literal["common_stock_candidate", "non_common_stock", "unknown"]
ScannerRiskState = Literal["risk_on", "neutral", "risk_off", "unknown"]
ScannerTechnicalPosition = Literal[
    "breakout",
    "pullback_to_ma5",
    "pullback_to_ma10_and_rebound",
    "near_ma20_support",
    "extended_above_ma",
    "breakdown",
    "range_bound",
    "unknown",
]


class ScannerBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DailyStockRecord(ScannerBaseModel):
    source: str
    market_type: ScannerMarketType
    date: str
    stock_id: str
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover_value: int
    change: float | None = None
    transactions: int | None = None
    is_limit_up: bool | None = None
    next_limit_up: float | None = None
    next_limit_down: float | None = None
    instrument_classification: InstrumentClassification = "common_stock_candidate"
    classification_notes: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class BenchmarkDailyRecord(ScannerBaseModel):
    source: str
    benchmark_symbol: ScannerBenchmarkSymbol
    date: str
    close: float
    change: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class SkippedRawRow(ScannerBaseModel):
    source: str
    row_number: int
    reason: str
    market_type: ScannerMarketType | None = None
    benchmark_symbol: ScannerBenchmarkSymbol | None = None
    stock_id: str | None = None
    name: str | None = None
    date: str | None = None
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class RawStockLoadResult(ScannerBaseModel):
    source_path: str
    market_type: ScannerMarketType
    records: list[DailyStockRecord]
    skipped_rows: list[SkippedRawRow]


class RawBenchmarkLoadResult(ScannerBaseModel):
    source_path: str
    benchmark_symbol: ScannerBenchmarkSymbol
    records: list[BenchmarkDailyRecord]
    skipped_rows: list[SkippedRawRow]


class LocalRawMarketDataSnapshot(ScannerBaseModel):
    listed_stocks: RawStockLoadResult
    otc_stocks: RawStockLoadResult
    taiex_benchmark: RawBenchmarkLoadResult
    otc_benchmark: RawBenchmarkLoadResult


class StockIndicatorSnapshot(ScannerBaseModel):
    stock_id: str | None
    market_type: ScannerMarketType | None
    as_of_date: str | None
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    average_volume_20d: float | None = None
    volume_ratio_20d: float | None = None
    prior_20d_high: float | None = None
    prior_20d_low: float | None = None
    prior_60d_high: float | None = None
    prior_60d_low: float | None = None
    distance_from_ma20: float | None = None
    relative_strength_20d_vs_benchmark: float | None = None
    relative_strength_60d_vs_benchmark: float | None = None
    warnings: list[str] = Field(default_factory=list)


class BenchmarkRegimeSnapshot(ScannerBaseModel):
    benchmark_symbol: ScannerBenchmarkSymbol | None
    as_of_date: str | None
    ma20: float | None = None
    ma60: float | None = None
    risk_state: ScannerRiskState = "unknown"
    warnings: list[str] = Field(default_factory=list)


class SkippedContextCandidate(ScannerBaseModel):
    stock_id: str | None = None
    date: str | None = None
    reason: str
    details: list[str] = Field(default_factory=list)


class ContextWriteResult(ScannerBaseModel):
    was_written: bool
    context_path: str | None = None
    context_data: dict[str, Any] | None = None
    skipped_candidate: SkippedContextCandidate | None = None
    warnings: list[str] = Field(default_factory=list)


class ScannerConfig(ScannerBaseModel):
    min_turnover_value: int = 20_000_000
    min_output_warning_threshold: int = 20
    max_output: int = 50


class SkippedScannerCandidate(ScannerBaseModel):
    stock_id: str | None = None
    date: str | None = None
    reason: str
    details: list[str] = Field(default_factory=list)


class ScannerPassCandidate(ScannerBaseModel):
    stock_id: str
    stock_name: str
    market_type: ScannerMarketType
    date: str
    risk_reward_ratio: float
    relative_strength_20d_vs_benchmark: float | None = None
    relative_strength_60d_vs_benchmark: float | None = None
    volume_ratio_20d: float
    technical_position: ScannerTechnicalPosition
    distance_from_ma20: float | None = None
    penalties: list[str] = Field(default_factory=list)
    scanner_rank: int | None = None
    scanner_score: float | None = None
    context_data: dict[str, Any]
    context_path: str | None = None


class ScannerRunSummary(ScannerBaseModel):
    input_candidate_count: int
    output_context_count: int
    skipped_count: int
    penalty_candidate_count: int
    warnings: list[str] = Field(default_factory=list)
    skip_reason_counts: dict[str, int] = Field(default_factory=dict)
    penalty_counts: dict[str, int] = Field(default_factory=dict)


class ScannerRunResult(ScannerBaseModel):
    candidates: list[ScannerPassCandidate]
    skipped_candidates: list[SkippedScannerCandidate]
    summary: ScannerRunSummary
