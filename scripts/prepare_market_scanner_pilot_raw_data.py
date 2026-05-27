from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
import sys
import time
from http.cookiejar import CookieJar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


STOCK_COLUMNS = [
    "Date",
    "Code",
    "Name",
    "Open",
    "High",
    "Low",
    "Close",
    "TradeVolume",
    "TradeValue",
    "Change",
    "Transaction",
    "IsLimitUp",
]

BENCHMARK_COLUMNS = [
    "Date",
    "BenchmarkSymbol",
    "IndexName",
    "Open",
    "High",
    "Low",
    "Close",
    "Change",
]

TWSE_STOCK_REQUIRED_FIELDS = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"]
TPEX_STOCK_REQUIRED_FIELDS = ["日期", "成交張數", "成交仟元", "開盤", "最高", "最低", "收盤", "漲跌", "筆數"]
TWSE_TAIEX_REQUIRED_FIELDS = ["日期", "開盤指數", "最高指數", "最低指數", "收盤指數"]
TPEX_INDEX_REQUIRED_FIELDS = ["日期", "開市", "最高", "最低", "收市", "漲/跌"]

TWSE_STOCK_DAY_PATTERN = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={yyyymm01}&stockNo={stock_id}"
TWSE_TAIEX_PATTERN = "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=json&date={yyyymm01}"
TPEX_STOCK_PATTERN = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code={stock_id}&date={yyyy/mm/01}&response=json"
TPEX_INDEX_PATTERN = "https://www.tpex.org.tw/www/zh-tw/indexInfo/inx?date={yyyy/mm/01}&response=json"

LIMIT_UP_NOTE = (
    "Official historical monthly sources used by this one-shot helper do not expose a same-day "
    "limit-up flag; IsLimitUp is intentionally left blank."
)
MARKET_TYPE_CORRECTION_NOTE = "watchlist market_type corrected from listed to otc by official source check"
OFFICIAL_MARKET_TYPE_CORRECTIONS = {
    "5274": {"from": "listed", "to": "otc", "reason": MARKET_TYPE_CORRECTION_NOTE},
    "6274": {"from": "listed", "to": "otc", "reason": MARKET_TYPE_CORRECTION_NOTE},
}


class SourceContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class WatchlistEntry:
    stock_id: str
    market_type: str
    stock_name_optional: str = ""
    category: str = ""
    reason_optional: str = ""


@dataclass
class NormalizeResult:
    rows: list[dict[str, str]]
    malformed_rows: list[dict[str, Any]] = field(default_factory=list)
    optional_change_anomalies: list[dict[str, Any]] = field(default_factory=list)
    official_name: str | None = None


class OfficialJsonFetcher:
    def __init__(self, timeout_seconds: int = 30, retry_sleep_seconds: float = 2.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_sleep_seconds = retry_sleep_seconds
        self.tls_strict_verification_relaxed_urls: list[str] = []
        self.retry_events: list[dict[str, Any]] = []
        self.official_ssl_context = official_ssl_context()
        self.cookie_jar = CookieJar()

    def __call__(self, url: str) -> Any:
        if urlparse(url).netloc in {"www.twse.com.tw", "www.tpex.org.tw"}:
            self.tls_strict_verification_relaxed_urls.append(url)
            return self._fetch(url, context=self.official_ssl_context)
        return self._fetch(url)

    def _fetch(self, url: str, context: ssl.SSLContext | None = None) -> Any:
        redirects_remaining = 5
        transient_retries_remaining = 3
        current_url = url
        allowed_hosts = {"www.twse.com.tw", "www.tpex.org.tw"}
        while True:
            try:
                return self._fetch_once(current_url, context=context)
            except HTTPError as exc:
                if exc.code not in {301, 302, 303, 307, 308} or redirects_remaining <= 0:
                    raise
                location = exc.headers.get("Location")
                if not location and urlparse(current_url).netloc in allowed_hosts and transient_retries_remaining > 0:
                    self.retry_events.append({"url": current_url, "reason": f"HTTP {exc.code} without Location"})
                    transient_retries_remaining -= 1
                    time.sleep(self.retry_sleep_seconds)
                    continue
                if not location:
                    raise
                redirected_url = location if location.startswith("http") else f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}{location}"
                if urlparse(redirected_url).netloc not in allowed_hosts:
                    raise SourceContractError(f"Official source redirected outside allowed hosts: {current_url} -> {redirected_url}")
                current_url = redirected_url
                redirects_remaining -= 1
            except SourceContractError as exc:
                if "did not return JSON" in str(exc) and urlparse(current_url).netloc in allowed_hosts and transient_retries_remaining > 0:
                    self.retry_events.append({"url": current_url, "reason": str(exc)})
                    transient_retries_remaining -= 1
                    time.sleep(self.retry_sleep_seconds)
                    continue
                raise

    def _fetch_once(self, url: str, context: ssl.SSLContext | None = None) -> Any:
        request = Request(
            url,
            headers=_official_request_headers(url),
        )
        opener = build_opener(HTTPCookieProcessor(self.cookie_jar), HTTPSHandler(context=context))
        with opener.open(request, timeout=self.timeout_seconds) as response:
            content_type = response.headers.get("content-type", "")
            raw = response.read()
        if "json" not in content_type.lower():
            raise SourceContractError(f"Official source did not return JSON: {url} content-type={content_type}")
        return json.loads(raw.decode("utf-8-sig"))


