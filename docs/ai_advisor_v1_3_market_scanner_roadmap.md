# AI Advisor v1.3 Market Data Scanner Roadmap

Project: Market Data Scanner / Context Generator

Roadmap owner: PM + Codex

Status: draft, pending human-gated source decisions

---

## 1. Objective

Build the upstream module that creates `StockAdviceContext` JSON folders when the trader has no CSV and no prepared context folder.

The scanner must preserve the AI Advisor product boundary:

```text
market data scanner
-> context JSON folder
-> existing Streamlit AI Advisor
```

It must not change advice guardrails, ranking, logging, benchmark mapping, alpha denominator, or Real LLM scope.

---

## 2. Gate 0 - Human Decisions

Before implementation:

- resolve `HP-001`: product direction data source,
- resolve `HP-002`: first implementation adapter path,
- record decisions in `docs/market_data_source_decision.md`,
- keep risks in `docs/market_data_scanner_risk_register.md`.

Recommended default:

```text
product direction: official TWSE / TPEx after-market public data
first implementation: local raw market-data file adapter, then official downloader
```

---

## 3. Milestones

| Milestone | Owner | Exit Criteria |
|---|---|---|
| M0 - Source Decision | PM | `humanpending.md` decisions resolved and ADR updated |
| M1 - Local Raw Adapter | Codex | local daily stock/benchmark files load into typed records; source-contract tests pass |
| M2 - Indicators | Codex | MA, volume ratio, relative strength, market regime tests pass |
| M3 - Context Writer | Codex | generated JSON validates as `StockAdviceContext`; theme/leader fallback tested |
| M4 - Scanner Filter / Score | Codex + PM | hard skip vs penalty rules tested; at least 20 fixture contexts generated |
| M5 - Streamlit Integration Check | Codex | generated folder loads through existing v1.2 Streamlit flow |
| M6 - Official Downloader Spike | Codex | current TWSE / TPEx source behavior verified; no brittle scraping accepted |

---

## 4. Acceptance Commands

Expected first implementation tests:

```bash
pytest tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner.py
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_streamlit_smoke.py
```

Full relevant set after integration:

```bash
pytest tests/test_ai_advisor_schemas.py \
       tests/test_ai_advisor_guardrails.py \
       tests/test_ai_advisor_batch.py \
       tests/test_ai_advisor_evaluator.py \
       tests/test_ai_advisor_streamlit_smoke.py \
       tests/test_ai_advisor_market_scanner_indicators.py \
       tests/test_ai_advisor_market_scanner.py
```

---

## 5. No-Go Criteria

- scanner fabricates missing market facts,
- scanner changes advice ranking or guardrails,
- scanner mutates advice/evaluation logs,
- scanner relies on LLM ranking,
- downloader is implemented before source behavior is verified,
- fewer than 20 contexts are produced without clear warning and skip/penalty summary,
- `theme.*` or `leader_status.*` fallback is not deterministic.
