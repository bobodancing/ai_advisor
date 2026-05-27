from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "prepare_market_scanner_pilot_raw_data.py"
spec = importlib.util.spec_from_file_location("prepare_market_scanner_pilot_raw_data", SCRIPT_PATH)
assert spec and spec.loader
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)


START = date(2026, 5, 1)
END = date(2026, 5, 31)


def test_twse_stock_rows_normalize_to_scanner_stock_csv_fields() -> None:
    payload = {
        "stat": "OK",
        "title": "115年05月 2330 台積電           各日成交資訊",
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數", "註記"],
        "data": [["115/05/04", "44,458,732", "99,944,198,300", "2,200.00", "2,285.00", "2,195.00", "2,275.00", "+140.00", "129,173", ""]],
    }

    result = helper.normalize_twse_stock_payload(payload, helper.WatchlistEntry("2330", "listed", "TSMC"), START, END)

    assert result.malformed_rows == []
    assert result.rows == [
        {
            "Date": "2026-05-04",
            "Code": "2330",
            "Name": "台積電",
            "Open": "2200",
            "High": "2285",
            "Low": "2195",
            "Close": "2275",
            "TradeVolume": "44458732",
            "TradeValue": "99944198300",
            "Change": "140",
            "Transaction": "129173",
            "IsLimitUp": "",
        }
    ]


def test_tpex_stock_rows_normalize_to_scanner_stock_csv_fields() -> None:
    payload = {
        "stat": "ok",
        "name": "環球晶",
        "tables": [
            {
                "title": "個股日成交資訊",
                "subtitle": "6488 環球晶 115年05月",
                "fields": ["日 期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"],
                "data": [["115/05/04", "9,995", "6,114,837", "605.00", "628.00", "597.00", "606.00", "26.00", "17,616"]],
            }
        ],
    }

    result = helper.normalize_tpex_stock_payload(payload, helper.WatchlistEntry("6488", "otc", "GlobalWafers"), START, END)

    assert result.malformed_rows == []
    assert result.rows == [
        {
            "Date": "2026-05-04",
            "Code": "6488",
            "Name": "環球晶",
            "Open": "605",
            "High": "628",
            "Low": "597",
            "Close": "606",
            "TradeVolume": "9995000",
            "TradeValue": "6114837000",
            "Change": "26",
            "Transaction": "17616",
            "IsLimitUp": "",
        }
    ]


def test_taiex_benchmark_rows_normalize_to_scanner_benchmark_csv_fields() -> None:
    payload = {
        "stat": "OK",
        "fields": ["日期", "開盤指數", "最高指數", "最低指數", "收盤指數"],
        "data": [["115/05/04", "39,228.39", "40,755.52", "39,228.39", "40,705.14"]],
    }

    result = helper.normalize_twse_taiex_payload(payload, START, END)

    assert result.malformed_rows == []
    assert result.rows == [
        {
            "Date": "2026-05-04",
            "BenchmarkSymbol": "TAIEX",
            "IndexName": "TAIEX",
            "Open": "39228.39",
            "High": "40755.52",
            "Low": "39228.39",
            "Close": "40705.14",
            "Change": "",
        }
    ]


def test_otc_benchmark_rows_normalize_to_scanner_benchmark_csv_fields() -> None:
    payload = {
        "stat": "ok",
        "tables": [
            {
                "title": "櫃買指數(月查詢)",
                "fields": ["日期", "開市", "最高", "最低", "收市", "漲/跌"],
                "data": [["2026/05/04", "385.82", "398.43", "385.82", "398.25", "13.67"]],
            }
        ],
    }

    result = helper.normalize_tpex_index_payload(payload, START, END)

    assert result.malformed_rows == []
    assert result.rows == [
        {
            "Date": "2026-05-04",
            "BenchmarkSymbol": "OTC",
            "IndexName": "OTC",
            "Open": "385.82",
            "High": "398.43",
            "Low": "385.82",
            "Close": "398.25",
            "Change": "13.67",
        }
    ]


def test_missing_official_same_day_limit_up_leaves_is_limit_up_blank() -> None:
    listed_payload = {
        "stat": "OK",
        "title": "115年05月 2330 台積電           各日成交資訊",
        "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
        "data": [["115/05/04", "1", "2", "3", "4", "2", "3", "0", "5"]],
    }
    otc_payload = {
        "stat": "ok",
        "tables": [
            {
                "subtitle": "6488 環球晶 115年05月",
                "fields": ["日 期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"],
                "data": [["115/05/04", "1", "2", "3", "4", "2", "3", "0", "5"]],
            }
        ],
    }

    listed = helper.normalize_twse_stock_payload(listed_payload, helper.WatchlistEntry("2330", "listed", "TSMC"), START, END)
    otc = helper.normalize_tpex_stock_payload(otc_payload, helper.WatchlistEntry("6488", "otc", "GlobalWafers"), START, END)

    assert listed.rows[0]["IsLimitUp"] == ""
    assert otc.rows[0]["IsLimitUp"] == ""


