from __future__ import annotations

import copy

import pytest

from ai_advisor.guardrails import apply_balanced_guardrails
from ai_advisor.schemas import StockAdviceContext, StockAdviceOutput


def deep_merge(base: dict, updates: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def context_data(**updates) -> dict:
    base = {
        "date": "2026-05-23",
        "market_type": "listed",
        "benchmark_symbol": "TAIEX",
        "stock": {
            "stock_id": "3017",
            "name": "Stock 3017",
            "close": 123.5,
            "change_pct": 3.2,
            "volume_ratio_20d": 1.8,
        },
        "market_regime": {"risk_state": "risk_on"},
        "theme": {"name": "thermal", "rank": 1, "score": 86, "lifecycle": "main_uptrend"},
        "leader_status": {"leader_rank": "leader_1"},
        "technical": {
            "position": "pullback_to_ma10_and_rebound",
            "is_overheated": False,
            "is_limit_up": False,
        },
        "risk": {
            "invalid_level": 116,
            "nearest_support": 118,
            "planned_target": 140,
            "risk_reward_ratio": 2.1,
        },
    }
    return deep_merge(base, updates)


def raw_advice(**updates) -> StockAdviceOutput:
    data = {
        "recommendation": "small_probe",
        "grade": "B",
        "confidence": 76,
        "summary": "Structured context supports a controlled probe.",
        "bull_case": ["Risk reward is acceptable."],
        "bear_case": ["Setup fails if invalidation breaks."],
        "entry_conditions": ["Confirm next-session strength."],
        "stop_loss_plan": ["Stop at invalid_level."],
        "take_profit_plan": ["Scale out near planned target."],
        "invalidation_conditions": ["Lose invalid_level."],
        "next_session_confirmation": ["Volume confirms."],
        "risk_flags": [],
        "evidence": [{"field": "risk.risk_reward_ratio", "value": 2.1}],
        "data_quality_warnings": [],
    }
    data.update(updates)
    return StockAdviceOutput.model_validate(data)


def guarded(context_updates: dict | None = None, advice_updates: dict | None = None):
    context = StockAdviceContext.model_validate(context_data(**(context_updates or {})))
    advice = raw_advice(**(advice_updates or {}))
    return apply_balanced_guardrails(context, advice)


def test_complete_data_and_rr_above_1_5_may_allow_small_probe() -> None:
    result = guarded({"risk": {"risk_reward_ratio": 1.6}})

    assert result.guardrail_result.was_blocked is False
    assert result.final_advice.recommendation == "small_probe"


def test_risk_reward_below_1_5_forbids_small_probe() -> None:
    result = guarded({"risk": {"risk_reward_ratio": 1.2}})

    assert result.final_advice.recommendation != "small_probe"
    assert any("risk_reward_ratio below 1.5" in reason for reason in result.guardrail_result.reasons)


def test_is_overheated_forbids_small_probe() -> None:
    result = guarded({"technical": {"is_overheated": True}})

    assert result.final_advice.recommendation == "avoid_chasing"
    assert result.final_advice.grade == "C"


def test_late_stage_forbids_a_but_allows_wait_pullback() -> None:
    result = guarded(
        {"theme": {"lifecycle": "late_stage"}},
        {"grade": "A", "recommendation": "small_probe", "confidence": 84},
    )

    assert result.final_advice.grade != "A"
    assert result.final_advice.recommendation == "wait_pullback"
    assert any("late_stage" in reason for reason in result.guardrail_result.reasons)


@pytest.mark.parametrize("lifecycle", ["fading", "broken"])
def test_fading_or_broken_becomes_avoid_chasing_or_reject(lifecycle: str) -> None:
    result = guarded({"theme": {"lifecycle": lifecycle}})

    assert result.final_advice.recommendation in {"avoid_chasing", "reject"}
    assert result.final_advice.grade in {"C", "Reject"}


def test_restricted_terms_without_evidence_block() -> None:
    result = guarded(advice_updates={"summary": "外資買超 supports the setup."})

    assert result.guardrail_result.hallucination_suspected is True
    assert result.guardrail_result.was_blocked is True
    assert result.final_advice.grade == "Reject"
    assert result.final_advice.recommendation == "reject"


def test_restricted_terms_with_context_evidence_do_not_block() -> None:
    result = guarded(
        {"institutional": {"foreign_investor": "net buy"}},
        {
            "summary": "外資買超 is present in provided evidence.",
            "evidence": [{"field": "institutional.foreign_investor", "value": "net buy"}],
        },
    )

    assert result.guardrail_result.hallucination_suspected is False
    assert result.guardrail_result.was_blocked is False
