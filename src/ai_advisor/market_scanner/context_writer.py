from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from ai_advisor.market_scanner.schemas import (
    BenchmarkRegimeSnapshot,
    ContextWriteResult,
    DailyStockRecord,
    ScannerBenchmarkSymbol,
    ScannerMarketType,
    SkippedContextCandidate,
    StockIndicatorSnapshot,
)
from ai_advisor.schemas import StockAdviceContext


VALID_CONTEXT_RISK_STATES = {"risk_on", "neutral", "risk_off"}
MARKET_BENCHMARKS: dict[ScannerMarketType, ScannerBenchmarkSymbol] = {
    "listed": "TAIEX",
    "otc": "OTC",
}


def build_stock_advice_context_data(
    stock_records: Sequence[DailyStockRecord],
    indicators: StockIndicatorSnapshot,
    regime: BenchmarkRegimeSnapshot,
) -> ContextWriteResult:
    records = sorted(stock_records, key=lambda record: record.date)
    if not records:
        return _skip(None, None, "no stock records", [])

    latest = records[-1]
    warnings: list[str] = []
    benchmark_symbol = MARKET_BENCHMARKS[latest.market_type]

    if indicators.stock_id not in {None, latest.stock_id}:
        return _skip(latest.stock_id, latest.date, "indicator stock_id mismatch", [f"indicator stock_id={indicators.stock_id}"])
    if indicators.market_type not in {None, latest.market_type}:
        return _skip(latest.stock_id, latest.date, "indicator market_type mismatch", [f"indicator market_type={indicators.market_type}"])
    if indicators.as_of_date != latest.date:
        return _skip(
            latest.stock_id,
            latest.date,
            "indicator as_of_date mismatch",
            [f"latest stock date={latest.date}", f"indicator as_of_date={indicators.as_of_date}"],
        )
    if regime.benchmark_symbol != benchmark_symbol:
        return _skip(
            latest.stock_id,
            latest.date,
            "benchmark regime does not match market_type",
            [f"market_type={latest.market_type}", f"expected benchmark_symbol={benchmark_symbol}", f"actual benchmark_symbol={regime.benchmark_symbol}"],
        )
    if regime.as_of_date != latest.date:
        return _skip(
            latest.stock_id,
            latest.date,
            "benchmark regime as_of_date mismatch",
            [f"latest stock date={latest.date}", f"benchmark regime as_of_date={regime.as_of_date}"],
        )
    if regime.risk_state not in VALID_CONTEXT_RISK_STATES:
        return _skip(
            latest.stock_id,
            latest.date,
            "benchmark regime unavailable for context schema",
            ["scanner-only risk_state=unknown must not be written to StockAdviceContext"],
        )

    change_pct = _daily_change_pct(records)
    if change_pct is None:
        return _skip(latest.stock_id, latest.date, "daily change_pct unavailable", ["need prior close or valid source change"])

    if indicators.volume_ratio_20d is None:
        return _skip(latest.stock_id, latest.date, "volume_ratio_20d unavailable", list(indicators.warnings))

    risk_geometry = _derive_structural_risk(latest, indicators)
    if risk_geometry is None:
        return _skip(
            latest.stock_id,
            latest.date,
            "structural risk geometry unavailable",
            [
                "M3 does not synthesize close + 2R targets",
                "needs structural support below close and structural target above close",
            ],
        )

    if indicators.warnings:
        warnings.extend(indicators.warnings)
    data_quality_warnings = [
        "sector/theme data unavailable; market_scan fallback used",
        "technical classifier not implemented in M3; technical.position set to unknown",
    ]
    if latest.is_limit_up is None:
        data_quality_warnings.append("official limit-up flag unavailable; technical.is_limit_up set to false")

    data_source_notes = [
        "theme.rank/theme.score are neutral market_scan fallback values, not real sector strength",
        "leader_status.leader_rank is unknown because M3 has no scanner universe ranking",
        "risk fields are derived from structural OHLCV levels only; no close + 2R target was synthesized",
    ]

    context_data = {
        "date": latest.date,
        "market_type": latest.market_type,
        "benchmark_symbol": benchmark_symbol,
        "stock": {
            "stock_id": latest.stock_id,
            "name": latest.name,
            "close": latest.close,
            "change_pct": change_pct,
            "volume_ratio_20d": indicators.volume_ratio_20d,
        },
        "market_regime": {"risk_state": regime.risk_state},
        "theme": {"name": "market_scan", "rank": 999, "score": 50, "lifecycle": "unknown"},
        "leader_status": {"leader_rank": "unknown"},
        "technical": {
            "position": "unknown",
            "is_overheated": _is_overheated(indicators),
            "is_limit_up": bool(latest.is_limit_up) if latest.is_limit_up is not None else False,
        },
        "risk": risk_geometry,
        "scanner_metadata": {
            "ma5": indicators.ma5,
            "ma10": indicators.ma10,
            "ma20": indicators.ma20,
            "ma60": indicators.ma60,
            "average_volume_20d": indicators.average_volume_20d,
            "prior_20d_high": indicators.prior_20d_high,
            "prior_20d_low": indicators.prior_20d_low,
            "prior_60d_high": indicators.prior_60d_high,
            "prior_60d_low": indicators.prior_60d_low,
            "distance_from_ma20": indicators.distance_from_ma20,
            "relative_strength_20d_vs_benchmark": indicators.relative_strength_20d_vs_benchmark,
            "relative_strength_60d_vs_benchmark": indicators.relative_strength_60d_vs_benchmark,
            "benchmark_ma20": regime.ma20,
            "benchmark_ma60": regime.ma60,
        },
        "data_source_notes": data_source_notes,
        "data_quality_warnings": data_quality_warnings,
    }
    context = StockAdviceContext.model_validate(context_data)
    missing_fields = context.missing_required_fields()
    if missing_fields:
        return _skip(latest.stock_id, latest.date, "context schema required fields missing", missing_fields)

    return ContextWriteResult(was_written=False, context_data=context.model_dump(mode="json"), warnings=warnings)


