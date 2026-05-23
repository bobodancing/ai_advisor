from __future__ import annotations

import json
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ai_advisor" / "stock_contexts"
APP_PATH = Path(__file__).parents[1] / "apps" / "ai_advisor_streamlit.py"


spec = importlib.util.spec_from_file_location("ai_advisor_streamlit_app", APP_PATH)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def test_fixture_folder_can_load_and_fake_batch_renders_sorted_table() -> None:
    paths, messages = app.load_folder_context_paths(str(FIXTURE_DIR), max_batch_size=50)

    assert messages == []
    assert len(paths) >= 20

    ranked = app.run_batch(app.MODE_FAKE, paths, append_log=False)
    rows = app.ranked_table_rows(ranked)

    assert rows
    assert tuple(rows[0].keys()) == app.TABLE_COLUMNS
    assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))


def test_fake_demo_and_real_llm_modes_can_switch_with_real_mode_guard(monkeypatch) -> None:
    paths, _ = app.load_folder_context_paths(str(FIXTURE_DIR), max_batch_size=50)

    assert app.mode_options() == (app.MODE_FAKE, app.MODE_REAL)
    assert app.build_run_gate(app.MODE_FAKE, [], max_llm_calls_per_run=50, api_key=None).can_submit is True

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    missing_key_gate = app.build_run_gate(app.MODE_REAL, paths, max_llm_calls_per_run=50, api_key=None)

    assert missing_key_gate.estimated_llm_calls == len(paths)
    assert missing_key_gate.can_submit is False
    assert any("OPENAI_API_KEY" in message for message in missing_key_gate.messages)

    too_many_gate = app.build_run_gate(app.MODE_REAL, paths, max_llm_calls_per_run=1, api_key="test-key")

    assert too_many_gate.can_submit is False
    assert any("exceeds max_llm_calls_per_run" in message for message in too_many_gate.messages)

    guard_only_gate = app.build_run_gate(app.MODE_REAL, paths, max_llm_calls_per_run=50, api_key="test-key")

    assert guard_only_gate.estimated_llm_calls == len(paths)
    assert guard_only_gate.can_submit is False
    assert any("guard-only in Session G" in message for message in guard_only_gate.messages)


def test_table_filters_respect_show_blocked_rows() -> None:
    paths, _ = app.load_folder_context_paths(str(FIXTURE_DIR), max_batch_size=5)
    ranked = app.run_batch(app.MODE_FAKE, paths, append_log=False)

    filtered = app.apply_ranked_filters(
        ranked,
        selected_grades=["A", "B", "C", "Reject"],
        selected_recommendations=["small_probe", "wait_pullback", "observe", "avoid_chasing", "reject"],
        show_blocked_rows=False,
    )

    assert all(row.was_blocked is False for row in filtered)


def test_detail_view_model_displays_final_stock_plan_sections() -> None:
    paths, _ = app.load_folder_context_paths(str(FIXTURE_DIR), max_batch_size=1)
    ranked = app.run_batch(app.MODE_FAKE, paths, append_log=False)
    sections = app.stock_detail_sections(ranked[0].guarded_advice)

    assert tuple(sections.keys()) == app.DETAIL_SECTION_TITLES
    assert sections["conclusion"]
    assert sections["entry_plan"]
    assert sections["stop_loss"]
    assert ranked[0].guarded_advice.final_advice.summary in sections["conclusion"]


def test_alpha_evaluation_view_uses_placeholder_without_complete_followup_records() -> None:
    paths, _ = app.load_folder_context_paths(str(FIXTURE_DIR), max_batch_size=20)
    ranked = app.run_batch(app.MODE_FAKE, paths, append_log=False)
    view_model = app.alpha_evaluation_view_model(ranked, evaluation_log_path="missing_evaluation_stub.jsonl")

    assert view_model.actionable_candidate_count == sum(1 for row in ranked if app.is_actionable_candidate(row))
    assert view_model.complete_followup_count == 0
    assert view_model.alpha_hit_rate_5d_vs_market is None
    assert view_model.average_alpha_5d_pct is None
    assert "Session H" in (view_model.warning or "")
    assert "current loaded batch" in app.ALPHA_SCOPE_NOTE
    assert "existing evaluation log" in app.ALPHA_SCOPE_NOTE


