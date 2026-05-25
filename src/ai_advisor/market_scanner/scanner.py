from __future__ import annotations

import copy
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from ai_advisor.market_scanner.context_writer import build_stock_advice_context_data, deterministic_context_filename
from ai_advisor.market_scanner.indicators import calculate_stock_indicators, classify_benchmark_regime
from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    DailyStockRecord,
    ScannerBenchmarkSymbol,
    ScannerConfig,
    ScannerPassCandidate,
    ScannerRunResult,
    ScannerRunSummary,
    ScannerTechnicalPosition,
    SkippedScannerCandidate,
    StockIndicatorSnapshot,
)


MARKET_BENCHMARKS = {"listed": "TAIEX", "otc": "OTC"}
TECHNICAL_POSITION_PREFERENCE: dict[ScannerTechnicalPosition, int] = {
    "pullback_to_ma10_and_rebound": 0,
    "pullback_to_ma5": 1,
    "near_ma20_support": 2,
    "breakout": 3,
    "range_bound": 4,
    "extended_above_ma": 5,
    "unknown": 6,
    "breakdown": 7,
}


def scan_market_candidates(
    stock_universe: Sequence[Sequence[DailyStockRecord]],
    benchmark_records_by_symbol: Mapping[ScannerBenchmarkSymbol, Sequence[BenchmarkDailyRecord]],
    config: ScannerConfig | None = None,
    output_dir: str | Path | None = None,
) -> ScannerRunResult:
    scanner_config = config or ScannerConfig()
    pass_candidates: list[ScannerPassCandidate] = []
    skipped_candidates: list[SkippedScannerCandidate] = []

    for stock_records in stock_universe:
        candidate = evaluate_stock_candidate(stock_records, benchmark_records_by_symbol, scanner_config)
        if isinstance(candidate, SkippedScannerCandidate):
            skipped_candidates.append(candidate)
        else:
            pass_candidates.append(candidate)

    ranked_candidates = rank_scanner_candidates(pass_candidates)
    truncated_candidates = ranked_candidates[: scanner_config.max_output]
    final_candidates = _assign_rank_and_score(truncated_candidates)
    if output_dir is not None:
        final_candidates = [_write_candidate_context(candidate, output_dir) for candidate in final_candidates]

    warnings: list[str] = []
    if len(ranked_candidates) > scanner_config.max_output:
        warnings.append(
            f"max_output applied: kept {scanner_config.max_output} of {len(ranked_candidates)} pass candidates"
        )
    if len(final_candidates) < scanner_config.min_output_warning_threshold:
        warnings.append(
            f"fewer than {scanner_config.min_output_warning_threshold} contexts generated: {len(final_candidates)}"
        )

    penalty_counter: Counter[str] = Counter()
    for candidate in final_candidates:
        penalty_counter.update(candidate.penalties)

    summary = ScannerRunSummary(
        input_candidate_count=len(stock_universe),
        output_context_count=len(final_candidates),
        skipped_count=len(skipped_candidates),
        penalty_candidate_count=sum(1 for candidate in final_candidates if candidate.penalties),
        warnings=warnings,
        skip_reason_counts=dict(Counter(candidate.reason for candidate in skipped_candidates)),
        penalty_counts=dict(penalty_counter),
    )
    return ScannerRunResult(candidates=final_candidates, skipped_candidates=skipped_candidates, summary=summary)