def prepare_pilot_raw_data(
    *,
    watchlist_path: str | Path,
    output_dir: str | Path,
    start_date: date,
    end_date: date,
    fetch_json: Callable[[str], Any] | None = None,
    request_sleep_seconds: float = 0.5,
) -> dict[str, Any]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    watchlist = read_watchlist(watchlist_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fetcher = fetch_json or OfficialJsonFetcher()
    months = list(month_starts(start_date, end_date))

    listed_rows: list[dict[str, str]] = []
    otc_rows: list[dict[str, str]] = []
    taiex_rows: list[dict[str, str]] = []
    otc_benchmark_rows: list[dict[str, str]] = []
    malformed_rows: list[dict[str, Any]] = []
    optional_change_anomalies: list[dict[str, Any]] = []
    source_urls: dict[str, list[str]] = {
        "twse_stock_day": [],
        "tpex_trading_stock": [],
        "twse_mi_5mins_hist": [],
        "tpex_index_info_inx": [],
    }
    per_symbol_name_source: dict[str, str] = {}

    for entry in watchlist:
        symbol_rows: list[dict[str, str]] = []
        official_name: str | None = None
        for month in months:
            if entry.market_type == "listed":
                url = build_twse_stock_url(entry.stock_id, month)
                source_urls["twse_stock_day"].append(url)
                result = normalize_twse_stock_payload(fetcher(url), entry, start_date, end_date)
            else:
                url = build_tpex_stock_url(entry.stock_id, month)
                source_urls["tpex_trading_stock"].append(url)
                result = normalize_tpex_stock_payload(fetcher(url), entry, start_date, end_date)

            symbol_rows.extend(result.rows)
            malformed_rows.extend(_tag_malformed_rows(result.malformed_rows, entry.stock_id, entry.market_type, url))
            optional_change_anomalies.extend(
                _tag_optional_change_anomalies(result.optional_change_anomalies, entry.stock_id, entry.market_type, url)
            )
            official_name = official_name or result.official_name
            if request_sleep_seconds:
                time.sleep(request_sleep_seconds)

        if symbol_rows:
            per_symbol_name_source[entry.stock_id] = "official" if official_name else "watchlist_fallback"
        if entry.market_type == "listed":
            listed_rows.extend(symbol_rows)
        else:
            otc_rows.extend(symbol_rows)

    for month in months:
        url = build_twse_taiex_url(month)
        source_urls["twse_mi_5mins_hist"].append(url)
        result = normalize_twse_taiex_payload(fetcher(url), start_date, end_date)
        taiex_rows.extend(result.rows)
        malformed_rows.extend(_tag_malformed_rows(result.malformed_rows, None, "benchmark", url))
        if request_sleep_seconds:
            time.sleep(request_sleep_seconds)

        url = build_tpex_index_url(month)
        source_urls["tpex_index_info_inx"].append(url)
        result = normalize_tpex_index_payload(fetcher(url), start_date, end_date)
        otc_benchmark_rows.extend(result.rows)
        malformed_rows.extend(_tag_malformed_rows(result.malformed_rows, None, "benchmark", url))
        if request_sleep_seconds:
            time.sleep(request_sleep_seconds)

    listed_rows = _dedupe_rows(listed_rows, ("Date", "Code"))
    otc_rows = _dedupe_rows(otc_rows, ("Date", "Code"))
    taiex_rows = _dedupe_rows(taiex_rows, ("Date", "BenchmarkSymbol"))
    otc_benchmark_rows = _dedupe_rows(otc_benchmark_rows, ("Date", "BenchmarkSymbol"))

    listed_path = output / "listed_stock_daily.csv"
    otc_path = output / "otc_stock_daily.csv"
    taiex_path = output / "taiex_benchmark.csv"
    otc_benchmark_path = output / "otc_benchmark.csv"
    write_csv(listed_path, STOCK_COLUMNS, sorted(listed_rows, key=lambda row: (row["Date"], row["Code"])))
    write_csv(otc_path, STOCK_COLUMNS, sorted(otc_rows, key=lambda row: (row["Date"], row["Code"])))
    write_csv(taiex_path, BENCHMARK_COLUMNS, sorted(taiex_rows, key=lambda row: row["Date"]))
    write_csv(otc_benchmark_path, BENCHMARK_COLUMNS, sorted(otc_benchmark_rows, key=lambda row: row["Date"]))

    per_symbol_counts = {entry.stock_id: 0 for entry in watchlist}
    per_symbol_latest_dates: dict[str, str | None] = {entry.stock_id: None for entry in watchlist}
    for row in listed_rows + otc_rows:
        per_symbol_counts[row["Code"]] = per_symbol_counts.get(row["Code"], 0) + 1
        current_latest = per_symbol_latest_dates.get(row["Code"])
        if current_latest is None or row["Date"] > current_latest:
            per_symbol_latest_dates[row["Code"]] = row["Date"]
    missing_symbols = [stock_id for stock_id, count in per_symbol_counts.items() if count == 0]
    audit = {
        "scope": "HP-003 one-shot official pilot data preparation helper; not a production downloader",
        "requested_date_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "watchlist": {
            "path": str(watchlist_path),
            "count": len(watchlist),
            "listed_count": sum(1 for entry in watchlist if entry.market_type == "listed"),
            "otc_count": sum(1 for entry in watchlist if entry.market_type == "otc"),
            "reason_optional_policy": "provenance only; not emitted to scanner raw CSV and not used as ranking evidence",
        },
        "market_type_corrections": _market_type_correction_audit(watchlist),
        "source_endpoint_patterns": {
            "twse_stock_day": TWSE_STOCK_DAY_PATTERN,
            "tpex_trading_stock": TPEX_STOCK_PATTERN,
            "twse_mi_5mins_hist": TWSE_TAIEX_PATTERN,
            "tpex_index_info_inx": TPEX_INDEX_PATTERN,
        },
        "source_urls": source_urls,
        "fetched_stock_count": sum(1 for count in per_symbol_counts.values() if count > 0),
        "missing_stock_count": len(missing_symbols),
        "missing_stock_ids": missing_symbols,
        "per_file_row_counts": {
            listed_path.name: len(listed_rows),
            otc_path.name: len(otc_rows),
            taiex_path.name: len(taiex_rows),
            otc_benchmark_path.name: len(otc_benchmark_rows),
        },
        "per_symbol_row_counts": per_symbol_counts,
        "per_symbol_latest_date": per_symbol_latest_dates,
        "latest_date_per_source": {
            "listed_stock_daily": _latest_date(listed_rows),
            "otc_stock_daily": _latest_date(otc_rows),
            "taiex_benchmark": _latest_date(taiex_rows),
            "otc_benchmark": _latest_date(otc_benchmark_rows),
        },
        "skipped_malformed_source_rows": {
            "count": len(malformed_rows),
            "rows": malformed_rows,
        },
        "optional_change_anomalies": {
            "count": len(optional_change_anomalies),
            "samples": optional_change_anomalies[:20],
            "policy": "Non-numeric stock Change tokens are treated as optional anomalies; OHLCV rows are preserved and Change is emitted blank.",
        },
        "name_source": {
            "official_count": sum(1 for value in per_symbol_name_source.values() if value == "official"),
            "watchlist_fallback_count": sum(1 for value in per_symbol_name_source.values() if value == "watchlist_fallback"),
            "by_symbol": per_symbol_name_source,
        },
        "limit_up_availability_note": LIMIT_UP_NOTE,
        "source_limitations": [
            "No trading calendar is inferred; the helper only keeps dates returned by official sources.",
            "TAIEX MI_5MINS_HIST does not expose daily Change; Change is left blank for TAIEX benchmark rows.",
            LIMIT_UP_NOTE,
        ],
    }
    tls_relaxed_urls = getattr(fetcher, "tls_strict_verification_relaxed_urls", [])
    if tls_relaxed_urls:
        audit["tls_strict_verification_relaxed"] = {
            "used": True,
            "url_count": len(tls_relaxed_urls),
            "note": "Python 3.13 strict X.509 verification was relaxed for official TWSE/TPEx HTTPS hosts; certificate verification remained enabled.",
        }
    else:
        audit["tls_strict_verification_relaxed"] = {"used": False}
    retry_events = getattr(fetcher, "retry_events", [])
    audit["official_fetch_retries"] = {
        "count": len(retry_events),
        "events": retry_events,
        "policy": "Only official TWSE/TPEx non-JSON or redirect-without-location transient responses are retried; persistent format changes still stop the helper.",
    }

    audit_path = output / "pilot_data_prep_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def normalize_twse_stock_payload(
    payload: Any,
    entry: WatchlistEntry,
    start_date: date,
    end_date: date,
) -> NormalizeResult:
    fields, data = _twse_payload_fields_and_data(payload, "TWSE STOCK_DAY")
    if fields is None or data is None:
        return NormalizeResult(rows=[])
    _assert_required_fields("TWSE STOCK_DAY", fields, TWSE_STOCK_REQUIRED_FIELDS)
    official_name = _parse_twse_stock_name(payload.get("title"), entry.stock_id)
    name = official_name or entry.stock_name_optional
    rows: list[dict[str, str]] = []
    malformed: list[dict[str, Any]] = []
    optional_change_anomalies: list[dict[str, Any]] = []
    for row_index, raw_row in enumerate(data, start=1):
        try:
            row_date = parse_official_date(_at(raw_row, 0))
            if not _date_in_range(row_date, start_date, end_date):
                continue
            change, anomaly = optional_change_text(_at(raw_row, 7))
            if anomaly is not None:
                optional_change_anomalies.append({"row_index": row_index, "date": row_date.isoformat(), **anomaly})
            rows.append(
                {
                    "Date": row_date.isoformat(),
                    "Code": entry.stock_id,
                    "Name": name,
                    "Open": decimal_text(_at(raw_row, 3)),
                    "High": decimal_text(_at(raw_row, 4)),
                    "Low": decimal_text(_at(raw_row, 5)),
                    "Close": decimal_text(_at(raw_row, 6)),
                    "TradeVolume": integer_text(_at(raw_row, 1)),
                    "TradeValue": integer_text(_at(raw_row, 2)),
                    "Change": change,
                    "Transaction": integer_text(_at(raw_row, 8), allow_blank=True),
                    "IsLimitUp": "",
                }
            )
        except ValueError as exc:
            malformed.append({"row_index": row_index, "reason": str(exc), "raw_row": raw_row})
    return NormalizeResult(
        rows=rows,
        malformed_rows=malformed,
        optional_change_anomalies=optional_change_anomalies,
        official_name=official_name,
    )


