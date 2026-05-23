from __future__ import annotations

import json
from pathlib import Path

from ai_advisor.batch_engine import generate_stock_batch_advice, rank_stock_advices
from ai_advisor.llm_client import FakeStockAdviceClient
from ai_advisor.schemas import ContextSummary, GuardedAdviceOutput, GuardrailResult, StockAdviceOutput


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ai_advisor" / "stock_contexts"


def test_20_plus_fixture_contexts_can_be_processed_in_fake_mode() -> None:
    paths = sorted(str(path) for path in FIXTURE_DIR.glob("*.json"))
    assert len(paths) >= 20

    outputs = generate_stock_batch_advice(paths, append_log=False)

    assert len(outputs) == len(paths)
    assert all(output.raw_advice is not None for output in outputs)
    assert any(output.final_advice.recommendation == "small_probe" for output in outputs)
    ranked = rank_stock_advices(outputs)
    assert [row.rank for row in ranked] == list(range(1, len(paths) + 1))


def test_one_llm_failure_does_not_stop_batch() -> None:
    paths = sorted(str(path) for path in FIXTURE_DIR.glob("*.json"))[:5]
    outputs = generate_stock_batch_advice(
        paths,
        llm_client=FakeStockAdviceClient(fail_stock_ids={"3003"}),
        append_log=False,
    )

    assert len(outputs) == 5
    failed = [output for output in outputs if output.guardrail_result.was_blocked]
    assert len(failed) == 1
    assert "LLM request failed" in failed[0].guardrail_result.error_message
    assert sum(output.raw_advice is not None for output in outputs) == 4


def test_one_validation_failure_does_not_stop_batch(tmp_path: Path) -> None:
    valid_path = next(FIXTURE_DIR.glob("*.json"))
    invalid_path = tmp_path / "invalid_context.json"
    invalid_data = json.loads(valid_path.read_text(encoding="utf-8"))
    invalid_data["market_regime"]["risk_state"] = "risk_maybe"
    invalid_path.write_text(json.dumps(invalid_data), encoding="utf-8")

    outputs = generate_stock_batch_advice([str(valid_path), str(invalid_path)], append_log=False)

    assert len(outputs) == 2
    assert outputs[0].guardrail_result.was_blocked is False
    assert outputs[1].guardrail_result.was_blocked is True
    assert "context validation failed" in outputs[1].guardrail_result.error_message


def test_ranking_follows_fixed_priority() -> None:
    outputs = [
        make_output("3004", "B", "wait_pullback", 90),
        make_output("3003", "B", "small_probe", 50),
        make_output("3002", "A", "wait_pullback", 10),
        make_output("3001", "Reject", "reject", 99),
        make_output("3000", "A", "small_probe", 99, blocked=True),
        make_output("3008", "C", "observe", 40),
        make_output("3007", "C", "observe", 40),
    ]

    ranked = rank_stock_advices(outputs)

    assert [row.stock_id for row in ranked] == ["3002", "3003", "3004", "3007", "3008", "3001", "3000"]


def test_advice_log_appends_immutable_snapshot_with_null_alpha_placeholders(tmp_path: Path) -> None:
    path = next(FIXTURE_DIR.glob("*.json"))
    log_path = tmp_path / "ai_advice_log.jsonl"

    generate_stock_batch_advice([str(path)], log_path=str(log_path), append_log=True)
    generate_stock_batch_advice([str(path)], log_path=str(log_path), append_log=True)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["advice_close"] is not None
    assert first["market_type"] in {"listed", "otc", "unknown"}
    assert first["benchmark_symbol"] in {"TAIEX", "OTC", "unknown"}
    assert first["input_context_hash"]
    assert first["stock_return_5d_pct"] is None
    assert first["benchmark_return_5d_pct"] is None
    assert first["alpha_5d_pct"] is None
    assert first["alpha_hit_5d"] is None


def make_output(
    stock_id: str,
    grade: str,
    recommendation: str,
    confidence: int,
    blocked: bool = False,
) -> GuardedAdviceOutput:
    advice = StockAdviceOutput(
        recommendation=recommendation,
        grade=grade,
        confidence=confidence,
        summary="ranking fixture",
        bull_case=[],
        bear_case=[],
        entry_conditions=[],
        stop_loss_plan=[],
        take_profit_plan=[],
        invalidation_conditions=[],
        next_session_confirmation=[],
        risk_flags=[],
        evidence=[],
        data_quality_warnings=[],
    )
    return GuardedAdviceOutput(
        raw_advice=advice,
        final_advice=advice,
        context_summary=ContextSummary(
            advice_date="2026-05-23",
            stock_id=stock_id,
            stock_name=f"Stock {stock_id}",
            advice_close=100,
            market_type="listed",
            benchmark_symbol="TAIEX",
            input_context_hash=f"hash-{stock_id}",
        ),
        guardrail_result=GuardrailResult(
            was_downgraded=False,
            was_blocked=blocked,
            final_grade=grade,
            final_recommendation=recommendation,
            reasons=[] if not blocked else ["blocked for ranking test"],
            hallucination_suspected=False,
            error_message=None,
        ),
    )
