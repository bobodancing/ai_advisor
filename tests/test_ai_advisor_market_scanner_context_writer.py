from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ai_advisor.market_scanner import (
    build_stock_advice_context_data,
    calculate_stock_indicators,
    classify_benchmark_regime,
    write_stock_advice_context_json,
)
from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    BenchmarkRegimeSnapshot,
    DailyStockRecord,
    ScannerBenchmarkSymbol,
    ScannerMarketType,
)
from ai_advisor.schemas import StockAdviceContext


def test_listed_context_writer_outputs_valid_stock_advice_context() -> None:
    stock_records = stock_series(stock_id="2330", market_type="listed", name="台積電")
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.skipped_candidate is None
    assert result.context_data is not None
    context = StockAdviceContext.model_validate(result.context_data)
    assert context.missing_required_fields() == []
    assert context.market_type == "listed"
    assert context.benchmark_symbol == "TAIEX"
    assert context.stock.stock_id == "2330"
    assert context.stock.name == "台積電"
    assert context.market_regime.risk_state == "risk_on"
    assert context.risk.invalid_level is not None
    assert context.risk.nearest_support is not None
    assert context.risk.planned_target is not None
    assert context.risk.risk_reward_ratio is not None
    assert context.risk.planned_target > context.stock.close


def test_otc_context_writer_outputs_valid_stock_advice_context() -> None:
    stock_records = stock_series(stock_id="6488", market_type="otc", name="GlobalWafers")
    indicators = calculate_stock_indicators(stock_records, benchmark_series("OTC"))
    regime = classify_benchmark_regime(benchmark_series("OTC"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is not None
    context = StockAdviceContext.model_validate(result.context_data)
    assert context.missing_required_fields() == []
    assert context.market_type == "otc"
    assert context.benchmark_symbol == "OTC"
    assert context.stock.stock_id == "6488"


def test_market_scan_fallback_is_neutral_and_keeps_strength_out_of_theme_fields() -> None:
    stock_records = stock_series()
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is not None
    theme = result.context_data["theme"]
    assert theme == {"name": "market_scan", "rank": 999, "score": 50.0, "lifecycle": "unknown"}
    assert "relative_strength_20d_vs_benchmark" not in theme
    assert "scanner_score" not in theme
    assert result.context_data["leader_status"]["leader_rank"] == "unknown"
    assert result.context_data["scanner_metadata"]["relative_strength_20d_vs_benchmark"] is not None
    assert "sector/theme data unavailable; market_scan fallback used" in result.context_data["data_quality_warnings"]
    assert any("not real sector strength" in note for note in result.context_data["data_source_notes"])


def test_unknown_benchmark_regime_is_skipped_before_context_schema_write() -> None:
    stock_records = stock_series()
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = BenchmarkRegimeSnapshot(benchmark_symbol="TAIEX", as_of_date="2024-03-01", risk_state="unknown")

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is None
    assert result.skipped_candidate is not None
    assert result.skipped_candidate.reason == "benchmark regime unavailable for context schema"
    assert "scanner-only risk_state=unknown must not be written to StockAdviceContext" in result.skipped_candidate.details


@pytest.mark.parametrize("as_of_date", ["2024-02-29", "2024-03-02", None])
def test_indicator_as_of_date_mismatch_is_skipped(as_of_date: str | None) -> None:
    stock_records = stock_series()
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX")).model_copy(
        update={"as_of_date": as_of_date}
    )
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is None
    assert result.skipped_candidate is not None
    assert result.skipped_candidate.reason == "indicator as_of_date mismatch"
    assert "latest stock date=2024-03-01" in result.skipped_candidate.details
    assert f"indicator as_of_date={as_of_date}" in result.skipped_candidate.details


@pytest.mark.parametrize("as_of_date", ["2024-02-29", "2024-03-02", None])
def test_regime_as_of_date_mismatch_is_skipped(as_of_date: str | None) -> None:
    stock_records = stock_series()
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX")).model_copy(update={"as_of_date": as_of_date})

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is None
    assert result.skipped_candidate is not None
    assert result.skipped_candidate.reason == "benchmark regime as_of_date mismatch"
    assert "latest stock date=2024-03-01" in result.skipped_candidate.details
    assert f"benchmark regime as_of_date={as_of_date}" in result.skipped_candidate.details


def test_matching_as_of_dates_remain_valid_for_context_write() -> None:
    stock_records = stock_series()
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert indicators.as_of_date == stock_records[-1].date
    assert regime.as_of_date == stock_records[-1].date
    assert result.skipped_candidate is None
    assert result.context_data is not None
    assert result.context_data["date"] == stock_records[-1].date


def test_context_writer_skips_when_structural_target_is_unavailable() -> None:
    stock_records = stock_series()
    stock_records[-1] = stock_records[-1].model_copy(update={"open": 299, "high": 301, "low": 298, "close": 300})
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))

    result = build_stock_advice_context_data(stock_records, indicators, regime)

    assert result.context_data is None
    assert result.skipped_candidate is not None
    assert result.skipped_candidate.reason == "structural risk geometry unavailable"
    assert "M3 does not synthesize close + 2R targets" in result.skipped_candidate.details


