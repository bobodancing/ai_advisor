from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ai_advisor.config import DEFAULT_CONFIG, ensure_output_dir
from ai_advisor.schemas import AdviceLogEntry, GuardedAdviceOutput


def append_advice_log(
    output: GuardedAdviceOutput,
    log_path: str,
    model: str | None = None,
    prompt_version: str | None = None,
    strategy_profile: str | None = None,
) -> AdviceLogEntry:
    ensure_output_dir(log_path)
    raw = output.raw_advice
    summary = output.context_summary
    result = output.guardrail_result
    entry = AdviceLogEntry(
        timestamp=datetime.now(UTC).isoformat(),
        advice_date=summary.advice_date,
        stock_id=summary.stock_id,
        stock_name=summary.stock_name,
        advice_close=summary.advice_close,
        market_type=summary.market_type,
        benchmark_symbol=summary.benchmark_symbol,
        input_context_hash=summary.input_context_hash,
        model=model or DEFAULT_CONFIG.model,
        prompt_version=prompt_version or DEFAULT_CONFIG.prompt_version,
        strategy_profile=strategy_profile or DEFAULT_CONFIG.strategy_profile,
        raw_recommendation=raw.recommendation if raw else None,
        raw_grade=raw.grade if raw else None,
        final_recommendation=result.final_recommendation,
        final_grade=result.final_grade,
        confidence=output.final_advice.confidence,
        was_downgraded=result.was_downgraded,
        was_blocked=result.was_blocked,
        hallucination_suspected=result.hallucination_suspected,
        guardrail_reasons=result.reasons,
        stock_return_5d_pct=None,
        benchmark_return_5d_pct=None,
        alpha_5d_pct=None,
        alpha_hit_5d=None,
        was_useful=None,
        human_feedback=None,
    )
    with Path(log_path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.model_dump(), ensure_ascii=False, separators=(",", ":")) + "\n")
    return entry