def test_alpha_evaluation_view_can_read_existing_evaluation_stub(tmp_path: Path) -> None:
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    records = [
        {
            "included_in_alpha_denominator": True,
            "alpha_hit_5d": True,
            "alpha_5d_pct": 2.5,
        },
        {
            "included_in_alpha_denominator": True,
            "alpha_hit_5d": False,
            "alpha_5d_pct": -1.0,
        },
        {
            "included_in_alpha_denominator": False,
            "alpha_hit_5d": True,
            "alpha_5d_pct": 5.0,
        },
    ]
    evaluation_log.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    view_model = app.alpha_evaluation_view_model([], evaluation_log_path=evaluation_log)

    assert view_model.complete_followup_count == 2
    assert view_model.alpha_hit_rate_5d_vs_market == 0.5
    assert view_model.average_alpha_5d_pct == 0.75
    assert "existing evaluation log" in (view_model.warning or "")


def test_alpha_evaluation_view_uses_latest_evaluation_record_per_key(tmp_path: Path) -> None:
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    records = [
        {
            "timestamp": "2026-05-23T10:00:00+00:00",
            "stock_id": "3001",
            "advice_date": "2026-05-23",
            "input_context_hash": "hash-3001",
            "included_in_alpha_denominator": True,
            "alpha_hit_5d": False,
            "alpha_5d_pct": -2.0,
        },
        {
            "timestamp": "2026-05-23T11:00:00+00:00",
            "stock_id": "3001",
            "advice_date": "2026-05-23",
            "input_context_hash": "hash-3001",
            "included_in_alpha_denominator": True,
            "alpha_hit_5d": True,
            "alpha_5d_pct": 3.0,
        },
    ]
    evaluation_log.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    view_model = app.alpha_evaluation_view_model([], evaluation_log_path=evaluation_log)

    assert view_model.complete_followup_count == 1
    assert view_model.alpha_hit_rate_5d_vs_market == 1.0
    assert view_model.average_alpha_5d_pct == 3.0
    assert "superseded records exist" in (view_model.warning or "")


def test_followup_csv_upload_processes_csv_and_appends_evaluation_log(tmp_path: Path) -> None:
    advice_log = tmp_path / "ai_advice_log.jsonl"
    evaluation_log = tmp_path / "ai_advice_evaluation.jsonl"
    advice_log.write_text(
        json.dumps(
            {
                "timestamp": "2026-05-23T12:00:00+00:00",
                "advice_type": "stock_batch",
                "advice_date": "2026-05-23",
                "stock_id": "3001",
                "stock_name": "Stock 3001",
                "advice_close": 100,
                "market_type": "listed",
                "benchmark_symbol": "TAIEX",
                "input_context_hash": "hash-3001",
                "model": "fake-demo",
                "prompt_version": "v1.2",
                "strategy_profile": "balanced",
                "raw_recommendation": "small_probe",
                "raw_grade": "A",
                "final_recommendation": "small_probe",
                "final_grade": "A",
                "confidence": 82,
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
        )
        + "\n",
        encoding="utf-8",
    )
    original_advice_log = advice_log.read_text(encoding="utf-8")
    upload = UploadedFile(
        name="followup.csv",
        content=b"stock_id,advice_date,close_5d,benchmark_return_5d_pct\n3001,2026-05-23,104,1\n",
    )

    summary = app.process_followup_csv_upload(
        upload,
        advice_log_path=str(advice_log),
        evaluation_log_path=str(evaluation_log),
        cache_dir=tmp_path,
    )

    records = [json.loads(line) for line in evaluation_log.read_text(encoding="utf-8").splitlines()]
    assert advice_log.read_text(encoding="utf-8") == original_advice_log
    assert summary.alpha_hit_rate_5d_vs_market == 1.0
    assert len(records) == 1
    assert records[0]["alpha_5d_pct"] == 3


@dataclass
class UploadedFile:
    name: str
    content: bytes

    def getvalue(self) -> bytes:
        return self.content
