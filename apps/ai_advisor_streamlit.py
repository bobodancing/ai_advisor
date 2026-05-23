from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised when running the app without the dependency.
    st = None

from ai_advisor.batch_engine import generate_stock_batch_advice, rank_stock_advices
from ai_advisor.config import DEFAULT_CONFIG
from ai_advisor.schemas import GuardedAdviceOutput, RankedStockAdvice, StockAdviceContext


SAFETY_NOTICE = "交易決策輔助，不是保證獲利或下單指令。"
MODE_FAKE = "fake/demo"
MODE_REAL = "real LLM"
REAL_MODE_GUARD_ONLY_MESSAGE = "Real LLM execution is guard-only in Session G and cannot submit yet."
MODE_OPTIONS = (MODE_FAKE, MODE_REAL)
INPUT_UPLOAD = "upload JSON files"
INPUT_FOLDER = "folder path"
INPUT_OPTIONS = (INPUT_UPLOAD, INPUT_FOLDER)
TABLE_COLUMNS = (
    "rank",
    "stock_id",
    "stock_name",
    "grade",
    "recommendation",
    "confidence",
    "risk_flags_count",
    "data_quality_warnings_count",
    "was_blocked",
    "guardrail_reasons",
)
DETAIL_SECTION_TITLES = (
    "conclusion",
    "core_reasons",
    "bull_case",
    "bear_case",
    "entry_plan",
    "stop_loss",
    "take_profit",
    "invalidation",
    "next_session_confirmation",
    "data_quality_warnings",
)


@dataclass(frozen=True)
class RunGate:
    can_submit: bool
    estimated_llm_calls: int
    messages: tuple[str, ...]


@dataclass(frozen=True)
class AlphaEvaluationViewModel:
    actionable_candidate_count: int
    complete_followup_count: int
    alpha_hit_rate_5d_vs_market: float | None
    average_alpha_5d_pct: float | None
    source: str
    warning: str | None


def mode_options() -> tuple[str, str]:
    return MODE_OPTIONS


