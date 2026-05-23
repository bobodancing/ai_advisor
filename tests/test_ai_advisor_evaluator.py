from __future__ import annotations

import json
from pathlib import Path

from ai_advisor.evaluator import update_followup_returns


FIXTURE_FOLLOWUP_CSV = Path(__file__).parent / "fixtures" / "ai_advisor" / "followup_prices_valid.csv"


def test_positive_5_day_alpha_sets_alpha_hit_true(tmp_path: Path) -> None:
    advice_log = tmp_path / "ai_advice_log.jsonl"
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    write_jsonl(
        advice_log,
        [
            advice_entry(
                stock_id="3001",
                advice_close=100,
                final_grade="B",
                final_recommendation="small_probe",
                input_context_hash="hash-3001",
            )
        ],
    )
    followup_csv = tmp_path / "followup.csv"
    followup_csv.write_text(
        "stock_id,advice_date,input_context_hash,close_5d,benchmark_return_5d_pct\n"
        "3001,2026-05-23,hash-3001,105,1.0\n",
        encoding="utf-8",
    )

    summary = update_followup_returns(str(advice_log), str(followup_csv), str(evaluation_log))
    record = read_jsonl(evaluation_log)[0]

    assert record["stock_return_5d_pct"] == 5
    assert record["alpha_5d_pct"] == 4
    assert record["alpha_hit_5d"] is True
    assert record["included_in_alpha_denominator"] is True
    assert summary.alpha_hit_rate_5d_vs_market == 1.0
    assert summary.average_alpha_5d_pct == 4


def test_observe_is_excluded_from_main_alpha_denominator(tmp_path: Path) -> None:
    advice_log = tmp_path / "ai_advice_log.jsonl"
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    write_jsonl(
        advice_log,
        [
            advice_entry(
                stock_id="3002",
                advice_close=100,
                final_grade="B",
                final_recommendation="observe",
                input_context_hash="hash-observe",
            )
        ],
    )
    followup_csv = tmp_path / "followup.csv"
    followup_csv.write_text(
        "stock_id,advice_date,close_5d,benchmark_return_5d_pct\n"
        "3002,2026-05-23,110,0\n",
        encoding="utf-8",
    )

    summary = update_followup_returns(str(advice_log), str(followup_csv), str(evaluation_log))
    record = read_jsonl(evaluation_log)[0]

    assert record["alpha_5d_pct"] == 10
    assert record["alpha_hit_5d"] is True
    assert record["included_in_alpha_denominator"] is False
    assert record["exclusion_reason"] == "not actionable candidate"
    assert summary.actionable_candidate_count == 0
    assert summary.complete_followup_count == 0
    assert summary.alpha_hit_rate_5d_vs_market is None


def test_missing_benchmark_return_excludes_row_and_warns(tmp_path: Path) -> None:
    advice_log = tmp_path / "ai_advice_log.jsonl"
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    write_jsonl(
        advice_log,
        [
            advice_entry(
                stock_id="3003",
                advice_close=100,
                final_grade="A",
                final_recommendation="wait_pullback",
                input_context_hash="hash-3003",
            )
        ],
    )
    followup_csv = tmp_path / "followup.csv"
    followup_csv.write_text(
        "stock_id,advice_date,close_5d,benchmark_return_5d_pct\n"
        "3003,2026-05-23,108,\n",
        encoding="utf-8",
    )

    summary = update_followup_returns(str(advice_log), str(followup_csv), str(evaluation_log))
    record = read_jsonl(evaluation_log)[0]

    assert record["stock_return_5d_pct"] == 8
    assert record["benchmark_return_5d_pct"] is None
    assert record["alpha_5d_pct"] is None
    assert record["alpha_hit_5d"] is None
    assert record["included_in_alpha_denominator"] is False
    assert record["exclusion_reason"] == "missing benchmark_return_5d_pct"
    assert summary.actionable_candidate_count == 1
    assert summary.complete_followup_count == 0
    assert any("missing benchmark_return_5d_pct" in warning for warning in summary.warnings)


def test_followup_evaluation_appends_and_does_not_mutate_advice_log(tmp_path: Path) -> None:
    advice_log = tmp_path / "ai_advice_log.jsonl"
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    write_jsonl(
        advice_log,
        [
            advice_entry(
                stock_id="3001",
                advice_close=101,
                final_grade="A",
                final_recommendation="small_probe",
                input_context_hash="hash-3001",
            ),
            advice_entry(
                stock_id="3002",
                advice_close=102,
                final_grade="A",
                final_recommendation="small_probe",
                input_context_hash="hash-3002",
            ),
        ],
    )
    original_advice_log = advice_log.read_text(encoding="utf-8")

    summary = update_followup_returns(str(advice_log), str(FIXTURE_FOLLOWUP_CSV), str(evaluation_log))

    assert advice_log.read_text(encoding="utf-8") == original_advice_log
    evaluation_records = read_jsonl(evaluation_log)
    assert len(evaluation_records) == 2
    assert summary.appended_evaluation_count == 2
    assert summary.complete_followup_count == 2
    assert evaluation_records[0]["input_context_hash"] == "hash-3001"
    assert evaluation_records[0]["source_followup_csv"] == str(FIXTURE_FOLLOWUP_CSV)

    update_followup_returns(str(advice_log), str(FIXTURE_FOLLOWUP_CSV), str(evaluation_log))

    assert advice_log.read_text(encoding="utf-8") == original_advice_log
    assert len(read_jsonl(evaluation_log)) == 4


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def advice_entry(
    *,
    stock_id: str,
    advice_close: float,
    final_grade: str,
    final_recommendation: str,
    input_context_hash: str,
) -> dict:
    return {
        "timestamp": "2026-05-23T12:00:00+00:00",
        "advice_type": "stock_batch",
        "advice_date": "2026-05-23",
        "stock_id": stock_id,
        "stock_name": f"Stock {stock_id}",
        "advice_close": advice_close,
        "market_type": "listed",
        "benchmark_symbol": "TAIEX",
        "input_context_hash": input_context_hash,
        "model": "fake-demo",
        "prompt_version": "v1.2",
        "strategy_profile": "balanced",
        "raw_recommendation": final_recommendation,
        "raw_grade": final_grade,
        "final_recommendation": final_recommendation,
        "final_grade": final_grade,
        "confidence": 80,
        "was_downgraded": False,
        "was_blocked": False,
        "hallucination_suspected": False,
        "guardrail_reasons": [],
        "stock_return_5d_pct": None,
        "benchmark_return_5d_pct": None,
        "alpha_5d_pct": None,
        "alpha_hit_5d": None,
        "was_useful": None,
        "human_feedback": None,
    }
