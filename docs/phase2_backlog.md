# Phase 2 Backlog

- Daily AI Advice
- Risk Review
- Market data downloading and trading calendar inference
  - Market Data Scanner / Context Generator is now the primary Phase 2 / v1.3 candidate because the user has no CSV or context folder.
  - See `docs/market_data_scanner_v1_3_plan.md`.
  - Roadmap: `docs/ai_advisor_v1_3_market_scanner_roadmap.md`.
  - Source ADR: `docs/market_data_source_decision.md`.
  - Risk register: `docs/market_data_scanner_risk_register.md`.
  - First version should use read-only after-market market data, deterministic indicators, deterministic filters, and `StockAdviceContext` JSON output.
  - Do not implement intraday monitoring, auto trading, or LLM-generated ranking.
- Sector benchmark alpha
- Human feedback UI
- Trade plan version comparison
- Multi-provider support
- Real LLM API execution / provider integration
  - Implement a real OpenAI-backed advice client only after v1.2 Go/No-Go.
  - Preserve existing guards: `OPENAI_API_KEY` check, `estimated_llm_calls`, `max_llm_calls_per_run`, and row-level failure isolation.
  - Raw LLM output must still pass `StockAdviceOutput` schema validation and deterministic guardrails before display.
