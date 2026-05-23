from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_advisor.config import DEFAULT_CONFIG, ensure_output_dir
from ai_advisor.schemas import AdviceLogEntry, AlphaSummary, EvaluationLogEntry


REQUIRED_FOLLOWUP_COLUMNS = {"stock_id", "advice_date", "close_5d", "benchmark_return_5d_pct"}


def update_followup_returns(
    advice_log_path: str,
    followup_csv_path: str,
    evaluation_log_path: str = DEFAULT_CONFIG.evaluation_log_path,
) -> AlphaSummary:
    advice_entries = _read_advice_log(advice_log_path)
    followup_rows = _read_followup_csv(followup_csv_path)
    existing_evaluation_keys = _read_existing_evaluation_keys(evaluation_log_path)

    warnings: list[str] = []
    entries_by_stock_date: dict[tuple[str, str], list[AdviceLogEntry]] = defaultdict(list)
    entries_by_full_key: dict[tuple[str, str, str], list[AdviceLogEntry]] = defaultdict(list)
    for entry in advice_entries:
        if entry.stock_id is None or entry.advice_date is None:
            continue
        stock_date_key = (entry.stock_id, entry.advice_date)
        entries_by_stock_date[stock_date_key].append(entry)
        if entry.input_context_hash:
            entries_by_full_key[(entry.stock_id, entry.advice_date, entry.input_context_hash)].append(entry)

    records: list[EvaluationLogEntry] = []
    for row_index, row in enumerate(followup_rows, start=2):
        stock_id = str(row.get("stock_id", "")).strip()
        advice_date = str(row.get("advice_date", "")).strip()
        input_context_hash = str(row.get("input_context_hash", "")).strip()

        if not stock_id or not advice_date:
            warnings.append(f"follow-up row {row_index} missing stock_id or advice_date; skipped")
            continue

        if input_context_hash:
            matches = entries_by_full_key.get((stock_id, advice_date, input_context_hash), [])
        else:
            matches = entries_by_stock_date.get((stock_id, advice_date), [])

        if not matches:
            warnings.append(f"follow-up row {row_index} did not match an advice snapshot for {stock_id} {advice_date}")
            continue

        if not input_context_hash and len(matches) > 1:
            warnings.append(
                f"follow-up row {row_index} matched {len(matches)} advice snapshots for {stock_id} {advice_date}; "
                "appended one evaluation per snapshot"
            )

        for entry in matches:
            record = _build_evaluation_record(entry, row, followup_csv_path)
            key = (record.stock_id, record.advice_date, record.input_context_hash)
            if key in existing_evaluation_keys:
                warnings.append(
                    f"superseding evaluation appended for {record.stock_id} {record.advice_date} "
                    f"{record.input_context_hash}; consumers should use the latest valid record"
                )
            if record.exclusion_reason == "missing benchmark_return_5d_pct":
                warnings.append(
                    f"{record.stock_id} {record.advice_date} excluded from alpha denominator: "
                    "missing benchmark_return_5d_pct"
                )
            records.append(record)
            existing_evaluation_keys.add(key)

    _append_evaluation_records(records, evaluation_log_path)

    included_records = [record for record in records if record.included_in_alpha_denominator]
    alpha_values = [record.alpha_5d_pct for record in included_records if record.alpha_5d_pct is not None]
    alpha_hit_count = sum(1 for record in included_records if record.alpha_hit_5d is True)
    complete_followup_count = len(included_records)

    return AlphaSummary(
        advice_log_path=advice_log_path,
        followup_csv_path=followup_csv_path,
        evaluation_log_path=evaluation_log_path,
        advice_snapshot_count=len(advice_entries),
        followup_row_count=len(followup_rows),
        matched_advice_count=len(records),
        appended_evaluation_count=len(records),
        actionable_candidate_count=sum(1 for entry in advice_entries if _is_actionable(entry)),
        complete_followup_count=complete_followup_count,
        alpha_hit_count=alpha_hit_count,
        alpha_hit_rate_5d_vs_market=(
            alpha_hit_count / complete_followup_count if complete_followup_count else None
        ),
        average_alpha_5d_pct=(sum(alpha_values) / len(alpha_values) if alpha_values else None),
        warnings=_dedupe(warnings),
        records=records,
    )