def evaluate_stock_candidate(
    stock_records: Sequence[DailyStockRecord],
    benchmark_records_by_symbol: Mapping[ScannerBenchmarkSymbol, Sequence[BenchmarkDailyRecord]],
    config: ScannerConfig,
) -> ScannerPassCandidate | SkippedScannerCandidate:
    records = sorted(stock_records, key=lambda record: record.date)
    if not records:
        return SkippedScannerCandidate(reason="no stock records")

    latest = records[-1]
    if len(records) < 60:
        return _skip(latest, "insufficient history for MA60", [f"need 60, got {len(records)}"])
    if latest.close <= 0:
        return _skip(latest, "close <= 0", [f"close={latest.close}"])
    if latest.turnover_value < config.min_turnover_value:
        return _skip(
            latest,
            "turnover_value below configured liquidity floor",
            [f"turnover_value={latest.turnover_value}", f"min_turnover_value={config.min_turnover_value}"],
        )

    benchmark_symbol = MARKET_BENCHMARKS[latest.market_type]
    benchmark_records = benchmark_records_by_symbol.get(benchmark_symbol, [])
    indicators = calculate_stock_indicators(records, benchmark_records)
    regime = classify_benchmark_regime(benchmark_records)
    context_result = build_stock_advice_context_data(records, indicators, regime)
    if context_result.context_data is None:
        skipped = context_result.skipped_candidate
        reason = f"context writer skipped: {skipped.reason}" if skipped else "context writer skipped"
        details = list(skipped.details if skipped else [])
        return _skip(latest, reason, details)

    context_data = copy.deepcopy(context_result.context_data)
    _extend_unique(context_data.setdefault("data_quality_warnings", []), context_result.warnings)
    technical_position = classify_technical_position(latest, indicators)
    context_data["technical"]["position"] = technical_position
    _remove_context_warning(context_data, "technical classifier not implemented in M3; technical.position set to unknown")
    context_data.setdefault("data_source_notes", []).append(
        "technical.position is classified by deterministic M4 scanner policy"
    )

    hard_skip = _hard_skip_reason(context_data, technical_position)
    if hard_skip is not None:
        return _skip(latest, hard_skip[0], hard_skip[1])

    penalties = _penalties(context_data, technical_position)
    _extend_unique(context_data.setdefault("data_quality_warnings", []), penalties)
    context_data.setdefault("scanner_metadata", {}).update(
        {
            "technical_position": technical_position,
            "penalties": penalties,
        }
    )

    risk = context_data["risk"]
    stock = context_data["stock"]
    scanner_metadata = context_data["scanner_metadata"]
    return ScannerPassCandidate(
        stock_id=latest.stock_id,
        stock_name=latest.name,
        market_type=latest.market_type,
        date=latest.date,
        risk_reward_ratio=risk["risk_reward_ratio"],
        relative_strength_20d_vs_benchmark=scanner_metadata.get("relative_strength_20d_vs_benchmark"),
        relative_strength_60d_vs_benchmark=scanner_metadata.get("relative_strength_60d_vs_benchmark"),
        volume_ratio_20d=stock["volume_ratio_20d"],
        technical_position=technical_position,
        distance_from_ma20=scanner_metadata.get("distance_from_ma20"),
        penalties=penalties,
        context_data=context_data,
    )


def rank_scanner_candidates(candidates: Sequence[ScannerPassCandidate]) -> list[ScannerPassCandidate]:
    return sorted(candidates, key=_candidate_sort_key)


def classify_technical_position(
    latest: DailyStockRecord,
    indicators: StockIndicatorSnapshot,
) -> ScannerTechnicalPosition:
    close = latest.close
    if indicators.ma20 is not None and indicators.prior_20d_low is not None:
        if close < indicators.ma20 and close < indicators.prior_20d_low:
            return "breakdown"

    if indicators.ma10 is not None and close >= indicators.ma10 and latest.low <= indicators.ma10 * 1.015 and close > latest.open:
        return "pullback_to_ma10_and_rebound"
    if indicators.ma5 is not None and close >= indicators.ma5 and latest.low <= indicators.ma5 * 1.01 and close > latest.open:
        return "pullback_to_ma5"
    if indicators.ma20 is not None and close >= indicators.ma20 and latest.low <= indicators.ma20 * 1.02:
        return "near_ma20_support"
    if indicators.prior_20d_high is not None and indicators.volume_ratio_20d is not None:
        if close > indicators.prior_20d_high and indicators.volume_ratio_20d >= 1.5:
            return "breakout"
    if indicators.ma20 is not None and close >= indicators.ma20 * 1.12:
        return "extended_above_ma"
    if indicators.ma10 is not None and close >= indicators.ma10 * 1.08:
        return "extended_above_ma"
    if indicators.ma20 is not None and indicators.prior_20d_high is not None:
        if close >= indicators.ma20 * 0.98 and close <= indicators.prior_20d_high:
            return "range_bound"
    return "unknown"


