from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ALPHA_PLACEHOLDER_FIELDS = [
    "stock_return_5d_pct",
    "benchmark_return_5d_pct",
    "alpha_5d_pct",
    "alpha_hit_5d",
    "was_useful",
    "human_feedback",
]

REQUIRED_RAW_FILES = [
    "listed_stock_daily.csv",
    "otc_stock_daily.csv",
    "taiex_benchmark.csv",
    "otc_benchmark.csv",
    "pilot_data_prep_audit.json",
]

WATCHLIST_COLUMNS = [
    "stock_id",
    "market_type",
    "stock_name_optional",
    "category",
    "reason_optional",
]

FOLLOWUP_COLUMNS = [
    "stock_id",
    "advice_date",
    "input_context_hash",
    "close_5d",
    "benchmark_return_5d_pct",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build first real advice pilot watchlist and follow-up CSV from immutable advice log and local raw CSV."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight")
    add_advice_args(preflight)
    preflight.set_defaults(func=run_preflight)

    watchlist = subparsers.add_parser("write-watchlist")
    add_advice_args(watchlist)
    watchlist.add_argument("--output", required=True)
    watchlist.set_defaults(func=run_write_watchlist)

    followup = subparsers.add_parser("build-followup")
    add_advice_args(followup)
    followup.add_argument("--raw-dir", required=True)
    followup.add_argument("--output", required=True)
    followup.add_argument("--followup-date", default="2026-06-02")
    followup.set_defaults(func=run_build_followup)

    args = parser.parse_args()
    args.func(args)


def add_advice_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--advice-log", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--advice-date", default="2026-05-26")
    parser.add_argument("--expected-line-count", type=int, default=26)
    parser.add_argument("--expected-unique-key-count", type=int, default=26)
    parser.add_argument("--expected-actionable-count", type=int, default=17)
    parser.add_argument("--expected-blocked-count", type=int, default=0)
    parser.add_argument("--expected-listed-taiex-count", type=int, default=15)
    parser.add_argument("--expected-otc-otc-count", type=int, default=11)