def write_stock_advice_context_json(
    stock_records: Sequence[DailyStockRecord],
    indicators: StockIndicatorSnapshot,
    regime: BenchmarkRegimeSnapshot,
    output_dir: str | Path,
) -> ContextWriteResult:
    result = build_stock_advice_context_data(stock_records, indicators, regime)
    if result.context_data is None:
        return result

    output_path = Path(output_dir) / deterministic_context_filename(result.context_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result.context_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(serialized, encoding="utf-8")
    return result.model_copy(update={"was_written": True, "context_path": str(output_path)})


def deterministic_context_filename(context_data: dict) -> str:
    date_text = _safe_filename_part(str(context_data["date"]))
    stock_id = _safe_filename_part(str(context_data["stock"]["stock_id"]))
    market_type = _safe_filename_part(str(context_data["market_type"]))
    return f"{date_text}_{market_type}_{stock_id}.json"


def _derive_structural_risk(latest: DailyStockRecord, indicators: StockIndicatorSnapshot) -> dict[str, float] | None:
    close = latest.close
    support_candidates = [
        indicators.ma10,
        indicators.ma20,
        indicators.prior_20d_low,
        indicators.prior_60d_low,
    ]
    target_candidates = [
        indicators.prior_20d_high,
        indicators.prior_60d_high,
    ]
    supports_below_close = [value for value in support_candidates if value is not None and 0 < value < close]
    targets_above_close = [value for value in target_candidates if value is not None and value > close]
    if not supports_below_close or not targets_above_close:
        return None

    nearest_support = max(supports_below_close)
    invalid_level = nearest_support * 0.98
    planned_target = min(targets_above_close)
    risk_per_share = close - invalid_level
    reward_per_share = planned_target - close
    if invalid_level <= 0 or invalid_level >= close or reward_per_share <= 0 or risk_per_share <= 0:
        return None

    return {
        "nearest_support": nearest_support,
        "invalid_level": invalid_level,
        "planned_target": planned_target,
        "risk_reward_ratio": reward_per_share / risk_per_share,
    }


def _daily_change_pct(records: Sequence[DailyStockRecord]) -> float | None:
    latest = records[-1]
    if len(records) >= 2:
        previous_close = records[-2].close
    elif latest.change is not None:
        previous_close = latest.close - latest.change
    else:
        return None

    if previous_close <= 0:
        return None
    return (latest.close - previous_close) / previous_close * 100


def _is_overheated(indicators: StockIndicatorSnapshot) -> bool:
    return indicators.distance_from_ma20 is not None and indicators.distance_from_ma20 >= 12


def _skip(stock_id: str | None, date: str | None, reason: str, details: list[str]) -> ContextWriteResult:
    return ContextWriteResult(
        was_written=False,
        skipped_candidate=SkippedContextCandidate(stock_id=stock_id, date=date, reason=reason, details=details),
    )


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "unknown"
