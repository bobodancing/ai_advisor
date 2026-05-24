from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    DailyStockRecord,
    LocalRawMarketDataSnapshot,
    RawBenchmarkLoadResult,
    RawStockLoadResult,
    ScannerBenchmarkSymbol,
    ScannerMarketType,
    SkippedRawRow,
)


EMPTY_TOKENS = {
    "",
    "-",
    "--",
    "---",
    "----",
    "N/A",
    "NA",
    "NULL",
    "NONE",
    "無",
    "暫停交易",
    "停止交易",
    "除權息",
    "不適用",
}

NON_COMMON_STOCK_NAME_KEYWORDS = (
    "ETF",
    "ETN",
    "權證",
    "認購",
    "認售",
    "購",
    "售",
    "牛",
    "熊",
    "債",
    "受益證券",
    "指數投資證券",
    "存託憑證",
    "TDR",
    "特別股",
    "可轉債",
)

LISTED_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("Date", "date", "日期"),
    "stock_id": ("Code", "code", "證券代號", "有價證券代號"),
    "name": ("Name", "name", "證券名稱", "有價證券名稱"),
    "open": ("OpeningPrice", "Open", "open", "開盤價"),
    "high": ("HighestPrice", "High", "high", "最高價"),
    "low": ("LowestPrice", "Low", "low", "最低價"),
    "close": ("ClosingPrice", "Close", "close", "收盤價"),
    "change": ("Change", "change", "漲跌價差", "漲跌"),
    "volume": ("TradeVolume", "TradingShares", "成交股數", "成交量"),
    "turnover_value": ("TradeValue", "TransactionAmount", "成交金額"),
    "transactions": ("Transaction", "TransactionNumber", "成交筆數"),
    "is_limit_up": ("IsLimitUp", "LimitUpFlag", "漲停註記"),
    "next_limit_up": ("NextLimitUp", "漲停價"),
    "next_limit_down": ("NextLimitDown", "跌停價"),
}

OTC_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("Date", "date", "日期"),
    "stock_id": ("SecuritiesCompanyCode", "Code", "code", "代號", "證券代號"),
    "name": ("CompanyName", "Name", "name", "名稱", "證券名稱"),
    "open": ("Open", "OpeningPrice", "open", "開盤價"),
    "high": ("High", "HighestPrice", "high", "最高價"),
    "low": ("Low", "LowestPrice", "low", "最低價"),
    "close": ("Close", "ClosingPrice", "close", "收盤價"),
    "change": ("Change", "change", "漲跌"),
    "volume": ("TradingShares", "TradeVolume", "成交股數", "成交量"),
    "turnover_value": ("TransactionAmount", "TradeValue", "成交金額"),
    "transactions": ("TransactionNumber", "Transaction", "成交筆數"),
    "is_limit_up": ("IsLimitUp", "LimitUpFlag", "漲停註記"),
    "next_limit_up": ("NextLimitUp", "漲停價"),
    "next_limit_down": ("NextLimitDown", "跌停價"),
}

BENCHMARK_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("Date", "date", "日期"),
    "symbol": ("BenchmarkSymbol", "benchmark_symbol", "IndexCode", "指數代號"),
    "name": ("IndexName", "Name", "name", "指數名稱"),
    "open": ("OpeningIndex", "OpeningPrice", "Open", "open", "開盤指數", "開盤價"),
    "high": ("HighestIndex", "HighestPrice", "High", "high", "最高指數", "最高價"),
    "low": ("LowestIndex", "LowestPrice", "Low", "low", "最低指數", "最低價"),
    "close": (
        "ClosingIndex",
        "ClosingPrice",
        "Close",
        "close",
        "TAIEX",
        "收盤指數",
        "收盤價",
        "發行量加權股價指數",
        "櫃買指數",
    ),
    "change": ("Change", "change", "漲跌", "漲跌點數"),
}

NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


def load_listed_stock_daily_records(path: str | Path) -> RawStockLoadResult:
    return load_stock_daily_records(path, market_type="listed")


