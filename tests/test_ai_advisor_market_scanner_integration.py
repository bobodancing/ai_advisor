from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from ai_advisor.batch_engine import generate_stock_batch_advice, rank_stock_advices
from ai_advisor.market_scanner import scan_market_candidates
from ai_advisor.market_scanner.schemas import BenchmarkDailyRecord, DailyStockRecord, ScannerConfig
from ai_advisor.schemas import StockAdviceContext


APP_PATH = Path(__file__).parents[1] / "apps" / "ai_advisor_streamlit.py"

spec = importlib.util.spec_from_file_location("ai_advisor_streamlit_app_m5", APP_PATH)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def test_scanner_generated_context_folder_loads_through_existing_fake_batch_flow(tmp_path: Path) -> None:
    output_dir = tmp_path / "scanner_contexts"
    reports_dir = tmp_path / "reports" / "ai_advice"
    reports_dir.mkdir(parents=True)
    advice_log = reports_dir / "ai_advice_log.jsonl"
    evaluation_log = reports_dir / "ai_advice_evaluation.jsonl"
    advice_log.write_text("advice sentinel\n", encoding="utf-8")
    evaluation_log.write_text("evaluation sentinel\n", encoding="utf-8")

    stock_universe = [
        scanner_stock_series(str(3100 + index), "listed", target_above_close=10 + index * 0.1)
        for index in range(12)
    ] + [
        scanner_stock_series(str(3200 + index), "otc", target_above_close=11 + index * 0.1)
        for index in range(8)
    ]

    scanner_result = scan_market_candidates(
        stock_universe,
        {
            "TAIEX": scanner_benchmark_series("TAIEX", start_close=100, step=0.2),
            "OTC": scanner_benchmark_series("OTC", start_close=80, step=0.15),
        },
        ScannerConfig(min_output_warning_threshold=20, max_output=50),
        output_dir=output_dir,
    )

    assert scanner_result.summary.output_context_count == 20
    assert not any("fewer than 20 contexts generated" in warning for warning in scanner_result.summary.warnings)

    context_paths = sorted(output_dir.glob("*.json"))
    assert len(context_paths) == scanner_result.summary.output_context_count
    for context_path in context_paths:
        context_data = json.loads(context_path.read_text(encoding="utf-8"))
        StockAdviceContext.model_validate(context_data)

    loaded_paths, load_messages = app.load_folder_context_paths(str(output_dir), max_batch_size=50)
    assert load_messages == []
    assert loaded_paths == sorted(str(path) for path in context_paths)

    ranked_from_streamlit_flow = app.run_batch(app.MODE_FAKE, loaded_paths, append_log=False)
    table_rows = app.ranked_table_rows(ranked_from_streamlit_flow)
    assert len(ranked_from_streamlit_flow) == len(loaded_paths)
    assert tuple(table_rows[0].keys()) == app.TABLE_COLUMNS
    assert [row["rank"] for row in table_rows] == list(range(1, len(table_rows) + 1))

    outputs = generate_stock_batch_advice(loaded_paths, log_path=str(advice_log), append_log=False)
    ranked_from_batch_flow = rank_stock_advices(outputs)
    assert len(ranked_from_batch_flow) == len(loaded_paths)
    assert all(output.raw_advice is not None for output in outputs)
    assert all(output.guardrail_result.error_message is None for output in outputs)
    assert advice_log.read_text(encoding="utf-8") == "advice sentinel\n"
    assert evaluation_log.read_text(encoding="utf-8") == "evaluation sentinel\n"


def scanner_stock_series(
    stock_id: str,
    market_type: str,
    *,
    target_above_close: float,
    length: int = 61,
) -> list[DailyStockRecord]:
    start = date(2024, 1, 1)
    latest_close = 100 + (length - 1) * 0.2
    records: list[DailyStockRecord] = []
    for index in range(length):
        close = 100 + index * 0.2
        high = close + 0.5
        if index == length - 2:
            high = latest_close + target_above_close
        records.append(
            DailyStockRecord(
                source="m5-integration-fixture",
                market_type=market_type,
                date=(start + timedelta(days=index)).isoformat(),
                stock_id=stock_id,
                name=f"Stock {stock_id}",
                open=close - 0.2,
                high=high,
                low=close - 0.5,
                close=close,
                volume=2_000_000 if index == length - 1 else 1_000_000,
                turnover_value=50_000_000,
                is_limit_up=False,
            )
        )
    return records


def scanner_benchmark_series(
    symbol: str,
    *,
    start_close: float,
    step: float,
    length: int = 61,
) -> list[BenchmarkDailyRecord]:
    start = date(2024, 1, 1)
    return [
        BenchmarkDailyRecord(
            source="m5-integration-fixture",
            benchmark_symbol=symbol,
            date=(start + timedelta(days=index)).isoformat(),
            close=start_close + index * step,
        )
        for index in range(length)
    ]
