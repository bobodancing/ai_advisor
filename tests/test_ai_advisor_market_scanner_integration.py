from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from ai_advisor.batch_engine import generate_stock_batch_advice, rank_stock_advices
from ai_advisor.market_scanner import scan_local_raw_market_data, scan_market_candidates
from ai_advisor.market_scanner.scanner import main as scanner_cli_main
from ai_advisor.market_scanner.schemas import BenchmarkDailyRecord, DailyStockRecord, ScannerConfig
from ai_advisor.schemas import StockAdviceContext


APP_PATH = Path(__file__).parents[1] / "apps" / "ai_advisor_streamlit.py"

spec = importlib.util.spec_from_file_location("ai_advisor_streamlit_app_m5", APP_PATH)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def test_local_official_raw_files_generate_contexts_for_existing_fake_batch_flow(tmp_path: Path) -> None:
    output_dir = tmp_path / "scanner_contexts"
    raw_files = _write_local_raw_fixture_files(tmp_path)

    scanner_result = scan_local_raw_market_data(
        listed_stock_file=raw_files["listed_stock_file"],
        otc_stock_file=raw_files["otc_stock_file"],
        taiex_benchmark_file=raw_files["taiex_benchmark_file"],
        otc_benchmark_file=raw_files["otc_benchmark_file"],
        config=ScannerConfig(min_output_warning_threshold=20, max_output=50),
        output_dir=output_dir,
    )

    assert scanner_result.summary.input_candidate_count == 20
    assert scanner_result.summary.output_context_count >= 20
    assert not any("fewer than 20 contexts generated" in warning for warning in scanner_result.summary.warnings)
    assert (
        "source latest_date mismatch: listed_stock=2024-03-01; otc_stock=2024-03-02; "
        "taiex_benchmark=2024-03-01; otc_benchmark=2024-03-02"
    ) in scanner_result.summary.warnings

    source_audit = scanner_result.summary.source_audit
    assert source_audit["listed_stock"].record_count == 12 * 61
    assert source_audit["otc_stock"].record_count == 8 * 61
    assert source_audit["taiex_benchmark"].record_count == 61
    assert source_audit["otc_benchmark"].record_count == 61
    assert source_audit["listed_stock"].skipped_row_count == 1
    assert source_audit["otc_stock"].skipped_row_count == 1
    assert source_audit["taiex_benchmark"].skipped_row_count == 1
    assert source_audit["otc_benchmark"].skipped_row_count == 1
    assert any(
        reason.startswith("non-common security excluded")
        for reason in source_audit["listed_stock"].raw_skip_reason_counts
    )
    assert source_audit["taiex_benchmark"].raw_skip_reason_counts == {"missing required field(s): close": 1}
    assert source_audit["listed_stock"].latest_date == "2024-03-01"
    assert source_audit["otc_stock"].latest_date == "2024-03-02"

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


