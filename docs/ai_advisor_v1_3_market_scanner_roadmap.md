# AI Advisor v1.3 Market Data Scanner Roadmap

Project: Market Data Scanner / Context Generator

Roadmap owner: PM + Codex

Status: Gate 0 resolved, M6 official source spike completed

Created: 2026-05-24

Target M1 start: 2026-05-25

Target scanner integration check: 2026-06-07

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

Resolved on 2026-05-24:

- `HP-001 = A`: product direction uses official TWSE / TPEx after-market public data.
- `HP-002 = B`: first implementation starts with local raw market-data file adapter, then adds official downloader after source behavior is verified.
- decisions are recorded in `docs/market_data_source_decision.md`.
- risks are tracked in `docs/market_data_scanner_risk_register.md`.

M1 may begin. The first implementation must use local raw official-format files and source-contract fixtures. Do not start with a live downloader.

---

## 3. Milestones

| Milestone | Deadline | Owner | Exit Criteria | Status |
|---|---:|---|---|---|
| M0 - Source Decision | 2026-05-24 | PM | `humanpending.md` decisions resolved and ADR updated | Done |
| M1 - Local Raw Adapter | 2026-05-27 | Codex | local daily stock/benchmark files load into typed records; source-contract tests pass | Done |
| M2 - Indicators | 2026-05-29 | Codex | MA, volume ratio, relative strength, market regime tests pass | Done |
| M3 - Context Writer | 2026-06-02 | Codex | generated JSON validates as `StockAdviceContext`; theme/leader fallback tested | Done |
| M4 - Scanner Filter / Score | 2026-06-05 | Codex + PM | hard skip vs penalty rules tested; at least 20 fixture contexts generated | Done |
| M5 - Streamlit Integration Check | 2026-06-07 | Codex | generated folder loads through existing v1.2 Streamlit flow | Done |
| M6 - Official Downloader Spike | 2026-06-12 | Codex | current TWSE / TPEx source behavior verified; no brittle scraping accepted | Done |

---

M5 was completed as automated integration/smoke verification. Manual Streamlit browser UAT has not been executed and remains for release/UAT or a later manual acceptance pass.

M6 was completed as source behavior verification only and recorded in `docs/market_data_source_spike_m6.md`. It did not implement a live downloader. The observed no-parameter OpenAPI candidates remain insufficient by themselves for MA60 / RS60 because stock feeds were observed as single-date snapshots and benchmark feeds were observed as current-month short series.

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
- scanner-only `risk_state = "unknown"` is written into v1.2 `StockAdviceContext.market_regime.risk_state`; insufficient regime data must skip or emit deterministic warning/block before context writing,
- `theme.*` or `leader_status.*` fallback is not deterministic.
