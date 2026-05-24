# Phase 2 Backlog

- Daily AI Advice
- Risk Review
- Market data downloading and trading calendar inference
- Sector benchmark alpha
- Human feedback UI
- Trade plan version comparison
- Multi-provider support
- Real LLM API execution / provider integration
  - Implement a real OpenAI-backed advice client only after v1.2 Go/No-Go.
  - Preserve existing guards: `OPENAI_API_KEY` check, `estimated_llm_calls`, `max_llm_calls_per_run`, and row-level failure isolation.
  - Raw LLM output must still pass `StockAdviceOutput` schema validation and deterministic guardrails before display.
