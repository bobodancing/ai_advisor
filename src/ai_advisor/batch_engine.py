from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ai_advisor.config import DEFAULT_CONFIG
from ai_advisor.guardrails import apply_balanced_guardrails
from ai_advisor.llm_client import FakeStockAdviceClient
from ai_advisor.logging import append_advice_log
from ai_advisor.schemas import (
    ContextSummary,
    GuardedAdviceOutput,
    GuardrailResult,
    RankedStockAdvice,
    StockAdviceContext,
    StockAdviceOutput,
    validate_stock_advice_output,
)


def generate_stock_batch_advice(
    context_paths: list[str],
    llm_client: Any | None = None,
    log_path: str | None = None,
    append_log: bool = True,
) -> list[GuardedAdviceOutput]:
    client = llm_client or FakeStockAdviceClient()
    outputs: list[GuardedAdviceOutput] = []
    for context_path in context_paths:
        output = _generate_one(context_path, client)
        outputs.append(output)
        if append_log:
            append_advice_log(output, log_path or DEFAULT_CONFIG.log_path)
    return outputs


def _generate_one(context_path: str, llm_client: Any) -> GuardedAdviceOutput:
    try:
        raw_text = Path(context_path).read_text(encoding="utf-8")
        context_hash = sha256(raw_text.encode("utf-8")).hexdigest()
        data = json.loads(raw_text)
    except Exception as exc:
        return _blocked_error_row(None, None, f"context read failed: {exc}")

    try:
        context = StockAdviceContext.model_validate(data)
    except ValidationError as exc:
        return _blocked_error_row(data, context_hash, f"context validation failed: {exc.errors()[0]['msg']}")

    try:
        raw_result = llm_client.generate_stock_advice(context)
        raw_advice = validate_stock_advice_output(raw_result)
    except ValidationError as exc:
        return _blocked_error_row(data, context_hash, f"raw advice validation failed: {exc.errors()[0]['msg']}", context)
    except Exception as exc:
        return _blocked_error_row(data, context_hash, f"LLM request failed: {exc}", context)

    return apply_balanced_guardrails(context, raw_advice, input_context_hash=context_hash)


def rank_stock_advices(outputs: list[GuardedAdviceOutput]) -> list[RankedStockAdvice]:
    grade_rank = {"A": 0, "B": 1, "C": 2, "Reject": 3}
    recommendation_rank = {
        "small_probe": 0,
        "wait_pullback": 1,
        "observe": 2,
        "avoid_chasing": 3,
        "reject": 4,
    }

    def sort_key(output: GuardedAdviceOutput) -> tuple[Any, ...]:
        return (
            output.guardrail_result.was_blocked,
            grade_rank[output.final_advice.grade],
            recommendation_rank[output.final_advice.recommendation],
            -output.final_advice.confidence,
            len(output.final_advice.risk_flags),
            output.context_summary.stock_id or "",
        )

    ranked_outputs = sorted(outputs, key=sort_key)
    ranked: list[RankedStockAdvice] = []
    for index, output in enumerate(ranked_outputs, start=1):
        ranked.append(
            RankedStockAdvice(
                rank=index,
                stock_id=output.context_summary.stock_id or "",
                stock_name=output.context_summary.stock_name or "",
                grade=output.final_advice.grade,
                recommendation=output.final_advice.recommendation,
                confidence=output.final_advice.confidence,
                risk_flags_count=len(output.final_advice.risk_flags),
                data_quality_warnings_count=len(output.final_advice.data_quality_warnings),
                was_blocked=output.guardrail_result.was_blocked,
                guardrail_reasons=output.guardrail_result.reasons,
                guarded_advice=output,
            )
        )
    return ranked


def _blocked_error_row(
    data: dict[str, Any] | None,
    context_hash: str | None,
    error_message: str,
    context: StockAdviceContext | None = None,
) -> GuardedAdviceOutput:
    summary = _context_summary_from_data(data, context_hash, context)
    final = StockAdviceOutput(
        recommendation="reject",
        grade="Reject",
        confidence=0,
        summary=error_message,
        bull_case=[],
        bear_case=[error_message],
        entry_conditions=[],
        stop_loss_plan=[],
        take_profit_plan=[],
        invalidation_conditions=[error_message],
        next_session_confirmation=[],
        risk_flags=["blocked_error_row"],
        evidence=[],
        data_quality_warnings=[error_message],
    )
    return GuardedAdviceOutput(
        raw_advice=None,
        final_advice=final,
        context_summary=summary,
        guardrail_result=GuardrailResult(
            was_downgraded=False,
            was_blocked=True,
            final_grade="Reject",
            final_recommendation="reject",
            reasons=[error_message],
            hallucination_suspected=False,
            error_message=error_message,
        ),
    )


def _context_summary_from_data(
    data: dict[str, Any] | None,
    context_hash: str | None,
    context: StockAdviceContext | None = None,
) -> ContextSummary:
    if context is not None:
        return ContextSummary(
            advice_date=context.date,
            stock_id=context.stock.stock_id,
            stock_name=context.stock.name,
            advice_close=context.stock.close,
            market_type=context.market_type or "unknown",
            benchmark_symbol=context.benchmark_symbol or "unknown",
            input_context_hash=context_hash,
        )

    stock = data.get("stock", {}) if isinstance(data, dict) else {}
    market_type = data.get("market_type", "unknown") if isinstance(data, dict) else "unknown"
    benchmark_symbol = data.get("benchmark_symbol", "unknown") if isinstance(data, dict) else "unknown"
    if market_type not in {"listed", "otc", "unknown"}:
        market_type = "unknown"
    if benchmark_symbol not in {"TAIEX", "OTC", "unknown"}:
        benchmark_symbol = "unknown"
    return ContextSummary(
        advice_date=data.get("date") if isinstance(data, dict) else None,
        stock_id=str(stock.get("stock_id")) if isinstance(stock, dict) and stock.get("stock_id") is not None else None,
        stock_name=stock.get("name") if isinstance(stock, dict) else None,
        advice_close=stock.get("close") if isinstance(stock, dict) else None,
        market_type=market_type,
        benchmark_symbol=benchmark_symbol,
        input_context_hash=context_hash,
    )


def update_followup_returns(
    advice_log_path: str,
    followup_csv_path: str,
    evaluation_log_path: str = DEFAULT_CONFIG.evaluation_log_path,
):
    from ai_advisor.evaluator import update_followup_returns as evaluator_update_followup_returns

    return evaluator_update_followup_returns(
        advice_log_path,
        followup_csv_path,
        evaluation_log_path=evaluation_log_path,
    )