def test_context_json_write_is_utf8_deterministic_and_does_not_touch_advice_logs(tmp_path: Path) -> None:
    stock_records = stock_series(stock_id="2330", market_type="listed", name="台積電")
    indicators = calculate_stock_indicators(stock_records, benchmark_series("TAIEX"))
    regime = classify_benchmark_regime(benchmark_series("TAIEX"))
    reports_dir = tmp_path / "reports" / "ai_advice"
    reports_dir.mkdir(parents=True)
    advice_log = reports_dir / "ai_advice_log.jsonl"
    evaluation_log = reports_dir / "ai_advice_evaluation.jsonl"
    advice_log.write_text("advice sentinel\n", encoding="utf-8")
    evaluation_log.write_text("evaluation sentinel\n", encoding="utf-8")

    first = write_stock_advice_context_json(stock_records, indicators, regime, tmp_path / "contexts")
    first_bytes = Path(first.context_path).read_bytes()
    second = write_stock_advice_context_json(stock_records, indicators, regime, tmp_path / "contexts")
    second_bytes = Path(second.context_path).read_bytes()

    assert first.was_written is True
    assert first.context_path == second.context_path
    assert Path(first.context_path).name == "2024-03-01_listed_2330.json"
    assert first_bytes == second_bytes
    assert "台積電".encode("utf-8") in first_bytes
    StockAdviceContext.model_validate(json.loads(first_bytes.decode("utf-8")))
    assert advice_log.read_text(encoding="utf-8") == "advice sentinel\n"
    assert evaluation_log.read_text(encoding="utf-8") == "evaluation sentinel\n"


def stock_series(
    *,
    stock_id: str = "2330",
    market_type: ScannerMarketType = "listed",
    name: str = "Stock 2330",
) -> list[DailyStockRecord]:
    start = date(2024, 1, 1)
    records: list[DailyStockRecord] = []
    for i in range(61):
        close = 120 + i * 0.5
        records.append(
            DailyStockRecord(
                source="context-writer-fixture",
                market_type=market_type,
                date=(start + timedelta(days=i)).isoformat(),
                stock_id=stock_id,
                name=name,
                open=close - 0.5,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=1_000_000 + i * 1_000,
                turnover_value=50_000_000 + i,
                is_limit_up=False,
            )
        )
    return records


def benchmark_series(symbol: ScannerBenchmarkSymbol) -> list[BenchmarkDailyRecord]:
    start = date(2024, 1, 1)
    records: list[BenchmarkDailyRecord] = []
    for i in range(61):
        close = 100 + i * 0.5
        records.append(
            BenchmarkDailyRecord(
                source="context-writer-fixture",
                benchmark_symbol=symbol,
                date=(start + timedelta(days=i)).isoformat(),
                close=close,
            )
        )
    return records