def load_otc_stock_daily_records(path: str | Path) -> RawStockLoadResult:
    return load_stock_daily_records(path, market_type="otc")


def load_stock_daily_records(path: str | Path, market_type: ScannerMarketType) -> RawStockLoadResult:
    source_path = Path(path)
    aliases = LISTED_ALIASES if market_type == "listed" else OTC_ALIASES
    records: list[DailyStockRecord] = []
    skipped_rows: list[SkippedRawRow] = []

    for row_number, row in enumerate(_read_rows(source_path), start=1):
        stock_id = _clean_text(_pick(row, aliases["stock_id"]))
        name = _clean_text(_pick(row, aliases["name"]))
        parsed_date = parse_market_date(_pick(row, aliases["date"]))
        classification, classification_notes = classify_instrument(stock_id, name)

        if classification != "common_stock_candidate":
            skipped_rows.append(
                _skip_stock_row(
                    source_path,
                    row_number,
                    market_type,
                    row,
                    "non-common security excluded: " + "; ".join(classification_notes),
                    stock_id,
                    name,
                    parsed_date,
                )
            )
            continue

        parsed_numbers = {
            "open": parse_number(_pick(row, aliases["open"])),
            "high": parse_number(_pick(row, aliases["high"])),
            "low": parse_number(_pick(row, aliases["low"])),
            "close": parse_number(_pick(row, aliases["close"])),
            "volume": parse_int(_pick(row, aliases["volume"])),
            "turnover_value": parse_int(_pick(row, aliases["turnover_value"])),
            "change": parse_number(_pick(row, aliases["change"])),
            "transactions": parse_int(_pick(row, aliases["transactions"])),
            "next_limit_up": parse_number(_pick(row, aliases["next_limit_up"])),
            "next_limit_down": parse_number(_pick(row, aliases["next_limit_down"])),
        }
        missing_fields = [
            field
            for field in ("open", "high", "low", "close", "volume", "turnover_value")
            if parsed_numbers[field] is None
        ]
        if parsed_date is None:
            missing_fields.append("date")
        if not stock_id:
            missing_fields.append("stock_id")
        if not name:
            missing_fields.append("name")

        close = parsed_numbers["close"]
        if close is not None and close <= 0:
            skipped_rows.append(
                _skip_stock_row(
                    source_path,
                    row_number,
                    market_type,
                    row,
                    "invalid close price <= 0",
                    stock_id,
                    name,
                    parsed_date,
                )
            )
            continue

        if missing_fields:
            skipped_rows.append(
                _skip_stock_row(
                    source_path,
                    row_number,
                    market_type,
                    row,
                    "missing required field(s): " + ", ".join(sorted(set(missing_fields))),
                    stock_id,
                    name,
                    parsed_date,
                )
            )
            continue

        records.append(
            DailyStockRecord(
                source=_source_label(source_path),
                market_type=market_type,
                date=parsed_date,
                stock_id=stock_id,
                name=name,
                open=parsed_numbers["open"],
                high=parsed_numbers["high"],
                low=parsed_numbers["low"],
                close=close,
                volume=parsed_numbers["volume"],
                turnover_value=parsed_numbers["turnover_value"],
                change=parsed_numbers["change"],
                transactions=parsed_numbers["transactions"],
                is_limit_up=parse_optional_bool(_pick(row, aliases["is_limit_up"])),
                next_limit_up=parsed_numbers["next_limit_up"],
                next_limit_down=parsed_numbers["next_limit_down"],
                instrument_classification=classification,
                classification_notes=classification_notes,
                raw_fields=dict(row),
            )
        )

    return RawStockLoadResult(
        source_path=str(source_path),
        market_type=market_type,
        records=records,
        skipped_rows=skipped_rows,
    )