def run_preflight(args: argparse.Namespace) -> None:
    entries, summary = load_and_validate_advice(args)
    summary["stock_rows"] = stock_rows_for_report(entries)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def run_write_watchlist(args: argparse.Namespace) -> None:
    entries, summary = load_and_validate_advice(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WATCHLIST_COLUMNS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "stock_id": str(entry["stock_id"]),
                    "market_type": str(entry["market_type"]),
                    "stock_name_optional": str(entry.get("stock_name") or ""),
                    "category": "first_real_advice_pilot",
                    "reason_optional": "active_advice_log_2026-05-26",
                }
            )

    print(
        json.dumps(
            {
                "watchlist_path": str(output),
                "row_count": len(entries),
                "advice_log_summary": summary,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def run_build_followup(args: argparse.Namespace) -> None:
    entries, advice_summary = load_and_validate_advice(args)
    raw_dir = Path(args.raw_dir)
    raw_summary = validate_raw_files(raw_dir, entries, args.advice_date, args.followup_date)

    stock_close_by_market = {
        "listed": load_stock_close_map(raw_dir / "listed_stock_daily.csv"),
        "otc": load_stock_close_map(raw_dir / "otc_stock_daily.csv"),
    }
    benchmark_close = {}
    benchmark_close.update(load_benchmark_close_map(raw_dir / "taiex_benchmark.csv"))
    benchmark_close.update(load_benchmark_close_map(raw_dir / "otc_benchmark.csv"))

    benchmark_returns = {}
    for symbol in ["TAIEX", "OTC"]:
        start_close = benchmark_close.get((symbol, args.advice_date))
        end_close = benchmark_close.get((symbol, args.followup_date))
        if start_close is None or end_close is None:
            raise SystemExit(f"missing benchmark close for {symbol} on advice or follow-up date")
        benchmark_returns[symbol] = (end_close - start_close) / start_close * Decimal("100")

    rows: list[dict[str, str]] = []
    actionable_missing: list[dict[str, str]] = []
    for entry in entries:
        stock_id = str(entry["stock_id"])
        market_type = str(entry["market_type"])
        benchmark_symbol = benchmark_for_market(market_type)
        close_5d = stock_close_by_market[market_type].get((stock_id, args.followup_date))
        benchmark_return = benchmark_returns[benchmark_symbol]
        if close_5d is None:
            if is_actionable(entry):
                actionable_missing.append(
                    {
                        "stock_id": stock_id,
                        "reason": f"missing close_5d for {args.followup_date}",
                    }
                )
            raise SystemExit(f"missing follow-up close for {stock_id} on {args.followup_date}")

        rows.append(
            {
                "stock_id": stock_id,
                "advice_date": str(entry["advice_date"]),
                "input_context_hash": str(entry.get("input_context_hash") or ""),
                "close_5d": decimal_to_csv(close_5d),
                "benchmark_return_5d_pct": decimal_to_csv(benchmark_return),
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FOLLOWUP_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    actionable_count = sum(1 for entry in entries if is_actionable(entry))
    actionable_complete_count = actionable_count - len(actionable_missing)
    print(
        json.dumps(
            {
                "followup_csv_path": str(output),
                "row_count": len(rows),
                "actionable_count": actionable_count,
                "actionable_complete_count": actionable_complete_count,
                "actionable_missing": actionable_missing,
                "benchmark_return_5d_pct": {
                    symbol: decimal_to_csv(value) for symbol, value in benchmark_returns.items()
                },
                "advice_log_summary": advice_summary,
                "raw_summary": raw_summary,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def load_and_validate_advice(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    advice_log = Path(args.advice_log)
    entries = read_jsonl(advice_log)
    digest = sha256_file(advice_log)

    keys = {
        (str(entry.get("stock_id")), str(entry.get("advice_date")), str(entry.get("input_context_hash")))
        for entry in entries
    }
    market_distribution = Counter(
        (str(entry.get("market_type")), str(entry.get("benchmark_symbol"))) for entry in entries
    )
    non_null_alpha = [
        {"stock_id": entry.get("stock_id"), "field": field}
        for entry in entries
        for field in ALPHA_PLACEHOLDER_FIELDS
        if entry.get(field) is not None
    ]
    actionable_count = sum(1 for entry in entries if is_actionable(entry))
    blocked_count = sum(1 for entry in entries if entry.get("was_blocked") is True)

    failures = []
    if digest != args.expected_sha256.lower():
        failures.append(f"sha256 mismatch: {digest}")
    if len(entries) != args.expected_line_count:
        failures.append(f"line_count mismatch: {len(entries)}")
    if len(keys) != args.expected_unique_key_count:
        failures.append(f"unique_key_count mismatch: {len(keys)}")
    if actionable_count != args.expected_actionable_count:
        failures.append(f"actionable_count mismatch: {actionable_count}")
    if blocked_count != args.expected_blocked_count:
        failures.append(f"blocked_count mismatch: {blocked_count}")
    if non_null_alpha:
        failures.append(f"alpha placeholder fields are non-null: {non_null_alpha}")
    if market_distribution[("listed", "TAIEX")] != args.expected_listed_taiex_count:
        failures.append(f"listed/TAIEX count mismatch: {market_distribution[('listed', 'TAIEX')]}")
    if market_distribution[("otc", "OTC")] != args.expected_otc_otc_count:
        failures.append(f"otc/OTC count mismatch: {market_distribution[('otc', 'OTC')]}")

    wrong_date = sorted({str(entry.get("advice_date")) for entry in entries if entry.get("advice_date") != args.advice_date})
    if wrong_date:
        failures.append(f"unexpected advice_date values: {wrong_date}")

    if failures:
        raise SystemExit("advice log preflight failed: " + "; ".join(failures))

    summary = {
        "advice_log_path": str(advice_log),
        "sha256": digest,
        "line_count": len(entries),
        "unique_key_count": len(keys),
        "actionable_count": actionable_count,
        "blocked_count": blocked_count,
        "non_null_alpha_placeholder_count": len(non_null_alpha),
        "market_distribution": {
            f"{market_type}/{benchmark_symbol}": count
            for (market_type, benchmark_symbol), count in sorted(market_distribution.items())
        },
    }
    return entries, summary


def validate_raw_files(
    raw_dir: Path,
    entries: list[dict[str, Any]],
    advice_date: str,
    followup_date: str,
) -> dict[str, Any]:
    missing_files = [filename for filename in REQUIRED_RAW_FILES if not (raw_dir / filename).exists()]
    if missing_files:
        raise SystemExit(f"missing raw output files: {missing_files}")

    listed = load_stock_close_map(raw_dir / "listed_stock_daily.csv")
    otc = load_stock_close_map(raw_dir / "otc_stock_daily.csv")
    benchmark = {}
    benchmark.update(load_benchmark_close_map(raw_dir / "taiex_benchmark.csv"))
    benchmark.update(load_benchmark_close_map(raw_dir / "otc_benchmark.csv"))

    missing_stock_closes = []
    for entry in entries:
        stock_id = str(entry["stock_id"])
        market_type = str(entry["market_type"])
        close_map = listed if market_type == "listed" else otc if market_type == "otc" else None
        if close_map is None:
            raise SystemExit(f"unsupported market_type in advice log: {market_type}")
        if (stock_id, advice_date) not in close_map:
            missing_stock_closes.append({"stock_id": stock_id, "date": advice_date})
        if (stock_id, followup_date) not in close_map:
            missing_stock_closes.append({"stock_id": stock_id, "date": followup_date})

    missing_benchmark_closes = []
    for symbol in ["TAIEX", "OTC"]:
        for target_date in [advice_date, followup_date]:
            if (symbol, target_date) not in benchmark:
                missing_benchmark_closes.append({"benchmark_symbol": symbol, "date": target_date})

    if missing_stock_closes or missing_benchmark_closes:
        raise SystemExit(
            "raw validation failed: "
            + json.dumps(
                {
                    "missing_stock_closes": missing_stock_closes,
                    "missing_benchmark_closes": missing_benchmark_closes,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    stock_followup_close_count = sum(
        1
        for entry in entries
        if (
            str(entry["stock_id"]),
            followup_date,
        )
        in (listed if entry["market_type"] == "listed" else otc)
    )

    return {
        "raw_dir": str(raw_dir),
        "required_files_present": REQUIRED_RAW_FILES,
        "advice_date": advice_date,
        "followup_date": followup_date,
        "stock_followup_close_count": stock_followup_close_count,
        "benchmark_dates_present": {
            symbol: [advice_date, followup_date] for symbol in ["TAIEX", "OTC"]
        },
    }


def load_stock_close_map(path: Path) -> dict[tuple[str, str], Decimal]:
    closes: dict[tuple[str, str], Decimal] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = str(row.get("Code") or "").strip()
            row_date = str(row.get("Date") or "").strip()
            close = parse_decimal(row.get("Close"))
            if code and row_date and close is not None:
                closes[(code, row_date)] = close
    return closes


def load_benchmark_close_map(path: Path) -> dict[tuple[str, str], Decimal]:
    closes: dict[tuple[str, str], Decimal] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = str(row.get("BenchmarkSymbol") or "").strip()
            row_date = str(row.get("Date") or "").strip()
            close = parse_decimal(row.get("Close"))
            if symbol and row_date and close is not None:
                closes[(symbol, row_date)] = close
    return closes


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    entries = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSONL at line {line_number}: {exc}") from exc
    return entries


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_actionable(entry: dict[str, Any]) -> bool:
    return (
        entry.get("final_grade") in {"A", "B"}
        and entry.get("final_recommendation") in {"wait_pullback", "small_probe"}
        and entry.get("was_blocked") is False
    )


def benchmark_for_market(market_type: str) -> str:
    if market_type == "listed":
        return "TAIEX"
    if market_type == "otc":
        return "OTC"
    raise SystemExit(f"unsupported market_type for benchmark mapping: {market_type}")


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "N/A", "null", "None"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise SystemExit(f"invalid decimal value: {value!r}") from exc


def decimal_to_csv(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.0000000001"))
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def stock_rows_for_report(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "stock_id": str(entry.get("stock_id") or ""),
            "stock_name": str(entry.get("stock_name") or ""),
            "market_type": str(entry.get("market_type") or ""),
            "benchmark_symbol": str(entry.get("benchmark_symbol") or ""),
        }
        for entry in entries
    ]


if __name__ == "__main__":
    main()