def normalize_tpex_stock_payload(
    payload: Any,
    entry: WatchlistEntry,
    start_date: date,
    end_date: date,
) -> NormalizeResult:
    table = _first_tpex_table(payload, "TPEx tradingStock")
    if table is None:
        return NormalizeResult(rows=[])
    _assert_required_fields("TPEx tradingStock", table.get("fields"), TPEX_STOCK_REQUIRED_FIELDS)
    official_name = _clean_text(payload.get("name")) or _parse_tpex_stock_name(table.get("subtitle"), entry.stock_id)
    name = official_name or entry.stock_name_optional
    rows: list[dict[str, str]] = []
    malformed: list[dict[str, Any]] = []
    optional_change_anomalies: list[dict[str, Any]] = []
    for row_index, raw_row in enumerate(table.get("data") or [], start=1):
        try:
            row_date = parse_official_date(_at(raw_row, 0))
            if not _date_in_range(row_date, start_date, end_date):
                continue
            change, anomaly = optional_change_text(_at(raw_row, 7))
            if anomaly is not None:
                optional_change_anomalies.append({"row_index": row_index, "date": row_date.isoformat(), **anomaly})
            rows.append(
                {
                    "Date": row_date.isoformat(),
                    "Code": entry.stock_id,
                    "Name": name,
                    "Open": decimal_text(_at(raw_row, 3)),
                    "High": decimal_text(_at(raw_row, 4)),
                    "Low": decimal_text(_at(raw_row, 5)),
                    "Close": decimal_text(_at(raw_row, 6)),
                    "TradeVolume": integer_text(_at(raw_row, 1), multiplier=1000),
                    "TradeValue": integer_text(_at(raw_row, 2), multiplier=1000),
                    "Change": change,
                    "Transaction": integer_text(_at(raw_row, 8), allow_blank=True),
                    "IsLimitUp": "",
                }
            )
        except ValueError as exc:
            malformed.append({"row_index": row_index, "reason": str(exc), "raw_row": raw_row})
    return NormalizeResult(
        rows=rows,
        malformed_rows=malformed,
        optional_change_anomalies=optional_change_anomalies,
        official_name=official_name,
    )