def load_benchmark_daily_records(
    path: str | Path,
    benchmark_symbol: ScannerBenchmarkSymbol,
) -> RawBenchmarkLoadResult:
    source_path = Path(path)
    records: list[BenchmarkDailyRecord] = []
    skipped_rows: list[SkippedRawRow] = []

    for row_number, row in enumerate(_read_rows(source_path), start=1):
        if not _row_matches_benchmark(row, benchmark_symbol):
            continue

        parsed_date = parse_market_date(_pick(row, BENCHMARK_ALIASES["date"]))
        close = parse_number(_pick(row, BENCHMARK_ALIASES["close"]))
        missing_fields: list[str] = []
        if parsed_date is None:
            missing_fields.append("date")
        if close is None:
            missing_fields.append("close")
        elif close <= 0:
            skipped_rows.append(
                _skip_benchmark_row(
                    source_path,
                    row_number,
                    benchmark_symbol,
                    row,
                    "invalid benchmark close <= 0",
                    parsed_date,
                )
            )
            continue

        if missing_fields:
            skipped_rows.append(
                _skip_benchmark_row(
                    source_path,
                    row_number,
                    benchmark_symbol,
                    row,
                    "missing required field(s): " + ", ".join(missing_fields),
                    parsed_date,
                )
            )
            continue

        records.append(
            BenchmarkDailyRecord(
                source=_source_label(source_path),
                benchmark_symbol=benchmark_symbol,
                date=parsed_date,
                close=close,
                change=parse_number(_pick(row, BENCHMARK_ALIASES["change"])),
                open=parse_number(_pick(row, BENCHMARK_ALIASES["open"])),
                high=parse_number(_pick(row, BENCHMARK_ALIASES["high"])),
                low=parse_number(_pick(row, BENCHMARK_ALIASES["low"])),
                raw_fields=dict(row),
            )
        )

    return RawBenchmarkLoadResult(
        source_path=str(source_path),
        benchmark_symbol=benchmark_symbol,
        records=records,
        skipped_rows=skipped_rows,
    )


def load_local_raw_market_data_snapshot(
    listed_stock_path: str | Path,
    otc_stock_path: str | Path,
    taiex_benchmark_path: str | Path,
    otc_benchmark_path: str | Path,
) -> LocalRawMarketDataSnapshot:
    return LocalRawMarketDataSnapshot(
        listed_stocks=load_listed_stock_daily_records(listed_stock_path),
        otc_stocks=load_otc_stock_daily_records(otc_stock_path),
        taiex_benchmark=load_benchmark_daily_records(taiex_benchmark_path, "TAIEX"),
        otc_benchmark=load_benchmark_daily_records(otc_benchmark_path, "OTC"),
    )


