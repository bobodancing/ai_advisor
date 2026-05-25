# AI Advisor v1.2 Release UAT Checklist

Owner: PM + Codex
Target date: 2026-06-11
Release decision date: 2026-06-12

This checklist verifies the v1.2 product loop after Session F/G/H:

```text
20+ stock JSON fixtures
-> fake/demo batch advice
-> ranked Streamlit table
-> stock detail inspection
-> immutable advice JSONL
-> follow-up CSV import
-> append-only evaluation JSONL
-> 5-trading-day alpha summary
```

The v1.3 scanner pilot readiness path adds an upstream local-only loop:

```text
four aggregate local official-format raw files
-> market scanner CLI/API
-> 20+ generated StockAdviceContext JSON files
-> existing Streamlit fake/demo batch flow
-> ranked advice table
```

Real LLM API execution is not part of v1.2 UAT. Real mode only needs API key checking, call estimate, max-call guard, and guard-only UI behavior.

---

## 1. Preconditions

- `requirements.txt` exists and includes the runtime/test dependencies.
- `tests/fixtures/ai_advisor/stock_contexts/` contains at least 20 stock context JSON fixtures.
- `tests/fixtures/ai_advisor/followup_prices_valid.csv` exists.
- `reports/ai_advice/` contains no committed `.jsonl` logs.
- `.gitignore` excludes secrets and generated advice/evaluation JSONL logs.
- `OPENAI_API_KEY` is not required for fake/demo UAT.
- v1.3 scanner pilot raw inputs, when used, are four local aggregate official-format files with 60+ sessions: listed stock, OTC stock, TAIEX benchmark, and OTC benchmark.
- Scanner pilot input must be local files only; no live downloader, network fetch, or scraping is part of this UAT.

---

## 2. Automated Checks

Run:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
pytest tests/test_ai_advisor_schemas.py \
       tests/test_ai_advisor_guardrails.py \
       tests/test_ai_advisor_batch.py \
       tests/test_ai_advisor_evaluator.py \
       tests/test_ai_advisor_streamlit_smoke.py \
       tests/test_ai_advisor_market_scanner.py \
       tests/test_ai_advisor_market_scanner_indicators.py \
       tests/test_ai_advisor_market_scanner_context_writer.py \
       tests/test_ai_advisor_market_scanner_filter_score.py \
       tests/test_ai_advisor_market_scanner_integration.py
```

Expected:

- dependency install succeeds,
- full relevant pytest set passes,
- test execution does not leave generated JSONL logs under `reports/ai_advice/`.

---

## 3. Streamlit Manual Flow

Start the app:

```bash
python -m streamlit run apps/ai_advisor_streamlit.py
```

Verify:

- safety notice is visible: `交易決策輔助，不是保證獲利或下單指令。`
- sidebar has fake/demo mode and real LLM mode,
- fixture folder path can be entered,
- max batch size is visible,
- fake/demo run can process at least 20 fixtures,
- Batch Results table is visible and sorted,
- filters can hide/show blocked rows,
- one stock can be selected for Stock Detail,
- Stock Detail shows conclusion, reasons, bull case, bear case, entry, stop loss, take profit, invalidation, confirmation, and data quality warnings,
- Alpha Evaluation view is visible.

Stop the Streamlit server after inspection.

Report manual verification as `[inspected]`, not automated acceptance.

---

## 4. Scanner-Generated Context Folder UAT

This path is for the v1.3 scanner pilot only. It generates context JSON files from local raw official-format files, then uses the existing Streamlit fake/demo flow.

Run the scanner from the repository root:

```bash
python -m ai_advisor.market_scanner.scanner \
  --listed-stock-file data/raw_market/2026-05-24/listed_stock_daily.csv \
  --otc-stock-file data/raw_market/2026-05-24/otc_stock_daily.csv \
  --taiex-benchmark-file data/raw_market/2026-05-24/taiex_benchmark.csv \
  --otc-benchmark-file data/raw_market/2026-05-24/otc_benchmark.csv \
  --output data/pilot_contexts/2026-05-24 \
  --max-output 50
```

Verify:

- command reads only local files,
- no downloader, network fetch, or scraping occurs,
- generated folder contains at least 20 `StockAdviceContext` JSON files for a pilot-sized input set,
- each generated JSON validates through the automated scanner integration test,
- generated folder can be entered in the Streamlit sidebar as a `folder path`,
- fake/demo run produces a sorted `Batch Results` table.

Manual browser inspection of Streamlit remains a separate UAT step and should still be reported as `[inspected]`.

---

## 5. Real Mode Guard UAT

Verify without calling a real LLM API:

- missing `OPENAI_API_KEY` does not crash the app,
- `estimated_llm_calls` is visible,
- execution is blocked when calls exceed `max_llm_calls_per_run`,
- v1.2 real mode clearly remains guard-only,
- no real provider call is wired during release hardening.

---

## 6. Follow-Up CSV UAT

Using a generated advice log and `tests/fixtures/ai_advisor/followup_prices_valid.csv`, verify:

- follow-up CSV import is triggered by an explicit button/action,
- evaluation appends records to `reports/ai_advice/ai_advice_evaluation.jsonl`,
- `reports/ai_advice/ai_advice_log.jsonl` is not rewritten or mutated,
- `stock_return_5d_pct`, `benchmark_return_5d_pct`, `alpha_5d_pct`, and `alpha_hit_5d` are computed,
- `observe` is excluded from the main alpha denominator,
- rows missing `benchmark_return_5d_pct` are excluded and surfaced as warnings.

---

## 7. Go / No-Go Notes

Go requires:

- CI exists and covers dependency install, editable package install, and the full relevant pytest set including scanner tests,
- README exists and is usable by a fresh construction session,
- automated checks pass,
- manual Streamlit flow is inspected,
- follow-up CSV evaluation preserves append-only log integrity,
- scanner-generated context folder flow is inspected before a v1.3 scanner pilot,
- no High or Medium blocker remains.

No-Go if:

- deterministic guardrails are only enforced by prompts,
- ranking differs from `AGENTS.md`,
- evaluation mutates advice snapshots,
- alpha denominator includes `observe`,
- one failed stock breaks the whole batch,
- release hardening adds real LLM API execution without explicit scope approval.
- scanner pilot adds a downloader, network fetch, scraping, or one-file-per-date orchestration without explicit scope approval.
