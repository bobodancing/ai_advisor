# AI Advisor Release Notes v1.2.1

Release version: `v1.2.1`

Release commit: `93625075ba0b502f4fe809cbf1ecd348c9097146`

Release date: 2026-05-24

## Release Scope Summary

v1.2.1 closes the AI Advisor v1.2 release hardening loop and makes the MVP ready for a first personal after-market pilot.

This release is documentation and release governance focused. It preserves the v1.2 product contract:

- deterministic stock-only batch advice,
- fake/demo mode as the release validation path,
- real LLM mode as guard-only,
- fixed guardrails and ranking,
- append-only advice and evaluation JSONL logs,
- 5-trading-day alpha evaluation from user-provided follow-up CSV.

No product behavior, schema, ranking, guardrail threshold, logging contract, benchmark mapping, or evaluation denominator was changed for this release closure.

## Included Capabilities

- Streamlit batch stock advice page.
- Loading multiple structured `StockAdviceContext` JSON files.
- Fixture folder flow for 20+ stock contexts.
- Stable fake/demo advice generation.
- Deterministic balanced guardrails.
- Fixed candidate ranking.
- Row-level failure handling.
- Batch Results, Stock Detail, and Alpha Evaluation views.
- Immutable advice snapshot JSONL creation.
- Separate append-only follow-up evaluation JSONL creation.
- Follow-up CSV evaluation for 5-trading-day alpha versus market benchmark.
- GitHub Actions CI installing `requirements.txt` and running the full relevant pytest suite.
- Release UAT checklist and first pilot runbook.

## Explicit Non-Goals

The following are not part of v1.2.1:

- Real LLM API execution or provider integration.
- Daily AI Advice.
- Risk Review.
- Market data download.
- Auto order execution.
- Trading calendar inference.
- Database or multi-user platform work.
- Phase 2 feature implementation.

Real LLM mode remains guard-only: API key check, estimated call count, max-call guard, and disabled submission behavior only.

## Verification Summary

Local verification:

- `python -m pip install -r requirements.txt`
- `pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py`
- Result from release closure: full relevant pytest suite passed with 30 tests.

GitHub Actions:

- `main` run for commit `93625075ba0b502f4fe809cbf1ecd348c9097146`: success.
- `v1.2.1` tag run for commit `93625075ba0b502f4fe809cbf1ecd348c9097146`: success.

Streamlit manual UAT:

- Fake/demo fixture folder flow inspected.
- Batch Results inspected.
- Stock Detail inspected.
- Alpha Evaluation inspected.
- Real LLM guard-only UI inspected with estimated calls, missing API key warning, and disabled submission.

Log hygiene:

- `reports/ai_advice/` contains only `.gitkeep` in the committed repository.
- Generated `.jsonl` advice and evaluation logs remain local artifacts and must not be committed.

## Known Low Risks

- GitHub Actions reports a Node.js 20 actions deprecation warning for the current action versions. This is Low risk and does not block v1.2.1.
- Follow-up CSV browser upload was not manually verified in the release hardening browser pass; automated evaluator and Streamlit smoke tests cover the follow-up CSV path.