def load_folder_context_paths(folder_path: str, max_batch_size: int) -> tuple[list[str], list[str]]:
    if not folder_path.strip():
        return [], []

    folder = Path(folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        return [], [f"context folder not found: {folder_path}"]

    paths = sorted(str(path) for path in folder.glob("*.json"))
    messages: list[str] = []
    if len(paths) > max_batch_size:
        messages.append(f"context files limited from {len(paths)} to max batch size {max_batch_size}")
    return paths[:max_batch_size], messages


def persist_uploaded_contexts(
    uploaded_files: Iterable[Any],
    max_batch_size: int,
    cache_dir: str | Path | None = None,
) -> tuple[list[str], list[str]]:
    files = list(uploaded_files)
    selected = files[:max_batch_size]
    messages: list[str] = []
    if len(files) > max_batch_size:
        messages.append(f"uploaded files limited from {len(files)} to max batch size {max_batch_size}")
    if not selected:
        return [], messages

    target_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "ai_advisor_uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for uploaded in selected:
        content = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
        digest = sha256(content).hexdigest()[:12]
        safe_name = Path(getattr(uploaded, "name", "uploaded_context.json")).name
        target_path = target_dir / f"{digest}_{safe_name}"
        target_path.write_bytes(content)
        paths.append(str(target_path))
    return paths, messages


def estimate_valid_context_count(context_paths: list[str]) -> tuple[int, list[str]]:
    valid_count = 0
    messages: list[str] = []
    for context_path in context_paths:
        try:
            data = json.loads(Path(context_path).read_text(encoding="utf-8"))
            StockAdviceContext.model_validate(data)
        except Exception as exc:
            messages.append(f"{Path(context_path).name}: invalid context excluded from real LLM estimate ({exc})")
        else:
            valid_count += 1
    return valid_count, messages


def build_run_gate(
    mode: str,
    context_paths: list[str],
    max_llm_calls_per_run: int,
    api_key: str | None,
) -> RunGate:
    if mode != MODE_REAL:
        return RunGate(can_submit=True, estimated_llm_calls=0, messages=())

    estimated_llm_calls, validation_messages = estimate_valid_context_count(context_paths)
    messages = [f"estimated_llm_calls = {estimated_llm_calls}", *validation_messages, REAL_MODE_GUARD_ONLY_MESSAGE]
    if not api_key:
        messages.append("OPENAI_API_KEY is required for real LLM mode")
    if estimated_llm_calls > max_llm_calls_per_run:
        messages.append(
            f"estimated_llm_calls exceeds max_llm_calls_per_run ({max_llm_calls_per_run}); submission blocked"
        )

    return RunGate(
        can_submit=False,
        estimated_llm_calls=estimated_llm_calls,
        messages=tuple(messages),
    )


def run_batch(
    mode: str,
    context_paths: list[str],
    append_log: bool = True,
) -> list[RankedStockAdvice]:
    if mode == MODE_REAL:
        raise NotImplementedError("Real LLM execution awaits the core LLM client; Session G only guards the UI boundary.")

    outputs = generate_stock_batch_advice(context_paths, append_log=append_log)
    return rank_stock_advices(outputs)


def apply_ranked_filters(
    ranked_advices: list[RankedStockAdvice],
    selected_grades: Iterable[str],
    selected_recommendations: Iterable[str],
    show_blocked_rows: bool,
) -> list[RankedStockAdvice]:
    grade_set = set(selected_grades)
    recommendation_set = set(selected_recommendations)
    return [
        row
        for row in ranked_advices
        if (show_blocked_rows or not row.was_blocked)
        and (not grade_set or row.grade in grade_set)
        and (not recommendation_set or row.recommendation in recommendation_set)
    ]


def ranked_table_rows(ranked_advices: list[RankedStockAdvice]) -> list[dict[str, Any]]:
    return [
        {
            "rank": row.rank,
            "stock_id": row.stock_id,
            "stock_name": row.stock_name,
            "grade": row.grade,
            "recommendation": row.recommendation,
            "confidence": row.confidence,
            "risk_flags_count": row.risk_flags_count,
            "data_quality_warnings_count": row.data_quality_warnings_count,
            "was_blocked": row.was_blocked,
            "guardrail_reasons": " | ".join(row.guardrail_reasons),
        }
        for row in ranked_advices
    ]


def batch_summary_metrics(ranked_advices: list[RankedStockAdvice]) -> dict[str, int]:
    return {
        "total_rows": len(ranked_advices),
        "actionable_candidates": sum(1 for row in ranked_advices if is_actionable_candidate(row)),
        "blocked_rows": sum(1 for row in ranked_advices if row.was_blocked),
        "grade_a_or_b": sum(1 for row in ranked_advices if row.grade in {"A", "B"} and not row.was_blocked),
    }


def is_actionable_candidate(row: RankedStockAdvice) -> bool:
    return (
        row.was_blocked is False
        and row.grade in {"A", "B"}
        and row.recommendation in {"wait_pullback", "small_probe"}
    )


def stock_detail_sections(output: GuardedAdviceOutput) -> dict[str, list[str]]:
    advice = output.final_advice
    result = output.guardrail_result
    return {
        "conclusion": [
            f"{advice.grade} / {advice.recommendation} / confidence {advice.confidence}",
            advice.summary,
        ],
        "core_reasons": result.reasons or ["No guardrail downgrade or block reasons."],
        "bull_case": advice.bull_case,
        "bear_case": advice.bear_case,
        "entry_plan": advice.entry_conditions,
        "stop_loss": advice.stop_loss_plan,
        "take_profit": advice.take_profit_plan,
        "invalidation": advice.invalidation_conditions,
        "next_session_confirmation": advice.next_session_confirmation,
        "data_quality_warnings": advice.data_quality_warnings,
    }


def alpha_evaluation_view_model(
    ranked_advices: list[RankedStockAdvice],
    evaluation_log_path: str | Path = DEFAULT_CONFIG.evaluation_log_path,
) -> AlphaEvaluationViewModel:
    actionable_count = sum(1 for row in ranked_advices if is_actionable_candidate(row))
    records = read_existing_evaluation_records(evaluation_log_path)
    denominator_records = [
        record
        for record in records
        if record.get("included_in_alpha_denominator") is True
        and record.get("alpha_hit_5d") is not None
        and record.get("alpha_5d_pct") is not None
    ]

    if not denominator_records:
        return AlphaEvaluationViewModel(
            actionable_candidate_count=actionable_count,
            complete_followup_count=0,
            alpha_hit_rate_5d_vs_market=None,
            average_alpha_5d_pct=None,
            source="placeholder",
            warning="Follow-up CSV calculation is intentionally deferred to Session H.",
        )

    hits = sum(1 for record in denominator_records if record["alpha_hit_5d"] is True)
    alpha_values = [float(record["alpha_5d_pct"]) for record in denominator_records]
    return AlphaEvaluationViewModel(
        actionable_candidate_count=actionable_count,
        complete_followup_count=len(denominator_records),
        alpha_hit_rate_5d_vs_market=hits / len(denominator_records),
        average_alpha_5d_pct=sum(alpha_values) / len(alpha_values),
        source=str(evaluation_log_path),
        warning="Displayed from existing evaluation log only; CSV calculation remains Session H scope.",
    )


def read_existing_evaluation_records(evaluation_log_path: str | Path) -> list[dict[str, Any]]:
    path = Path(evaluation_log_path)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def render_app(streamlit_module: Any | None = None) -> None:
    ui = streamlit_module or st
    if ui is None:
        raise RuntimeError("streamlit is required to run apps/ai_advisor_streamlit.py")

    ui.set_page_config(page_title="AI Advisor v1.2", layout="wide")
    ui.title("AI Advisor v1.2")
    ui.warning(SAFETY_NOTICE)

    with ui.sidebar:
        ui.warning(SAFETY_NOTICE)
        mode = ui.radio("mode", MODE_OPTIONS, index=0)
        input_mode = ui.radio("context input", INPUT_OPTIONS, index=1)
        max_batch_size = int(
            ui.number_input(
                "max batch size",
                min_value=1,
                max_value=DEFAULT_CONFIG.max_stocks_per_run,
                value=min(20, DEFAULT_CONFIG.max_stocks_per_run),
                step=1,
            )
        )
        show_blocked_rows = ui.checkbox("show blocked rows", value=True)
        followup_csv = ui.file_uploader("follow-up CSV uploader", type=["csv"])

    context_paths, input_messages = _resolve_context_paths(ui, input_mode, max_batch_size)
    for message in input_messages:
        ui.info(message)

    run_gate = build_run_gate(
        mode=mode,
        context_paths=context_paths,
        max_llm_calls_per_run=DEFAULT_CONFIG.max_llm_calls_per_run,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    if mode == MODE_REAL:
        for message in run_gate.messages:
            ui.info(message)
        ui.warning(REAL_MODE_GUARD_ONLY_MESSAGE)

    run_disabled = not run_gate.can_submit
    if ui.button("Run batch advice", disabled=run_disabled):
        if not context_paths:
            ui.error("Provide at least one context JSON file or folder path before running.")
        else:
            try:
                ui.session_state["ranked_advices"] = run_batch(mode, context_paths)
            except Exception as exc:
                ui.error(str(exc))

    ranked_advices = ui.session_state.get("ranked_advices", [])
    _render_main_views(ui, ranked_advices, show_blocked_rows, followup_csv)


def _resolve_context_paths(ui: Any, input_mode: str, max_batch_size: int) -> tuple[list[str], list[str]]:
    if input_mode == INPUT_FOLDER:
        folder_path = ui.text_input("folder path", value="")
        return load_folder_context_paths(folder_path, max_batch_size)

    uploaded_files = ui.file_uploader("upload JSON files", type=["json"], accept_multiple_files=True)
    return persist_uploaded_contexts(uploaded_files or [], max_batch_size)


def _render_main_views(
    ui: Any,
    ranked_advices: list[RankedStockAdvice],
    show_blocked_rows: bool,
    followup_csv: Any | None,
) -> None:
    batch_tab, detail_tab, alpha_tab = ui.tabs(["Batch Results", "Stock Detail", "Alpha Evaluation"])
    with batch_tab:
        _render_batch_results(ui, ranked_advices, show_blocked_rows)
    with detail_tab:
        _render_stock_detail(ui, ranked_advices)
    with alpha_tab:
        _render_alpha_evaluation(ui, ranked_advices, followup_csv)


def _render_batch_results(ui: Any, ranked_advices: list[RankedStockAdvice], show_blocked_rows: bool) -> None:
    ui.subheader("Batch Results")
    summary = batch_summary_metrics(ranked_advices)
    cols = ui.columns(4)
    cols[0].metric("rows", summary["total_rows"])
    cols[1].metric("actionable candidates", summary["actionable_candidates"])
    cols[2].metric("blocked rows", summary["blocked_rows"])
    cols[3].metric("A/B unblocked", summary["grade_a_or_b"])

    selected_grades = ui.multiselect("grade filter", ["A", "B", "C", "Reject"], default=["A", "B", "C", "Reject"])
    selected_recommendations = ui.multiselect(
        "recommendation filter",
        ["small_probe", "wait_pullback", "observe", "avoid_chasing", "reject"],
        default=["small_probe", "wait_pullback", "observe", "avoid_chasing", "reject"],
    )
    filtered = apply_ranked_filters(ranked_advices, selected_grades, selected_recommendations, show_blocked_rows)
    ui.dataframe(ranked_table_rows(filtered), use_container_width=True)


def _render_stock_detail(ui: Any, ranked_advices: list[RankedStockAdvice]) -> None:
    ui.subheader("Stock Detail")
    if not ranked_advices:
        ui.info("Run a batch to inspect one stock plan.")
        return

    options = [f"{row.rank}. {row.stock_id} {row.stock_name}" for row in ranked_advices]
    selected_label = ui.selectbox("stock", options)
    selected_index = options.index(selected_label)
    selected = ranked_advices[selected_index].guarded_advice
    sections = stock_detail_sections(selected)
    for title in DETAIL_SECTION_TITLES:
        ui.markdown(f"**{title.replace('_', ' ').title()}**")
        values = sections[title]
        if values:
            for value in values:
                ui.write(value)
        else:
            ui.write("None")


def _render_alpha_evaluation(ui: Any, ranked_advices: list[RankedStockAdvice], followup_csv: Any | None) -> None:
    ui.subheader("Alpha Evaluation")
    view_model = alpha_evaluation_view_model(ranked_advices)
    cols = ui.columns(4)
    cols[0].metric("actionable candidate count", view_model.actionable_candidate_count)
    cols[1].metric("complete follow-up count", view_model.complete_followup_count)
    hit_rate = (
        "pending"
        if view_model.alpha_hit_rate_5d_vs_market is None
        else f"{view_model.alpha_hit_rate_5d_vs_market:.1%}"
    )
    avg_alpha = "pending" if view_model.average_alpha_5d_pct is None else f"{view_model.average_alpha_5d_pct:.2f}%"
    cols[2].metric("alpha hit rate", hit_rate)
    cols[3].metric("average alpha_5d_pct", avg_alpha)
    ui.info(view_model.warning or f"source: {view_model.source}")
    if followup_csv is not None:
        ui.warning("CSV received but not processed in Session G; follow-up calculation is reserved for Session H.")


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
