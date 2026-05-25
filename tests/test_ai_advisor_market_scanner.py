from __future__ import annotations

from pathlib import Path

from ai_advisor.market_scanner import (
    load_benchmark_daily_records,
    load_listed_stock_daily_records,
    load_local_raw_market_data_snapshot,
    load_otc_stock_daily_records,
)
from ai_advisor.market_scanner.local_raw_adapter import parse_market_date, parse_number


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ai_advisor" / "market_scanner"


def test_source_contract_parses_roc_dates_gregorian_dates_and_numbers() -> None:
    assert parse_market_date("113/05/24") == "2024-05-24"
    assert parse_market_date("113年5月24日") == "2024-05-24"
    assert parse_market_date("2024-05-24") == "2024-05-24"
    assert parse_market_date("20240524") == "2024-05-24"

    assert parse_number("21,565.34") == 21565.34
    assert parse_number("+45.12") == 45.12
    assert parse_number("-0.83") == -0.83
    assert parse_number("X0.00") is None
    assert parse_number("除權息") is None


def test_listed_official_format_rows_load_into_typed_stock_records() -> None:
    result = load_listed_stock_daily_records(FIXTURE_DIR / "listed_stock_day_all_sample.json")

    assert result.market_type == "listed"
    assert len(result.records) == 1
    record = result.records[0]
    assert record.market_type == "listed"
    assert record.date == "2024-05-24"
    assert record.stock_id == "2330"
    assert record.name == "台積電"
    assert record.open == 850
    assert record.high == 872
    assert record.low == 848
    assert record.close == 865
    assert record.change == 15
    assert record.volume == 45678901
    assert record.turnover_value == 39012345678
    assert record.transactions == 42001
    assert record.instrument_classification == "common_stock_candidate"
    assert "universe certification pending" in record.classification_notes[0]

    skipped_by_stock_id = {row.stock_id: row.reason for row in result.skipped_rows}
    assert "0050" in skipped_by_stock_id
    assert "non-common security excluded" in skipped_by_stock_id["0050"]
    assert "2317" in skipped_by_stock_id
    assert "missing required field(s): close" in skipped_by_stock_id["2317"]


def test_otc_official_format_rows_load_into_typed_stock_records() -> None:
    result = load_otc_stock_daily_records(FIXTURE_DIR / "otc_daily_close_quotes_sample.json")

    assert result.market_type == "otc"
    assert len(result.records) == 1
    record = result.records[0]
    assert record.market_type == "otc"
    assert record.date == "2024-05-24"
    assert record.stock_id == "6488"
    assert record.name == "環球晶"
    assert record.open == 540
    assert record.high == 542
    assert record.low == 528
    assert record.close == 530
    assert record.change == -5
    assert record.volume == 1234567
    assert record.turnover_value == 654321000
    assert record.transactions == 3210
    assert record.next_limit_up == 583
    assert record.next_limit_down == 477

    skipped_by_stock_id = {row.stock_id: row.reason for row in result.skipped_rows}
    assert "00679B" in skipped_by_stock_id
    assert "stock_id is not exactly four digits" in skipped_by_stock_id["00679B"]
    assert "8926" in skipped_by_stock_id
    assert "missing required field(s): close" in skipped_by_stock_id["8926"]


def test_benchmark_official_format_rows_load_into_typed_records() -> None:
    taiex = load_benchmark_daily_records(FIXTURE_DIR / "taiex_benchmark_sample.json", "TAIEX")
    otc = load_benchmark_daily_records(FIXTURE_DIR / "otc_benchmark_sample.csv", "OTC")

    assert len(taiex.records) == 1
    assert taiex.records[0].benchmark_symbol == "TAIEX"
    assert taiex.records[0].date == "2024-05-24"
    assert taiex.records[0].close == 21565.34
    assert taiex.records[0].change == 45.12
    assert taiex.records[0].open == 21500

    assert len(otc.records) == 1
    assert otc.records[0].benchmark_symbol == "OTC"
    assert otc.records[0].date == "2024-05-24"
    assert otc.records[0].close == 268.75
    assert otc.records[0].change == -0.83


def test_local_raw_snapshot_keeps_listed_otc_and_benchmarks_distinct() -> None:
    snapshot = load_local_raw_market_data_snapshot(
        listed_stock_path=FIXTURE_DIR / "listed_stock_day_all_sample.json",
        otc_stock_path=FIXTURE_DIR / "otc_daily_close_quotes_sample.json",
        taiex_benchmark_path=FIXTURE_DIR / "taiex_benchmark_sample.json",
        otc_benchmark_path=FIXTURE_DIR / "otc_benchmark_sample.csv",
    )

    assert [record.market_type for record in snapshot.listed_stocks.records] == ["listed"]
    assert [record.market_type for record in snapshot.otc_stocks.records] == ["otc"]
    assert [record.benchmark_symbol for record in snapshot.taiex_benchmark.records] == ["TAIEX"]
    assert [record.benchmark_symbol for record in snapshot.otc_benchmark.records] == ["OTC"]

    skipped_ids = {row.stock_id for row in snapshot.listed_stocks.skipped_rows + snapshot.otc_stocks.skipped_rows}
    assert {"0050", "00679B"}.issubset(skipped_ids)
    loaded_ids = {record.stock_id for record in snapshot.listed_stocks.records + snapshot.otc_stocks.records}
    assert loaded_ids == {"2330", "6488"}


def test_official_csv_source_contract_rows_parse_with_chinese_headers() -> None:
    listed = load_listed_stock_daily_records(FIXTURE_DIR / "listed_stock_day_all_official_csv_sample.csv")
    otc = load_otc_stock_daily_records(FIXTURE_DIR / "otc_daily_close_quotes_official_csv_sample.csv")
    taiex = load_benchmark_daily_records(FIXTURE_DIR / "taiex_mi_index_official_csv_sample.csv", "TAIEX")
    otc_index = load_benchmark_daily_records(FIXTURE_DIR / "otc_index_official_csv_sample.csv", "OTC")

    assert [record.stock_id for record in listed.records] == ["2330"]
    assert listed.records[0].date == "2026-05-22"
    assert listed.records[0].name == "台積電"
    assert listed.records[0].close == 2255
    assert listed.records[0].volume == 26823133
    assert {row.stock_id for row in listed.skipped_rows} == {"0050"}

    assert [record.stock_id for record in otc.records] == ["6488"]
    assert otc.records[0].date == "2026-05-25"
    assert otc.records[0].name == "環球晶"
    assert otc.records[0].close == 788
    assert otc.records[0].change == 71
    assert otc.records[0].next_limit_up == 866
    assert otc.records[0].next_limit_down == 710
    assert {row.stock_id for row in otc.skipped_rows} == {"006201"}

    assert len(taiex.records) == 1
    assert taiex.records[0].date == "2026-05-22"
    assert taiex.records[0].close == 42267.97
    assert taiex.records[0].change == 899.76

    assert [record.date for record in otc_index.records] == ["2026-05-22", "2026-05-25"]
    assert otc_index.records[-1].close == 434.99
    assert otc_index.records[-1].open == 426.34