def test_twse_stock_change_x_token_preserves_row_and_outputs_blank_change() -> None:
    payload = {
        "stat": "OK",
        "title": "115/05 2330 TSMC",
        "fields": helper.TWSE_STOCK_REQUIRED_FIELDS,
        "data": [["115/05/04", "44,458,732", "99,944,198,300", "2,200.00", "2,285.00", "2,195.00", "2,275.00", "X0.00", "129,173"]],
    }

    result = helper.normalize_twse_stock_payload(payload, helper.WatchlistEntry("2330", "listed", "TSMC"), START, END)

    assert result.malformed_rows == []
    assert result.rows[0]["Change"] == ""
    assert result.rows[0]["Close"] == "2275"
    assert result.optional_change_anomalies == [
        {
            "row_index": 1,
            "date": "2026-05-04",
            "raw_change": "X0.00",
            "reason": "non-numeric optional Change token",
        }
    ]


def test_malformed_required_ohlcv_still_skips_row() -> None:
    payload = {
        "stat": "OK",
        "title": "115/05 2330 TSMC",
        "fields": helper.TWSE_STOCK_REQUIRED_FIELDS,
        "data": [["115/05/04", "44,458,732", "99,944,198,300", "2,200.00", "2,285.00", "2,195.00", "X0.00", "0.00", "129,173"]],
    }

    result = helper.normalize_twse_stock_payload(payload, helper.WatchlistEntry("2330", "listed", "TSMC"), START, END)

    assert result.rows == []
    assert result.optional_change_anomalies == []
    assert len(result.malformed_rows) == 1
    assert "invalid numeric value: X0.00" in result.malformed_rows[0]["reason"]


def test_prep_audit_includes_optional_change_anomaly_metadata(tmp_path: Path) -> None:
    watchlist = tmp_path / "watchlist.csv"
    watchlist.write_text(
        "stock_id,market_type,stock_name_optional,category,reason_optional\n"
        "5274,otc,SignalKing,AI,test provenance\n",
        encoding="utf-8",
    )

    def fake_fetch(url: str):
        if "tradingStock" in url:
            return {
                "stat": "ok",
                "name": "SignalKing",
                "tables": [
                    {
                        "fields": helper.TPEX_STOCK_REQUIRED_FIELDS,
                        "data": [["115/05/04", "1", "2", "3", "4", "2", "3", "X0.00", "5"]],
                    }
                ],
            }
        if "MI_5MINS_HIST" in url:
            return {
                "stat": "OK",
                "fields": helper.TWSE_TAIEX_REQUIRED_FIELDS,
                "data": [["115/05/04", "10", "11", "9", "10"]],
            }
        if "indexInfo/inx" in url:
            return {
                "stat": "ok",
                "tables": [
                    {
                        "fields": helper.TPEX_INDEX_REQUIRED_FIELDS,
                        "data": [["2026/05/04", "10", "11", "9", "10", "0"]],
                    }
                ],
            }
        raise AssertionError(f"unexpected URL: {url}")

    audit = helper.prepare_pilot_raw_data(
        watchlist_path=watchlist,
        output_dir=tmp_path / "out",
        start_date=START,
        end_date=END,
        fetch_json=fake_fetch,
        request_sleep_seconds=0,
    )

    assert audit["optional_change_anomalies"]["count"] == 1
    assert audit["optional_change_anomalies"]["samples"][0]["stock_id"] == "5274"
    assert audit["optional_change_anomalies"]["samples"][0]["raw_change"] == "X0.00"
    assert audit["market_type_corrections"][0] == {
        "stock_id": "5274",
        "from": "listed",
        "to": "otc",
        "actual_market_type": "otc",
        "reason": "watchlist market_type corrected from listed to otc by official source check",
        "status": "applied",
    }
    assert audit["per_symbol_latest_date"]["5274"] == "2026-05-04"


def test_market_type_correction_audit_marks_corrected_watchlist_as_applied() -> None:
    audit_rows = helper._market_type_correction_audit(
        [
            helper.WatchlistEntry("5274", "otc", "SignalKing"),
            helper.WatchlistEntry("6274", "otc", "Taiwan Union"),
        ]
    )

    assert audit_rows == [
        {
            "stock_id": "5274",
            "from": "listed",
            "to": "otc",
            "actual_market_type": "otc",
            "reason": "watchlist market_type corrected from listed to otc by official source check",
            "status": "applied",
        },
        {
            "stock_id": "6274",
            "from": "listed",
            "to": "otc",
            "actual_market_type": "otc",
            "reason": "watchlist market_type corrected from listed to otc by official source check",
            "status": "applied",
        },
    ]


def test_market_type_correction_audit_marks_uncorrected_watchlist_as_not_applied() -> None:
    audit_rows = helper._market_type_correction_audit([helper.WatchlistEntry("5274", "listed", "SignalKing")])

    assert audit_rows[0] == {
        "stock_id": "5274",
        "from": "listed",
        "to": "otc",
        "actual_market_type": "listed",
        "reason": "watchlist market_type corrected from listed to otc by official source check",
        "status": "not_applied",
    }
    assert audit_rows[1]["stock_id"] == "6274"
    assert audit_rows[1]["actual_market_type"] is None
    assert audit_rows[1]["status"] == "not_in_watchlist"
