# AI Advisor Release Notes v1.2.3

Release version: `v1.2.3`

Release commit: `23aa0d7bed8ec7706fd02aa6e6fa423042694817`

Release date: 2026-05-24

## Release Scope Summary

v1.2.3 is the official pilot-ready documentation artifact for AI Advisor v1.2.x.

It includes the v1.2 batch advice application plus release closure documentation, pilot runbook, and pilot log-handling guidance.

No product behavior, schema, guardrail threshold, ranking, logging contract, benchmark mapping, Real LLM execution, or alpha denominator was changed by the release documentation closure.

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
- Release UAT checklist.
- First pilot runbook.
- Dry-run vs official-pilot log-handling guidance.

## Explicit Non-Goals

The following are not part of v1.2.3 runtime:

- Real LLM API execution or provider integration.
- Daily AI Advice.
- Risk Review.
- Market data download.
- Market Data Scanner.
- Auto order execution.
- Trading calendar inference.
- Database or multi-user platform work.

## Known Follow-Up

The user does not currently have a `StockAdviceContext` folder or after-market CSV. The next product direction is Phase 2 / v1.3 Market Data Scanner planning, documented in:

- `docs/market_data_scanner_v1_3_plan.md`
- `docs/ai_advisor_v1_3_market_scanner_roadmap.md`
- `docs/market_data_source_decision.md`
- `docs/market_data_scanner_risk_register.md`

Market Data Scanner must remain upstream of AI Advisor and must not change v1.2 guardrails, ranking, logging, or alpha evaluation semantics.
