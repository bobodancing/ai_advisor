from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_advisor.schemas import StockAdviceContext, StockAdviceOutput


def valid_context_data() -> dict:
    return {
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
        "data_source_notes": [],
    }


def valid_advice_data() -> dict:
    return {
        "recommendation": "small_probe",
        "grade": "A",
        "confidence": 82,
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


def test_valid_stock_advice_context_passes() -> None:
    context = StockAdviceContext.model_validate(valid_context_data())

    assert context.stock.stock_id == "3017"
    assert context.market_type == "listed"
    assert context.benchmark_symbol == "TAIEX"
    assert context.missing_required_fields() == []


def test_missing_market_type_defaults_benchmark_to_taiex_and_warns() -> None:
    data = valid_context_data()
    data.pop("market_type")
    data.pop("benchmark_symbol")

    context = StockAdviceContext.model_validate(data)

    assert context.market_type == "unknown"
    assert context.benchmark_symbol == "TAIEX"
    assert "market_type missing or unknown; default benchmark_symbol set to TAIEX" in context.data_quality_warnings


def test_unknown_market_type_preserves_explicit_valid_benchmark_and_warns() -> None:
    data = valid_context_data()
    data["market_type"] = "unknown"
    data["benchmark_symbol"] = "OTC"

    context = StockAdviceContext.model_validate(data)

    assert context.market_type == "unknown"
    assert context.benchmark_symbol == "OTC"
    assert "market_type missing or unknown; explicit benchmark_symbol preserved" in context.data_quality_warnings


def test_invalid_stock_advice_output_enum_fails_validation() -> None:
    data = valid_advice_data()
    data["recommendation"] = "buy_now"

    with pytest.raises(ValidationError):
        StockAdviceOutput.model_validate(data)


def test_stock_advice_output_rejects_unsupported_extra_field() -> None:
    data = valid_advice_data()
    data["unsupported_extra"] = "外資買超 hidden outside fixed schema"

    with pytest.raises(ValidationError):
        StockAdviceOutput.model_validate(data)