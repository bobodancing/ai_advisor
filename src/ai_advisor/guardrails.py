from __future__ import annotations

from typing import Iterable

from ai_advisor.config import DEFAULT_CONFIG, GuardrailConfig
from ai_advisor.schemas import (
    ContextSummary,
    EvidenceItem,
    Grade,
    GuardedAdviceOutput,
    GuardrailResult,
    Recommendation,
    StockAdviceContext,
    StockAdviceOutput,
    get_context_path,
)


RESTRICTED_TERMS: dict[str, tuple[str, ...]] = {
    "新聞": ("新聞", "news"),
    "法人": ("法人", "institutional"),
    "外資": ("外資", "foreign", "foreign_investor"),
    "投信": ("投信", "investment_trust"),
    "營收": ("營收", "revenue"),
    "EPS": ("eps", "EPS"),
    "目標價": ("目標價", "target_price"),
    "財報": ("財報", "financial_report", "financials"),
    "訂單": ("訂單", "order", "orders"),
}

GRADE_ORDER: dict[Grade, int] = {"Reject": 0, "C": 1, "B": 2, "A": 3}


def apply_balanced_guardrails(
    context: StockAdviceContext,
    raw_advice: StockAdviceOutput,
    config: GuardrailConfig | None = None,
    input_context_hash: str | None = None,
) -> GuardedAdviceOutput:
    guardrail_config = config or DEFAULT_CONFIG.guardrails
    final = raw_advice.model_copy(deep=True)
    reasons: list[str] = []
    hallucination_suspected = False
    was_blocked = False

    missing_fields = context.missing_required_fields()
    if missing_fields:
        for field in missing_fields:
            message = f"missing required field: {field}"
            _append_unique(final.data_quality_warnings, message)
            reasons.append(message)
        final.grade = _cap_grade(final.grade, "C")
        if final.recommendation not in {"observe", "avoid_chasing", "reject"}:
            final.recommendation = "observe"
            reasons.append("required data missing; positive recommendation downgraded to observe")
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_data_missing)

    no_probe_missing_fields = {
        "risk.invalid_level",
        "risk.risk_reward_ratio",
        "technical.position",
        "theme.lifecycle",
        "market_regime.risk_state",
    }
    if final.recommendation == "small_probe" and no_probe_missing_fields.intersection(missing_fields):
        final.recommendation = "observe"
        final.grade = _cap_grade(final.grade, "C")
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_data_missing)
        reasons.append("required risk setup missing; small_probe downgraded")

    rr = context.risk.risk_reward_ratio
    if final.grade == "A" and (rr is None or rr < guardrail_config.min_rr_for_grade_a):
        final.grade = "B"
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("risk_reward_ratio below 2.0; grade A downgraded")

    if final.recommendation == "small_probe" and (rr is None or rr < guardrail_config.min_rr_for_small_probe):
        final.recommendation = "wait_pullback"
        final.grade = _cap_grade(final.grade, "C")
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("risk_reward_ratio below 1.5; small_probe downgraded")

    if context.technical.is_overheated is True and final.recommendation == "small_probe":
        final.recommendation = "avoid_chasing"
        final.grade = _cap_grade(final.grade, "C")
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("is_overheated is true; small_probe downgraded")

    if context.theme.lifecycle == "late_stage":
        if final.grade == "A":
            final.grade = "B"
            final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
            reasons.append("late_stage cannot be grade A under balanced profile")
        if final.recommendation == "small_probe":
            final.recommendation = "wait_pullback"
            final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
            reasons.append("late_stage requires wait_pullback instead of small_probe")

    if context.theme.lifecycle == "fading":
        final.grade = _cap_grade(final.grade, "C")
        final.recommendation = "avoid_chasing"
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("fading lifecycle must become avoid_chasing or reject")
    elif context.theme.lifecycle == "broken":
        final.grade = "Reject"
        final.recommendation = "reject"
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("broken lifecycle must become reject")

    if context.risk.invalid_level is None and final.recommendation in {"wait_pullback", "small_probe"}:
        final.recommendation = "observe"
        final.grade = _cap_grade(final.grade, "C")
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_data_missing)
        reasons.append("risk.invalid_level is null; positive advice downgraded")

    if context.market_regime.risk_state == "risk_off" and final.grade == "A":
        final.grade = "B"
        final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("risk_off market_regime forbids grade A")

    no_chase_triggered = False
    if context.technical.position == "extended_above_ma":
        no_chase_triggered = True
        if final.recommendation == "small_probe":
            final.recommendation = "wait_pullback"
            final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("technical.position extended_above_ma; no chase downgrade applied")
    if context.technical.is_limit_up is True:
        no_chase_triggered = True
        if final.recommendation in {"small_probe", "wait_pullback"}:
            final.recommendation = "avoid_chasing"
            final.grade = _cap_grade(final.grade, "C")
            final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("technical.is_limit_up is true; no chase downgrade applied")
    if context.stock.change_pct is not None and context.stock.change_pct >= 7:
        no_chase_triggered = True
        if final.recommendation in {"small_probe", "wait_pullback"}:
            final.recommendation = "avoid_chasing"
            final.grade = _cap_grade(final.grade, "C")
            final.confidence = min(final.confidence, guardrail_config.max_confidence_when_guardrail_downgraded)
        reasons.append("stock.change_pct >= 7; no chase downgrade applied")
    if no_chase_triggered and context.risk.nearest_support is None:
        _append_unique(final.risk_flags, "support proximity unavailable")
        reasons.append("support proximity cannot be determined; risk flag added")

    unsupported_terms = _unsupported_restricted_terms(context, raw_advice)
    if unsupported_terms:
        hallucination_suspected = True
        was_blocked = True
        for term in unsupported_terms:
            reasons.append(f'hallucination suspected: unsupported term "{term}"')
        final.grade = "Reject"
        final.recommendation = "reject"
        final.confidence = 0

    final.grade, final.recommendation = _enforce_compatibility(final.grade, final.recommendation, reasons)

    if final.grade == "Reject" and final.recommendation == "reject":
        was_blocked = was_blocked or raw_advice.grade != "Reject" or raw_advice.recommendation != "reject"

    was_downgraded = (
        raw_advice.grade != final.grade
        or raw_advice.recommendation != final.recommendation
        or raw_advice.confidence != final.confidence
    )

    context_summary = ContextSummary(
        advice_date=context.date,
        stock_id=context.stock.stock_id,
        stock_name=context.stock.name,
        advice_close=context.stock.close,
        market_type=context.market_type or "unknown",
        benchmark_symbol=context.benchmark_symbol or "unknown",
        input_context_hash=input_context_hash,
    )
    result = GuardrailResult(
        was_downgraded=was_downgraded,
        was_blocked=was_blocked,
        final_grade=final.grade,
        final_recommendation=final.recommendation,
        reasons=_dedupe(reasons),
        hallucination_suspected=hallucination_suspected,
        error_message=None,
    )
    return GuardedAdviceOutput(raw_advice=raw_advice, final_advice=final, context_summary=context_summary, guardrail_result=result)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _cap_grade(grade: Grade, max_grade: Grade) -> Grade:
    return grade if GRADE_ORDER[grade] <= GRADE_ORDER[max_grade] else max_grade