def normalize_twse_taiex_payload(payload: Any, start_date: date, end_date: date) -> NormalizeResult:
    fields, data = _twse_payload_fields_and_data(payload, "TWSE MI_5MINS_HIST")
    if fields is None or data is None:
        return NormalizeResult(rows=[])
    _assert_required_fields("TWSE MI_5MINS_HIST", fields, TWSE_TAIEX_REQUIRED_FIELDS)
    rows: list[dict[str, str]] = []
    malformed: list[dict[str, Any]] = []
    for row_index, raw_row in enumerate(data, start=1):
        try:
            row_date = parse_official_date(_at(raw_row, 0))
            if not _date_in_range(row_date, start_date, end_date):
                continue
            rows.append(
                {
                    "Date": row_date.isoformat(),
                    "BenchmarkSymbol": "TAIEX",
                    "IndexName": "TAIEX",
                    "Open": decimal_text(_at(raw_row, 1)),
                    "High": decimal_text(_at(raw_row, 2)),
                    "Low": decimal_text(_at(raw_row, 3)),
                    "Close": decimal_text(_at(raw_row, 4)),
                    "Change": "",
                }
            )
        except ValueError as exc:
            malformed.append({"row_index": row_index, "reason": str(exc), "raw_row": raw_row})
    return NormalizeResult(rows=rows, malformed_rows=malformed, official_name="TAIEX")