def test_local_official_raw_cli_json_summary_includes_source_audit(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "cli_contexts"
    raw_files = _write_local_raw_fixture_files(tmp_path)

    exit_code = scanner_cli_main(
        [
            "--listed-stock-file",
            str(raw_files["listed_stock_file"]),
            "--otc-stock-file",
            str(raw_files["otc_stock_file"]),
            "--taiex-benchmark-file",
            str(raw_files["taiex_benchmark_file"]),
            "--otc-benchmark-file",
            str(raw_files["otc_benchmark_file"]),
            "--output",
            str(output_dir),
            "--max-output",
            "50",
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["output_context_count"] == 20
    assert summary["source_audit"]["listed_stock"]["record_count"] == 12 * 61
    assert summary["source_audit"]["listed_stock"]["skipped_row_count"] == 1
    assert summary["source_audit"]["otc_stock"]["latest_date"] == "2024-03-02"
    assert any(warning.startswith("source latest_date mismatch") for warning in summary["warnings"])


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


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_local_raw_fixture_files(tmp_path: Path) -> dict[str, Path]:
    raw_dir = tmp_path / "raw"
    listed_stock_file = raw_dir / "listed_stock_day_all_aggregate.csv"
    otc_stock_file = raw_dir / "otc_daily_close_quotes_aggregate.csv"
    taiex_benchmark_file = raw_dir / "taiex_mi_index_aggregate.csv"
    otc_benchmark_file = raw_dir / "otc_index_aggregate.csv"

    _write_csv(
        listed_stock_file,
        [
            "Date",
            "Code",
            "Name",
            "TradeVolume",
            "TradeValue",
            "OpeningPrice",
            "HighestPrice",
            "LowestPrice",
            "ClosingPrice",
            "Change",
            "Transaction",
            "IsLimitUp",
        ],
        [
            row
            for index in range(12)
            for row in _listed_raw_rows(str(3100 + index), target_above_close=10 + index * 0.1)
        ]
        + [_listed_non_common_raw_row()],
    )
    _write_csv(
        otc_stock_file,
        [
            "Date",
            "SecuritiesCompanyCode",
            "CompanyName",
            "Close",
            "Change",
            "Open",
            "High",
            "Low",
            "TradingShares",
            "TransactionAmount",
            "TransactionNumber",
            "IsLimitUp",
            "NextLimitUp",
            "NextLimitDown",
        ],
        [
            row
            for index in range(8)
            for row in _otc_raw_rows(
                str(3200 + index),
                target_above_close=11 + index * 0.1,
                start_date=date(2024, 1, 2),
            )
        ]
        + [_otc_non_common_raw_row()],
    )
    _write_csv(
        taiex_benchmark_file,
        ["Date", "IndexName", "OpeningIndex", "HighestIndex", "LowestIndex", "ClosingIndex", "Change"],
        _taiex_benchmark_rows() + [_invalid_taiex_benchmark_raw_row()],
    )
    _write_csv(
        otc_benchmark_file,
        ["Date", "IndexName", "Open", "High", "Low", "Close", "Change"],
        _otc_benchmark_rows(start_date=date(2024, 1, 2)) + [_invalid_otc_benchmark_raw_row()],
    )
    return {
        "listed_stock_file": listed_stock_file,
        "otc_stock_file": otc_stock_file,
        "taiex_benchmark_file": taiex_benchmark_file,
        "otc_benchmark_file": otc_benchmark_file,
    }


def _listed_raw_rows(
    stock_id: str,
    *,
    target_above_close: float,
    start_date: date = date(2024, 1, 1),
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    previous_close: float | None = None
    for record in scanner_stock_series(stock_id, "listed", target_above_close=target_above_close, start_date=start_date):
        rows.append(
            {
                "Date": _roc_compact(record.date),
                "Code": record.stock_id,
                "Name": record.name,
                "TradeVolume": record.volume,
                "TradeValue": record.turnover_value,
                "OpeningPrice": record.open,
                "HighestPrice": record.high,
                "LowestPrice": record.low,
                "ClosingPrice": record.close,
                "Change": "" if previous_close is None else record.close - previous_close,
                "Transaction": 1000,
                "IsLimitUp": "false",
            }
        )
        previous_close = record.close
    return rows


def _otc_raw_rows(
    stock_id: str,
    *,
    target_above_close: float,
    start_date: date = date(2024, 1, 1),
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    previous_close: float | None = None
    for record in scanner_stock_series(stock_id, "otc", target_above_close=target_above_close, start_date=start_date):
        rows.append(
            {
                "Date": _roc_compact(record.date),
                "SecuritiesCompanyCode": record.stock_id,
                "CompanyName": record.name,
                "Close": record.close,
                "Change": "" if previous_close is None else record.close - previous_close,
                "Open": record.open,
                "High": record.high,
                "Low": record.low,
                "TradingShares": record.volume,
                "TransactionAmount": record.turnover_value,
                "TransactionNumber": 1000,
                "IsLimitUp": "false",
                "NextLimitUp": record.close * 1.1,
                "NextLimitDown": record.close * 0.9,
            }
        )
        previous_close = record.close
    return rows


def _listed_non_common_raw_row() -> dict[str, object]:
    return {
        "Date": "1130301",
        "Code": "0050",
        "Name": "ETF 0050",
        "TradeVolume": 1_000_000,
        "TradeValue": 100_000_000,
        "OpeningPrice": 100,
        "HighestPrice": 101,
        "LowestPrice": 99,
        "ClosingPrice": 100,
        "Change": 0,
        "Transaction": 1000,
        "IsLimitUp": "false",
    }


def _otc_non_common_raw_row() -> dict[str, object]:
    return {
        "Date": "1130302",
        "SecuritiesCompanyCode": "006201",
        "CompanyName": "ETF 006201",
        "Close": 100,
        "Change": 0,
        "Open": 100,
        "High": 101,
        "Low": 99,
        "TradingShares": 1_000_000,
        "TransactionAmount": 100_000_000,
        "TransactionNumber": 1000,
        "IsLimitUp": "false",
        "NextLimitUp": 110,
        "NextLimitDown": 90,
    }


def _taiex_benchmark_rows(start_date: date = date(2024, 1, 1)) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    previous_close: float | None = None
    for record in scanner_benchmark_series("TAIEX", start_close=100, step=0.2, start_date=start_date):
        rows.append(
            {
                "Date": _roc_compact(record.date),
                "IndexName": "TAIEX",
                "OpeningIndex": record.close - 0.1,
                "HighestIndex": record.close + 0.3,
                "LowestIndex": record.close - 0.3,
                "ClosingIndex": record.close,
                "Change": "" if previous_close is None else record.close - previous_close,
            }
        )
        previous_close = record.close
    return rows


def _otc_benchmark_rows(start_date: date = date(2024, 1, 1)) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    previous_close: float | None = None
    for record in scanner_benchmark_series("OTC", start_close=80, step=0.15, start_date=start_date):
        rows.append(
            {
                "Date": _gregorian_compact(record.date),
                "IndexName": "OTC",
                "Open": record.close - 0.1,
                "High": record.close + 0.3,
                "Low": record.close - 0.3,
                "Close": record.close,
                "Change": "" if previous_close is None else record.close - previous_close,
            }
        )
        previous_close = record.close
    return rows


def _invalid_taiex_benchmark_raw_row() -> dict[str, object]:
    return {
        "Date": "1130301",
        "IndexName": "TAIEX",
        "OpeningIndex": 100,
        "HighestIndex": 101,
        "LowestIndex": 99,
        "ClosingIndex": "",
        "Change": "",
    }


def _invalid_otc_benchmark_raw_row() -> dict[str, object]:
    return {
        "Date": "20240302",
        "IndexName": "OTC",
        "Open": 100,
        "High": 101,
        "Low": 99,
        "Close": "",
        "Change": "",
    }


def _roc_compact(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.year - 1911:03d}{parsed.month:02d}{parsed.day:02d}"


def _gregorian_compact(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.year:04d}{parsed.month:02d}{parsed.day:02d}"


def scanner_stock_series(
    stock_id: str,
    market_type: str,
    *,
    target_above_close: float,
    length: int = 61,
    start_date: date = date(2024, 1, 1),
) -> list[DailyStockRecord]:
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
                date=(start_date + timedelta(days=index)).isoformat(),
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
    start_date: date = date(2024, 1, 1),
) -> list[BenchmarkDailyRecord]:
    return [
        BenchmarkDailyRecord(
            source="m5-integration-fixture",
            benchmark_symbol=symbol,
            date=(start_date + timedelta(days=index)).isoformat(),
            close=start_close + index * step,
        )
        for index in range(length)
    ]