def parse_market_date(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None or _is_empty_token(text):
        return None

    compact_digits = re.sub(r"\D", "", text)
    if re.fullmatch(r"\d{8}", compact_digits):
        year = int(compact_digits[:4])
        if year >= 1900:
            return _iso_date(year, int(compact_digits[4:6]), int(compact_digits[6:8]))
    if re.fullmatch(r"\d{7}", compact_digits):
        return _iso_date(int(compact_digits[:3]) + 1911, int(compact_digits[3:5]), int(compact_digits[5:7]))

    normalized = (
        text.replace("民國", "")
        .replace("年", "/")
        .replace("月", "/")
        .replace("日", "")
        .replace("-", "/")
        .replace(".", "/")
    )
    parts = [part for part in normalized.split("/") if part]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None

    year = int(parts[0])
    if year < 1900:
        year += 1911
    return _iso_date(year, int(parts[1]), int(parts[2]))


def parse_number(value: Any) -> float | None:
    text = _normalize_text(value)
    if text is None or _is_empty_token(text):
        return None

    text = (
        text.replace(",", "")
        .replace("%", "")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("−", "-")
        .replace(" ", "")
    )
    if _is_empty_token(text) or not NUMERIC_PATTERN.match(text):
        return None
    return float(text)


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    if number is None:
        return None
    return int(number)


def parse_optional_bool(value: Any) -> bool | None:
    text = _normalize_text(value)
    if text is None or _is_empty_token(text):
        return None
    normalized = text.lower()
    if normalized in {"true", "t", "1", "yes", "y", "漲停"}:
        return True
    if normalized in {"false", "f", "0", "no", "n", "否"}:
        return False
    return None


def classify_instrument(stock_id: str | None, name: str | None) -> tuple[str, list[str]]:
    if not stock_id:
        return "unknown", ["missing stock_id; cannot verify ordinary common-stock status"]

    normalized_code = _normalize_text(stock_id) or ""
    normalized_name = (_normalize_text(name) or "").upper()

    if not re.fullmatch(r"\d{4}", normalized_code):
        return "non_common_stock", ["stock_id is not exactly four digits"]
    if normalized_code.startswith("0"):
        return "non_common_stock", ["stock_id starts with 0; likely ETF, warrant, or other non-common instrument"]

    matched_keywords = [keyword for keyword in NON_COMMON_STOCK_NAME_KEYWORDS if keyword.upper() in normalized_name]
    if matched_keywords:
        return "non_common_stock", ["name contains non-common instrument keyword(s): " + ", ".join(matched_keywords)]

    return (
        "common_stock_candidate",
        ["M1 heuristic: four-digit code with no excluded instrument keyword; universe certification pending"],
    )


def _read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _read_json_rows(path)
    if suffix in {".csv", ".txt"}:
        return _read_csv_rows(path)
    raise ValueError(f"Unsupported local raw market data file type: {path.suffix}")


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows: Any
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = next(
            (data[key] for key in ("data", "records", "items", "result") if isinstance(data.get(key), list)),
            None,
        )
    else:
        rows = None

    if not isinstance(rows, list):
        raise ValueError(f"JSON market data file must contain a row list: {path}")
    return [_coerce_row(row) for row in rows]


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _coerce_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("Market data rows must be JSON objects or CSV records")
    return {str(key): value for key, value in row.items()}


def _pick(row: dict[str, Any], aliases: Iterable[str]) -> Any:
    normalized_map = {_normalize_key(key): key for key in row}
    for alias in aliases:
        key = normalized_map.get(_normalize_key(alias))
        if key is not None:
            return row[key]
    return None


def _row_matches_benchmark(row: dict[str, Any], benchmark_symbol: ScannerBenchmarkSymbol) -> bool:
    symbol = _clean_text(_pick(row, BENCHMARK_ALIASES["symbol"]))
    name = _clean_text(_pick(row, BENCHMARK_ALIASES["name"]))
    if not symbol and not name:
        return True

    searchable = " ".join(part for part in (symbol, name) if part).upper()
    if benchmark_symbol == "TAIEX":
        return any(token in searchable for token in ("TAIEX", "加權", "發行量加權"))
    return any(token in searchable for token in ("OTC", "櫃買"))


def _skip_stock_row(
    source_path: Path,
    row_number: int,
    market_type: ScannerMarketType,
    row: dict[str, Any],
    reason: str,
    stock_id: str | None,
    name: str | None,
    parsed_date: str | None,
) -> SkippedRawRow:
    return SkippedRawRow(
        source=_source_label(source_path),
        row_number=row_number,
        reason=reason,
        market_type=market_type,
        stock_id=stock_id,
        name=name,
        date=parsed_date,
        raw_fields=dict(row),
    )


def _skip_benchmark_row(
    source_path: Path,
    row_number: int,
    benchmark_symbol: ScannerBenchmarkSymbol,
    row: dict[str, Any],
    reason: str,
    parsed_date: str | None,
) -> SkippedRawRow:
    return SkippedRawRow(
        source=_source_label(source_path),
        row_number=row_number,
        reason=reason,
        benchmark_symbol=benchmark_symbol,
        date=parsed_date,
        raw_fields=dict(row),
    )


def _normalize_key(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value)).strip().lower()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    return unicodedata.normalize("NFKC", str(value)).strip()


def _clean_text(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None or _is_empty_token(text):
        return None
    return text


def _is_empty_token(value: str) -> bool:
    return value.strip().upper() in EMPTY_TOKENS


def _iso_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _source_label(path: Path) -> str:
    return path.name
