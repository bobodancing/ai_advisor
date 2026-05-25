# AI Advisor v1.2

AI Advisor v1.2 is a Streamlit 批次個股 Alpha Finder for personal Taiwan stock review after market close.

The module loads structured `StockAdviceContext` JSON files, generates deterministic fake/demo stock advice, applies balanced guardrails, ranks candidates, logs immutable advice snapshots, and evaluates 5-trading-day alpha against the correct benchmark through follow-up CSV data.

It is not an autonomous trading bot, public advisory service, market data downloader, or real-time monitoring system.

## Release / Pilot

- Release notes: [docs/release_notes_v1_2_3.md](docs/release_notes_v1_2_3.md)
- First pilot runbook: [docs/first_pilot_runbook.md](docs/first_pilot_runbook.md)
- v1.3 scanner pilot runbook: [docs/market_scanner_pilot_runbook.md](docs/market_scanner_pilot_runbook.md)

The first official pilot should start from a clean or archived `reports/ai_advice` state.

## Install

Use Python 3.11 or a compatible local Python environment.

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
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

## Scanner-Generated Context Folder Flow

The v1.3 Market Scanner pilot can generate a `StockAdviceContext` folder from four local official-format raw files. It remains local-only and does not download, scrape, or fetch market data.

Required local raw input shape:

```text
listed stock daily raw file
OTC stock daily raw file
TAIEX benchmark raw file
OTC benchmark raw file
```

Each aggregate raw file should contain at least 60 sessions for the stocks or benchmark series used by the scanner pilot.

Example:

```bash
python -m ai_advisor.market_scanner.scanner \
  --listed-stock-file data/raw_market/2026-05-24/listed_stock_daily.csv \
  --otc-stock-file data/raw_market/2026-05-24/otc_stock_daily.csv \
  --taiex-benchmark-file data/raw_market/2026-05-24/taiex_benchmark.csv \
  --otc-benchmark-file data/raw_market/2026-05-24/otc_benchmark.csv \
  --output data/pilot_contexts/2026-05-24 \
  --max-output 50
```

Then load the generated output folder through the existing Streamlit fake/demo folder path flow:

```text
data/pilot_contexts/2026-05-24
```

See [docs/market_scanner_pilot_runbook.md](docs/market_scanner_pilot_runbook.md) for the local raw scanner pilot steps.

## No Context Folder Yet?

AI Advisor v1.2.x needs `StockAdviceContext` JSON files. It does not download market data by itself.

- If you have an after-market CSV, see the optional Scanner Lite plan: [docs/scanner_lite_context_builder_plan.md](docs/scanner_lite_context_builder_plan.md).
- If you have four local official-format aggregate raw files, use the v1.3 scanner pilot runbook: [docs/market_scanner_pilot_runbook.md](docs/market_scanner_pilot_runbook.md).
- If you need the system itself to obtain market data, that remains a later downloader task and is not part of this pilot: [docs/market_data_scanner_v1_3_plan.md](docs/market_data_scanner_v1_3_plan.md).
- v1.3 scanner roadmap: [docs/ai_advisor_v1_3_market_scanner_roadmap.md](docs/ai_advisor_v1_3_market_scanner_roadmap.md).

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
python -m pip install -e .
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner_context_writer.py tests/test_ai_advisor_market_scanner_filter_score.py tests/test_ai_advisor_market_scanner_integration.py
```

Narrow acceptance commands:

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
pytest tests/test_ai_advisor_streamlit_smoke.py
pytest tests/test_ai_advisor_evaluator.py
pytest tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner_context_writer.py tests/test_ai_advisor_market_scanner_filter_score.py tests/test_ai_advisor_market_scanner_integration.py
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