def _advice_text(advice: StockAdviceOutput) -> str:
    text_parts = [
        advice.summary,
        *advice.bull_case,
        *advice.bear_case,
        *advice.entry_conditions,
        *advice.stop_loss_plan,
        *advice.take_profit_plan,
        *advice.invalidation_conditions,
        *advice.next_session_confirmation,
        *advice.risk_flags,
    ]
    return "\n".join(text_parts)


def _unsupported_restricted_terms(context: StockAdviceContext, advice: StockAdviceOutput) -> list[str]:
    advice_text = _advice_text(advice).lower()
    unsupported: list[str] = []
    for term, tokens in RESTRICTED_TERMS.items():
        if any(token.lower() in advice_text for token in tokens) and not _has_matching_evidence(context, advice.evidence, term):
            unsupported.append(term)
    return unsupported


def _has_matching_evidence(context: StockAdviceContext, evidence: list[EvidenceItem], term: str) -> bool:
    tokens = tuple(token.lower() for token in RESTRICTED_TERMS[term])
    for item in evidence:
        field = item.field
        lowered = field.lower()
        if any(token in lowered for token in tokens) and get_context_path(context, field) is not None:
            return True
    return False


def _enforce_compatibility(grade: Grade, recommendation: Recommendation, reasons: list[str]) -> tuple[Grade, Recommendation]:
    allowed: dict[Grade, set[Recommendation]] = {
        "A": {"wait_pullback", "small_probe"},
        "B": {"observe", "wait_pullback", "small_probe"},
        "C": {"observe", "wait_pullback", "avoid_chasing"},
        "Reject": {"avoid_chasing", "reject"},
    }
    if recommendation in allowed[grade]:
        return grade, recommendation

    original = (grade, recommendation)
    if recommendation == "reject":
        grade = "Reject"
    elif recommendation == "avoid_chasing":
        grade = "C" if grade != "Reject" else grade
    elif recommendation == "small_probe" and grade == "C":
        recommendation = "wait_pullback"
    elif grade == "A":
        grade = "B"
    elif grade == "Reject":
        recommendation = "reject"
    else:
        recommendation = "observe"

    if recommendation not in allowed[grade]:
        grade = "Reject"
        recommendation = "reject"

    reasons.append(
        f"grade/recommendation compatibility corrected from {original[0]}/{original[1]} to {grade}/{recommendation}"
    )
    return grade, recommendation