def normalize_tpex_index_payload(payload: Any, start_date: date, end_date: date) -> NormalizeResult:
    table = _first_tpex_table(payload, "TPEx indexInfo/inx")
    if table is None:
        return NormalizeResult(rows=[])
    _assert_required_fields("TPEx indexInfo/inx", table.get("fields"), TPEX_INDEX_REQUIRED_FIELDS)
    rows: list[dict[str, str]] = []
    malformed: list[dict[str, Any]] = []
    for row_index, raw_row in enumerate(table.get("data") or [], start=1):
        try:
            row_date = parse_official_date(_at(raw_row, 0))
            if not _date_in_range(row_date, start_date, end_date):
                continue
            rows.append(
                {
                    "Date": row_date.isoformat(),
                    "BenchmarkSymbol": "OTC",
                    "IndexName": "OTC",
                    "Open": decimal_text(_at(raw_row, 1)),
                    "High": decimal_text(_at(raw_row, 2)),
                    "Low": decimal_text(_at(raw_row, 3)),
                    "Close": decimal_text(_at(raw_row, 4)),
                    "Change": decimal_text(_at(raw_row, 5), allow_blank=True),
                }
            )
        except ValueError as exc:
            malformed.append({"row_index": row_index, "reason": str(exc), "raw_row": raw_row})
    return NormalizeResult(rows=rows, malformed_rows=malformed, official_name="OTC")


def read_watchlist(path: str | Path) -> list[WatchlistEntry]:
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    entries: list[WatchlistEntry] = []
    for row_number, row in enumerate(rows, start=2):
        stock_id = _clean_text(row.get("stock_id"))
        market_type = (_clean_text(row.get("market_type")) or "").lower()
        if not stock_id or market_type not in {"listed", "otc"}:
            raise ValueError(f"Invalid watchlist row {row_number}: stock_id and market_type listed/otc are required")
        entries.append(
            WatchlistEntry(
                stock_id=stock_id,
                market_type=market_type,
                stock_name_optional=_clean_text(row.get("stock_name_optional")) or "",
                category=_clean_text(row.get("category")) or "",
                reason_optional=_clean_text(row.get("reason_optional")) or "",
            )
        )
    return entries