def _read_advice_log(advice_log_path: str) -> list[AdviceLogEntry]:
    path = Path(advice_log_path)
    if not path.exists():
        return []

    entries: list[AdviceLogEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(AdviceLogEntry.model_validate(json.loads(line)))
    return entries


def _read_followup_csv(followup_csv_path: str) -> list[dict[str, str]]:
    path = Path(followup_csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_FOLLOWUP_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"follow-up CSV missing required columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def _read_existing_evaluation_keys(evaluation_log_path: str) -> set[tuple[str | None, str | None, str | None]]:
    path = Path(evaluation_log_path)
    if not path.exists():
        return set()

    keys: set[tuple[str | None, str | None, str | None]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys.add((data.get("stock_id"), data.get("advice_date"), data.get("input_context_hash")))
    return keys


def _build_evaluation_record(
    advice_entry: AdviceLogEntry,
    followup_row: dict[str, Any],
    followup_csv_path: str,
) -> EvaluationLogEntry:
    close_5d = _optional_float(followup_row.get("close_5d"))
    benchmark_return = _optional_float(followup_row.get("benchmark_return_5d_pct"))
    stock_return = _stock_return_5d_pct(advice_entry.advice_close, close_5d)
    alpha = stock_return - benchmark_return if stock_return is not None and benchmark_return is not None else None
    exclusion_reason = _exclusion_reason(advice_entry, close_5d, benchmark_return, stock_return)
    included = exclusion_reason is None

    return EvaluationLogEntry(
        timestamp=datetime.now(UTC).isoformat(),
        advice_date=advice_entry.advice_date,
        stock_id=advice_entry.stock_id,
        input_context_hash=advice_entry.input_context_hash,
        advice_close=advice_entry.advice_close,
        close_5d=close_5d,
        benchmark_return_5d_pct=benchmark_return,
        stock_return_5d_pct=stock_return,
        alpha_5d_pct=alpha,
        alpha_hit_5d=alpha > 0 if alpha is not None else None,
        included_in_alpha_denominator=included,
        exclusion_reason=exclusion_reason,
        source_followup_csv=followup_csv_path,
    )


def _append_evaluation_records(records: list[EvaluationLogEntry], evaluation_log_path: str) -> None:
    if not records:
        return

    ensure_output_dir(evaluation_log_path)
    with Path(evaluation_log_path).open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False, separators=(",", ":")) + "\n")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return float(value)


def _stock_return_5d_pct(advice_close: float | None, close_5d: float | None) -> float | None:
    if advice_close is None or close_5d is None or advice_close == 0:
        return None
    return (close_5d - advice_close) / advice_close * 100


def _exclusion_reason(
    advice_entry: AdviceLogEntry,
    close_5d: float | None,
    benchmark_return: float | None,
    stock_return: float | None,
) -> str | None:
    if not _is_actionable(advice_entry):
        return "not actionable candidate"
    if close_5d is None:
        return "missing close_5d"
    if advice_entry.advice_close is None or advice_entry.advice_close == 0:
        return "missing or invalid advice_close"
    if stock_return is None:
        return "stock_return_5d_pct unavailable"
    if benchmark_return is None:
        return "missing benchmark_return_5d_pct"
    return None


def _is_actionable(advice_entry: AdviceLogEntry) -> bool:
    return (
        advice_entry.final_grade in {"A", "B"}
        and advice_entry.final_recommendation in {"wait_pullback", "small_probe"}
        and advice_entry.was_blocked is False
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
