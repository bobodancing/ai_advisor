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

Real LLM API execution is not part of v1.2 UAT. Real mode only needs API key checking, call estimate, max-call guard, and guard-only UI behavior.

---

## 1. Preconditions

- `requirements.txt` exists and includes the runtime/test dependencies.
- `tests/fixtures/ai_advisor/stock_contexts/` contains at least 20 stock context JSON fixtures.
- `tests/fixtures/ai_advisor/followup_prices_valid.csv` exists.
- `reports/ai_advice/` contains no committed `.jsonl` logs.
- `.gitignore` excludes secrets and generated advice/evaluation JSONL logs.
- `OPENAI_API_KEY` is not required for fake/demo UAT.

---

## 2. Automated Checks

Run:

```bash
python -m pip install -r requirements.txt
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py
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

## 4. Real Mode Guard UAT

Verify without calling a real LLM API:

- missing `OPENAI_API_KEY` does not crash the app,
- `estimated_llm_calls` is visible,
- execution is blocked when calls exceed `max_llm_calls_per_run`,
- v1.2 real mode clearly remains guard-only,
- no real provider call is wired during release hardening.

---

## 5. Follow-Up CSV UAT

Using a generated advice log and `tests/fixtures/ai_advisor/followup_prices_valid.csv`, verify:

- follow-up CSV import is triggered by an explicit button/action,
- evaluation appends records to `reports/ai_advice/ai_advice_evaluation.jsonl`,
- `reports/ai_advice/ai_advice_log.jsonl` is not rewritten or mutated,
- `stock_return_5d_pct`, `benchmark_return_5d_pct`, `alpha_5d_pct`, and `alpha_hit_5d` are computed,
- `observe` is excluded from the main alpha denominator,
- rows missing `benchmark_return_5d_pct` are excluded and surfaced as warnings.

---

## 6. Go / No-Go Notes

Go requires:

- CI exists and covers dependency install plus the full relevant pytest set,
- README exists and is usable by a fresh construction session,
- automated checks pass,
- manual Streamlit flow is inspected,
- follow-up CSV evaluation preserves append-only log integrity,
- no High or Medium blocker remains.

No-Go if:

- deterministic guardrails are only enforced by prompts,
- ranking differs from `AGENTS.md`,
- evaluation mutates advice snapshots,
- alpha denominator includes `observe`,
- one failed stock breaks the whole batch,
- release hardening adds real LLM API execution without explicit scope approval.