def _hard_skip_reason(
    context_data: dict,
    technical_position: ScannerTechnicalPosition,
) -> tuple[str, list[str]] | None:
    stock = context_data["stock"]
    risk = context_data["risk"]
    technical = context_data["technical"]
    close = stock["close"]
    change_pct = stock["change_pct"]

    if change_pct < -3:
        return "change_pct < -3", [f"change_pct={change_pct}"]
    if technical_position == "breakdown":
        return "technical.position == breakdown", []
    if risk.get("nearest_support") is None:
        return "risk.nearest_support missing", []
    if risk.get("invalid_level") is None:
        return "risk.invalid_level missing", []
    if risk["invalid_level"] >= close:
        return "risk.invalid_level >= close", [f"invalid_level={risk['invalid_level']}", f"close={close}"]
    if risk.get("risk_reward_ratio") is None:
        return "risk.risk_reward_ratio missing", []
    if risk["risk_reward_ratio"] <= 1.0:
        return "risk_reward_ratio <= 1.0", [f"risk_reward_ratio={risk['risk_reward_ratio']}"]
    if risk.get("planned_target") is None:
        return "risk.planned_target missing", []
    if risk["planned_target"] <= close:
        return "planned_target <= close", [f"planned_target={risk['planned_target']}", f"close={close}"]
    if technical.get("is_limit_up") is True:
        return "is_limit_up == true", []
    return None


def _penalties(context_data: dict, technical_position: ScannerTechnicalPosition) -> list[str]:
    stock = context_data["stock"]
    risk = context_data["risk"]
    market_regime = context_data["market_regime"]
    technical = context_data["technical"]
    theme = context_data["theme"]
    penalties: list[str] = []

    if 1.0 < risk["risk_reward_ratio"] < 1.5:
        penalties.append("risk_reward_ratio below small_probe threshold")
    if stock["volume_ratio_20d"] < 1.2:
        penalties.append("volume_ratio_20d below 1.2")
    if stock["change_pct"] >= 7 and technical.get("is_limit_up") is not True:
        penalties.append("no-chase penalty: change_pct >= 7")
    if market_regime["risk_state"] == "risk_off":
        penalties.append("market risk_off; guardrails will forbid A-grade")
    if technical_position == "extended_above_ma":
        penalties.append("extended above moving averages; no-chase risk")
    if technical_position == "unknown":
        penalties.append("technical position unknown")
    if theme.get("lifecycle") == "unknown":
        penalties.append("theme lifecycle unknown; market_scan fallback used")
    if technical.get("is_overheated") is True:
        penalties.append("is_overheated == true")
    return penalties


def _candidate_sort_key(candidate: ScannerPassCandidate) -> tuple:
    return (
        -candidate.risk_reward_ratio,
        -_none_low(candidate.relative_strength_20d_vs_benchmark),
        -_none_low(candidate.relative_strength_60d_vs_benchmark),
        -candidate.volume_ratio_20d,
        TECHNICAL_POSITION_PREFERENCE[candidate.technical_position],
        _distance_above_ma20_sort_value(candidate.distance_from_ma20),
        candidate.stock_id,
    )


def _assign_rank_and_score(candidates: Sequence[ScannerPassCandidate]) -> list[ScannerPassCandidate]:
    total = len(candidates)
    ranked: list[ScannerPassCandidate] = []
    for index, candidate in enumerate(candidates, start=1):
        score = 100.0 if total <= 1 else round(100 - ((index - 1) * 100 / (total - 1)), 4)
        context_data = copy.deepcopy(candidate.context_data)
        context_data.setdefault("scanner_metadata", {}).update(
            {
                "scanner_rank": index,
                "scanner_score": score,
            }
        )
        ranked.append(
            candidate.model_copy(
                update={
                    "scanner_rank": index,
                    "scanner_score": score,
                    "context_data": context_data,
                }
            )
        )
    return ranked


def _write_candidate_context(candidate: ScannerPassCandidate, output_dir: str | Path) -> ScannerPassCandidate:
    output_path = Path(output_dir) / deterministic_context_filename(candidate.context_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(candidate.context_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(serialized, encoding="utf-8")
    return candidate.model_copy(update={"context_path": str(output_path)})


def _skip(latest: DailyStockRecord, reason: str, details: list[str]) -> SkippedScannerCandidate:
    return SkippedScannerCandidate(stock_id=latest.stock_id, date=latest.date, reason=reason, details=details)


def _remove_context_warning(context_data: dict, warning: str) -> None:
    context_data["data_quality_warnings"] = [
        item for item in context_data.get("data_quality_warnings", []) if item != warning
    ]


def _extend_unique(values: list[str], additions: Sequence[str]) -> None:
    for addition in additions:
        if addition not in values:
            values.append(addition)


def _none_low(value: float | None) -> float:
    return value if value is not None else float("-inf")


def _distance_above_ma20_sort_value(value: float | None) -> float:
    if value is None:
        return float("inf")
    return value if value > 0 else 0