def build_twse_stock_url(stock_id: str, month: date) -> str:
    return "https://www.twse.com.tw/exchangeReport/STOCK_DAY?" + urlencode(
        {"response": "json", "date": f"{month.year:04d}{month.month:02d}01", "stockNo": stock_id}
    )


def build_tpex_stock_url(stock_id: str, month: date) -> str:
    return "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?" + urlencode(
        {"code": stock_id, "date": f"{month.year:04d}/{month.month:02d}/01", "response": "json"}
    )


def build_twse_taiex_url(month: date) -> str:
    return "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?" + urlencode(
        {"response": "json", "date": f"{month.year:04d}{month.month:02d}01"}
    )


def build_tpex_index_url(month: date) -> str:
    return "https://www.tpex.org.tw/www/zh-tw/indexInfo/inx?" + urlencode(
        {"date": f"{month.year:04d}/{month.month:02d}/01", "response": "json"}
    )


def _official_request_headers(url: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "Mozilla/5.0",
    }
    if urlparse(url).netloc == "www.twse.com.tw":
        headers["Referer"] = "https://www.twse.com.tw/zh/trading/historical/stock-day.html"
    elif urlparse(url).netloc == "www.tpex.org.tw":
        headers["Referer"] = "https://www.tpex.org.tw/zh-tw/mainboard/trading/info/stock-pricing.html"
    return headers


def official_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def month_starts(start_date: date, end_date: date) -> Sequence[date]:
    months: list[date] = []
    current = date(start_date.year, start_date.month, 1)
    last = date(end_date.year, end_date.month, 1)
    while current <= last:
        months.append(current)
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)
    return months


def parse_official_date(value: Any) -> date:
    text = _clean_text(value)
    if not text:
        raise ValueError("missing date")
    parts = [part for part in re.split(r"[/-]", text) if part]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"unsupported date format: {text}")
    year = int(parts[0])
    if year < 1900:
        year += 1911
    return date(year, int(parts[1]), int(parts[2]))


def decimal_text(value: Any, *, allow_blank: bool = False) -> str:
    text = _clean_text(value)
    if _is_blank(text):
        if allow_blank:
            return ""
        raise ValueError("missing numeric value")
    text = text.replace(",", "").replace("+", "").replace(" ", "")
    try:
        decimal_value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value}") from exc
    formatted = format(decimal_value, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


def optional_change_text(value: Any) -> tuple[str, dict[str, Any] | None]:
    try:
        return decimal_text(value, allow_blank=True), None
    except ValueError:
        return "", {"raw_change": value, "reason": "non-numeric optional Change token"}


def integer_text(value: Any, *, multiplier: int = 1, allow_blank: bool = False) -> str:
    text = decimal_text(value, allow_blank=allow_blank)
    if text == "":
        return ""
    decimal_value = Decimal(text) * multiplier
    if decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"expected integer-compatible value: {value}")
    return str(int(decimal_value))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _twse_payload_fields_and_data(payload: Any, source_name: str) -> tuple[list[str] | None, list[Any] | None]:
    if not isinstance(payload, dict):
        raise SourceContractError(f"{source_name} payload is not a JSON object")
    fields = payload.get("fields")
    data = payload.get("data")
    if fields is None or data is None:
        if payload.get("stat") and payload.get("stat") != "OK":
            return None, None
        raise SourceContractError(f"{source_name} payload missing fields/data")
    if not isinstance(data, list):
        raise SourceContractError(f"{source_name} data is not a list")
    return fields, data


