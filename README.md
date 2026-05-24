# AI Advisor v1.2

AI Advisor v1.2 is a Streamlit 批次個股 Alpha Finder for personal Taiwan stock review after market close.

The module loads structured `StockAdviceContext` JSON files, generates deterministic fake/demo stock advice, applies balanced guardrails, ranks candidates, logs immutable advice snapshots, and evaluates 5-trading-day alpha against the correct benchmark through follow-up CSV data.

It is not an autonomous trading bot, public advisory service, market data downloader, or real-time monitoring system.

## Release / Pilot

- Release notes: [docs/release_notes_v1_2_1.md](docs/release_notes_v1_2_1.md)
- First pilot runbook: [docs/first_pilot_runbook.md](docs/first_pilot_runbook.md)

## Install

Use Python 3.11 or a compatible local Python environment.

```bash
python -m pip install -r requirements.txt
```

## Run Streamlit

```bash
python -m streamlit run apps/ai_advisor_streamlit.py
```

The app is the primary v1.2 entry point. It shows the required safety notice:

```text
交易決策輔助，不是保證獲利或下單指令。
```

## Fixture Folder Flow

For local demo and UAT, use the bundled fixture folder:

```text
tests/fixtures/ai_advisor/stock_contexts
```

In the Streamlit sidebar:

1. Select `fake/demo`.
2. Select `folder path`.
3. Enter `tests/fixtures/ai_advisor/stock_contexts`.
4. Keep `max batch size` at 20 or higher.
5. Click `Run batch advice`.
6. Review `Batch Results`, select a stock under `Stock Detail`, and check `Alpha Evaluation`.

## Fake/Demo Mode

Fake/demo mode is the v1.2 development and release validation path.

- It does not call external LLM APIs.
- It produces stable fixture-friendly output.
- It still runs schema validation, deterministic guardrails, ranking, and logging behavior.

## Real LLM Mode

Real LLM mode is guard-only in v1.2.

- The UI checks `OPENAI_API_KEY`.
- It calculates and displays `estimated_llm_calls`.
- It blocks submission when calls exceed `max_llm_calls_per_run`.
- It does not call a real LLM API and has no provider execution wired in v1.2.

Real LLM execution/provider integration remains deferred to Phase 2 / v1.3 in `docs/phase2_backlog.md`.

## Follow-Up CSV

Use follow-up CSV data after the 5th trading day close. v1.2 does not infer trading calendars.

Required columns:

```csv
stock_id,advice_date,close_5d,benchmark_return_5d_pct
3017,2026-05-23,130.0,1.2
```

Streamlit flow:

1. Generate or load a batch so `reports/ai_advice/ai_advice_log.jsonl` exists.
2. Upload a follow-up CSV in the sidebar.
3. Open `Alpha Evaluation`.
4. Click `Process follow-up CSV`.
5. Confirm alpha summary metrics update.

Evaluation appends records to:

```text
reports/ai_advice/ai_advice_evaluation.jsonl
```

It must not rewrite or mutate:

```text
reports/ai_advice/ai_advice_log.jsonl
```

Main alpha denominator includes only actionable candidates:

```text
grade in ["A", "B"]
recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
```

`observe` rows are excluded from the main alpha hit-rate denominator.

## Tests

Release hardening command:

```bash
python -m pip install -r requirements.txt
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py
```

Narrow acceptance commands:

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
pytest tests/test_ai_advisor_streamlit_smoke.py
pytest tests/test_ai_advisor_evaluator.py
```

## Secrets And Generated Logs

Do not commit secrets or generated JSONL logs.

`.gitignore` must exclude:

```text
.env
.env.*
secrets.json
reports/ai_advice/*.jsonl
```

Generated advice and evaluation logs are local release/UAT artifacts only.