def _first_tpex_table(payload: Any, source_name: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        raise SourceContractError(f"{source_name} payload is not a JSON object")
    tables = payload.get("tables")
    if not isinstance(tables, list) or not tables:
        if payload.get("stat") and str(payload.get("stat")).lower() != "ok":
            return None
        raise SourceContractError(f"{source_name} payload missing tables")
    table = tables[0]
    if not isinstance(table, dict):
        raise SourceContractError(f"{source_name} first table is not an object")
    data = table.get("data")
    if data is None:
        raise SourceContractError(f"{source_name} table missing data")
    if not isinstance(data, list):
        raise SourceContractError(f"{source_name} table data is not a list")
    return table


def _assert_required_fields(source_name: str, observed: Any, required: Sequence[str]) -> None:
    if not isinstance(observed, list):
        raise SourceContractError(f"{source_name} fields is not a list")
    observed_normalized = [_normalize_header(field) for field in observed]
    required_normalized = [_normalize_header(field) for field in required]
    if observed_normalized[: len(required_normalized)] != required_normalized:
        raise SourceContractError(
            f"{source_name} field contract changed: observed={observed!r} required_prefix={list(required)!r}"
        )


def _at(row: Any, index: int) -> Any:
    if not isinstance(row, list) or len(row) <= index:
        raise ValueError(f"source row has fewer than {index + 1} columns")
    return row[index]


def _date_in_range(value: date, start_date: date, end_date: date) -> bool:
    return start_date <= value <= end_date


def _parse_twse_stock_name(title: Any, stock_id: str) -> str | None:
    text = _clean_text(title)
    if not text:
        return None
    match = re.search(rf"\b{re.escape(stock_id)}\s+(.+?)\s+各日成交資訊", text)
    return _clean_text(match.group(1)) if match else None


def _parse_tpex_stock_name(subtitle: Any, stock_id: str) -> str | None:
    text = _clean_text(subtitle)
    if not text:
        return None
    match = re.search(rf"\b{re.escape(stock_id)}\s+(.+?)\s+\d{{3}}年\d{{2}}月", text)
    return _clean_text(match.group(1)) if match else None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() in {"", "-", "--", "---", "N/A", "NA"}


def _normalize_header(value: Any) -> str:
    text = re.sub(r"<[^>]*>", "", str(value))
    return re.sub(r"\s+", "", text).strip()


def _tag_malformed_rows(rows: list[dict[str, Any]], stock_id: str | None, market_type: str, source_url: str) -> list[dict[str, Any]]:
    return [
        {
            "stock_id": stock_id,
            "market_type": market_type,
            "source_url": source_url,
            **row,
        }
        for row in rows
    ]


def _tag_optional_change_anomalies(
    rows: list[dict[str, Any]],
    stock_id: str,
    market_type: str,
    source_url: str,
) -> list[dict[str, Any]]:
    return [
        {
            "stock_id": stock_id,
            "market_type": market_type,
            "source_url": source_url,
            **row,
        }
        for row in rows
    ]


def _market_type_correction_audit(watchlist: Sequence[WatchlistEntry]) -> list[dict[str, str | None]]:
    watchlist_by_id = {entry.stock_id: entry for entry in watchlist}
    rows: list[dict[str, str | None]] = []
    for stock_id, correction in OFFICIAL_MARKET_TYPE_CORRECTIONS.items():
        entry = watchlist_by_id.get(stock_id)
        actual_market_type = entry.market_type if entry else None
        if entry is None:
            status = "not_in_watchlist"
        elif entry.market_type == correction["to"]:
            status = "applied"
        elif entry.market_type == correction["from"]:
            status = "not_applied"
        else:
            status = "unexpected_market_type"
        rows.append(
            {
                "stock_id": stock_id,
                "from": correction["from"],
                "to": correction["to"],
                "actual_market_type": actual_market_type,
                "reason": correction["reason"],
                "status": status,
            }
        )
    return rows


def _dedupe_rows(rows: list[dict[str, str]], keys: tuple[str, ...]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = tuple(row[field] for field in keys)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _latest_date(rows: list[dict[str, str]]) -> str | None:
    return max((row["Date"] for row in rows), default=None)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-shot HP-003 official pilot helper that prepares local aggregate raw CSV files "
            "for the market scanner. This is not a production downloader."
        )
    )
    parser.add_argument(
        "--watchlist",
        default="data/raw_market/manual_pilot_universe/watchlist_universe.csv",
        help="Watchlist CSV with stock_id and market_type columns.",
    )
    parser.add_argument("--output-dir", required=True, help="Ignored output folder for four aggregate raw CSV files.")
    parser.add_argument("--start-date", required=True, help="Inclusive YYYY-MM-DD start date.")
    parser.add_argument("--end-date", required=True, help="Inclusive YYYY-MM-DD end date.")
    parser.add_argument(
        "--request-sleep-seconds",
        type=float,
        default=0.5,
        help="Small pause between official requests. Default: 0.5.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        audit = prepare_pilot_raw_data(
            watchlist_path=args.watchlist,
            output_dir=args.output_dir,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
            request_sleep_seconds=args.request_sleep_seconds,
        )
    except SourceContractError as exc:
        print(f"Source contract changed; stopped without hard parsing: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
