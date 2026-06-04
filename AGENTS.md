# AI Advisor — Codex Operating Contract

This is the compact governance file for Codex in this repository.

Read this first. Then read the task-relevant source documents:

- `README.md`
- `ai_advisor_module_spec_v1_2_product_ready.md`
- `humanpending.md`
- v1.2 release/UAT docs when touching advice, Streamlit, logs, or evaluation
- v1.3 scanner docs when touching `market_scanner`

If this file and a detailed spec appear to conflict, follow the stricter, more deterministic, more audit-preserving rule and report the conflict.

---

## 1. Mission

AI Advisor is a personal Taiwan stock after-market decision-support module.

The product loop is:

```text
market data / user input
-> StockAdviceContext JSON folder
-> deterministic or guarded advice generation
-> deterministic guardrails
-> fixed ranking
-> Streamlit inspection
-> append-only advice JSONL
-> follow-up CSV
-> append-only evaluation JSONL
-> 5-trading-day alpha review
```

The product succeeds only if it improves:

```text
candidate discovery speed
+
alpha evaluation integrity
```

This is not an autonomous trading bot, public advisory service, live intraday monitor, markdown parser, database product, or general finance chatbot.

Safety wording must remain visible in user-facing flows:

```text
交易決策輔助，不是保證獲利或下單指令。
```

---

## 2. Current Product State

- v1.2.3 is sealed.
- v1.2 primary product is Streamlit batch stock Alpha Finder.
- v1.2 supports fake/demo batch advice, deterministic guardrails, fixed ranking, JSONL advice logging, follow-up CSV evaluation, CI, README, and UAT docs.
- v1.2 Real LLM mode is guard-only: API key check, estimated calls, and max-call guard. No provider execution is approved.
- v1.3 Market Scanner is an upstream context generator. Its boundary is:

```text
local/official-format market data
-> deterministic scanner
-> StockAdviceContext JSON folder
-> existing Streamlit AI Advisor
```

- Production downloader remains No-Go until explicitly approved after pilot retrospective.
- One-shot official pilot data prep helper is allowed only as HP-003 pilot exception; it is not production downloader approval.

When an official pilot advice log is active, do not rerun Streamlit batch before follow-up evaluation unless the user explicitly starts a new pilot. Reruns append duplicate advice snapshots and can pollute pilot accounting.

---

## 3. Non-Negotiable Priorities

Priority order:

```text
correctness
> reproducibility
> auditability
> scope control
> trader workflow speed
> implementation elegance
> AI cleverness
```

Do not silently change:

- schema semantics
- guardrail thresholds
- grade/recommendation compatibility
- ranking order
- benchmark mapping
- advice/evaluation JSONL semantics
- alpha denominator
- Real LLM scope
- scanner fallback semantics

If a request violates these, push back once with evidence and offer a safer alternative. If the user explicitly confirms the change, document the scope change and update the relevant spec/docs.

---

## 4. Codex Workflow

Before editing, identify the touched contract:

- schema
- guardrails
- ranking
- logging
- evaluation
- benchmark
- Streamlit UX
- LLM boundary
- scanner
- security/secrets
- docs/governance

Then make the smallest reversible change that satisfies the contract.

Use deterministic code and tests for product behavior. Prompt text may guide an LLM, but cannot be the only enforcement for validation, guardrails, ranking, logging, benchmark defaults, hallucination blocking, or alpha denominator rules.

Use `rg` / `rg --files` for search. Use `apply_patch` for manual edits. Do not revert unrelated user changes. Do not use destructive git commands unless the user explicitly asks.

Run the narrowest relevant test first, then expand when risk warrants it. Do not claim success from inspection alone.

Final reports must include:

```text
Summary
- What changed.

Verification
- [executed] exact commands run
- [inspected] files reviewed
- [assumed] anything not verified

Contract Impact
- Schema / guardrails / ranking / logging / evaluation / UI / config / scanner / docs

Notes
- Blockers, residual risk, or Phase 2 items.
```

---

## 5. Scope Boundaries

Allowed in v1.2:

- Streamlit batch stock advice page
- structured `StockAdviceContext` JSON input
- fake/demo mode
- Real LLM guard UI without provider execution
- deterministic guardrails and fixed ranking
- row-level failure handling
- append-only advice JSONL
- separate append-only evaluation JSONL
- follow-up CSV alpha evaluation

Allowed in v1.3 scanner:

- local official-format raw file adapter
- deterministic indicators
- deterministic filters, scoring, and context writing
- scanner CLI/API reading four aggregate local raw files
- one-shot pilot data prep helper under HP-003 only
- generated `StockAdviceContext` JSON loaded by existing Streamlit flow

Not allowed unless explicitly approved:

- auto trading
- intraday monitoring
- public investment advisory language
- trading-calendar inference inside v1.2 evaluation
- yfinance or unofficial market-data shortcut
- production downloader, scheduler, scraping, or hidden network fetch
- database/auth/vector DB/agent framework
- LLM-generated scanner ranking
- Real LLM provider execution
- changing v1.2 guardrails, ranking, logging, evaluation denominator, or benchmark mapping from scanner work

Put Phase 2 ideas only in `docs/phase2_backlog.md`; do not implement them opportunistically.

---

## 6. Human-Gated Decisions

Use `humanpending.md` only for true product gates, such as:

- changing alpha denominator
- changing ranking order
- changing guardrail thresholds
- changing log schema
- adding production market-data downloading
- adding a database
- changing benchmark mapping
- changing v1.2/v1.3 scope
- implementing auto trading

Continue all non-dependent work. Each open item must have a clear blocked area, options, recommended default, and status: `open`, `resolved`, or `obsolete`.

Current resolved decisions:

- HP-001 = A: long-term source direction is official TWSE / TPEx after-market public data.
- HP-002 = B: first implementation is local raw file adapter, then downloader after source behavior is verified.
- HP-003 = B: one-shot official data prep helper allowed for pilot only, not production downloader approval.

---

## 7. Data Contract

v1.2 input is structured UTF-8 JSON only. Do not parse Markdown contexts.

Required `StockAdviceContext` fields:

```text
date
stock.stock_id
stock.name
stock.close
stock.change_pct
stock.volume_ratio_20d
market_regime.risk_state
theme.name
theme.rank
theme.score
theme.lifecycle
leader_status.leader_rank
technical.position
technical.is_overheated
risk.invalid_level
risk.risk_reward_ratio
```

Recommended fields:

```text
market_type
benchmark_symbol
technical.is_limit_up
risk.nearest_support
risk.planned_target
data_source_notes
scanner_metadata
```

If `market_type` is missing or `unknown`:

- set `market_type = "unknown"`
- default `benchmark_symbol = "TAIEX"`
- add a data quality warning
- exception: preserve an explicitly valid `benchmark_symbol` of `TAIEX` or `OTC`, while still warning about unknown market type

Benchmark mapping:

```text
listed  -> TAIEX
otc     -> OTC
missing -> TAIEX + warning
unknown -> TAIEX + warning unless valid benchmark_symbol is explicit
```

Never infer benchmark from stock id unless the spec is updated.

Key enums:

```text
market_type: listed / otc / unknown
benchmark_symbol: TAIEX / OTC / unknown
risk_state: risk_on / neutral / risk_off
theme.lifecycle: early / main_uptrend / late_stage / fading / broken / unknown
leader_rank: leader_1 / leader_2 / follower / laggard / unknown
technical.position: breakout / pullback_to_ma5 / pullback_to_ma10_and_rebound / near_ma20_support / extended_above_ma / breakdown / range_bound / unknown
recommendation: observe / wait_pullback / small_probe / avoid_chasing / reject
grade: A / B / C / Reject
```

`StockAdviceOutput` must validate before guardrails and include recommendation, grade, confidence, summary, bull/bear cases, entry, stop, take-profit, invalidation, confirmation, risk flags, evidence, and data quality warnings.

Render only `GuardedAdviceOutput.final_advice` as final user-facing advice. Preserve raw advice for audit.

---

## 8. Guardrail Contract

Grade/recommendation compatibility:

```text
A       -> wait_pullback or small_probe only
B       -> observe / wait_pullback / small_probe
C       -> observe / wait_pullback / avoid_chasing only
Reject  -> avoid_chasing / reject only
```

Recommendation meanings:

```text
observe        = watch only, no trade plan yet
wait_pullback  = wait for pullback, do not chase
small_probe    = small position allowed only with trigger and stop
avoid_chasing  = do not chase; risk/quality too poor or overheated
reject         = discard; data or risk condition fails
```

Balanced guardrails:

- missing required data: final grade <= C, recommendation in `observe` / `avoid_chasing` / `reject`, confidence <= 60, and warnings list missing fields
- missing `risk.invalid_level`, `risk.risk_reward_ratio`, `technical.position`, `theme.lifecycle`, or `market_regime.risk_state`: `small_probe` forbidden
- A requires `risk_reward_ratio >= 2.0`
- `small_probe` requires `risk_reward_ratio >= 1.5`
- `technical.is_overheated == true` forbids `small_probe`
- `theme.lifecycle == late_stage` forbids A but may allow `wait_pullback`
- `theme.lifecycle in fading / broken` becomes `avoid_chasing` or `reject`
- `risk.invalid_level is null` forbids positive advice
- `market_regime.risk_state == risk_off` forbids A
- no-chase downgrade applies when `technical.position == extended_above_ma`, `technical.is_limit_up == true`, or `stock.change_pct >= 7`

Restricted unsupported-claim terms:

```text
新聞 / 法人 / 外資 / 投信 / 營收 / EPS / 目標價 / 財報 / 訂單
```

If advice uses these without matching evidence in context:

- `hallucination_suspected = true`
- `was_blocked = true`
- reason must name the unsupported term

Every downgrade or block needs an explicit reason.

---

## 9. Batch And Ranking Contract

Required interfaces:

```python
def generate_stock_batch_advice(context_paths: list[str]) -> list[GuardedAdviceOutput]: ...
def rank_stock_advices(outputs: list[GuardedAdviceOutput]) -> list[RankedStockAdvice]: ...
def update_followup_returns(advice_log_path: str, followup_csv_path: str, evaluation_log_path: str = "reports/ai_advice/ai_advice_evaluation.jsonl") -> AlphaSummary: ...
```

Single-file failures must become row-level blocked/error outputs, not batch crashes:

- context validation failed -> blocked row
- LLM request failed -> error row
- hallucination suspected -> blocked row

Ranking is fixed and stable:

```text
1. was_blocked == false first
2. grade: A > B > C > Reject
3. recommendation: small_probe > wait_pullback > observe > avoid_chasing > reject
4. confidence high to low
5. risk_flags count low to high
6. stock_id ascending
```

Do not replace this with model-generated ranking.

Required table columns:

```text
rank, stock_id, stock_name, grade, recommendation, confidence,
risk_flags_count, data_quality_warnings_count, was_blocked, guardrail_reasons
```

---

## 10. Logging And Evaluation Contract

There are two separate append-only JSONL logs:

```text
reports/ai_advice/ai_advice_log.jsonl
reports/ai_advice/ai_advice_evaluation.jsonl
```

Advice snapshots are immutable. At creation, alpha fields must be `null`. Normal evaluation must never rewrite, reorder, deduplicate, or mutate historical advice rows.

Evaluation records append to the evaluation log and are keyed by:

```text
stock_id + advice_date + input_context_hash
```

If multiple evaluations exist for the same key, consumers use the latest valid record by timestamp and report supersession. Do not rewrite older records.

Follow-up CSV format:

```csv
stock_id,advice_date,close_5d,benchmark_return_5d_pct
3017,2026-05-23,130.0,1.2
```

Computation:

```text
stock_return_5d_pct = (close_5d - advice_close) / advice_close * 100
alpha_5d_pct = stock_return_5d_pct - benchmark_return_5d_pct
alpha_hit_5d = alpha_5d_pct > 0
```

Main denominator includes only actionable candidates with complete follow-up:

```text
final_grade in ["A", "B"]
final_recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
benchmark_return_5d_pct present
```

`observe` is excluded. Missing benchmark return excludes the row and must surface a warning.

Do not infer trading calendars in v1.2. The CSV is assumed to already represent the 5th trading day close.

Historical JSONL rewrite is allowed only for an explicit migration/repair task with backup, migration note, before/after counts, raw advice preservation, and no silent denominator changes.

---

## 11. Streamlit Contract

Launch command:

```bash
python -m streamlit run apps/ai_advisor_streamlit.py
```

Required sidebar controls:

- mode: `fake/demo` / `real LLM`
- context input: upload JSON files / folder path
- max batch size
- show blocked rows
- follow-up CSV uploader

Required views:

- Batch Results: sorted table, filters, summary metrics
- Stock Detail: conclusion, reasons, bull/bear cases, entry, stop, take profit, invalidation, next-session confirmation, data quality warnings
- Alpha Evaluation: actionable count, complete follow-up count, alpha hit rate, average alpha

Real LLM mode must:

- check `OPENAI_API_KEY`
- show `estimated_llm_calls = number_of_valid_contexts`
- block runs above `max_llm_calls_per_run`
- not crash if key is missing
- not call a real provider in v1.2 unless explicitly promoted

Manual Streamlit verification requires starting the server, opening the local URL, inspecting required controls/views, stopping the server, and reporting as `[inspected]`.

---

## 12. Scanner v1.3 Contract

Scanner purpose:

```text
after-market raw data
-> deterministic features
-> deterministic candidate filter/score
-> validated StockAdviceContext JSON
```

Scanner must not:

- mutate `reports/ai_advice/*.jsonl`
- use LLM ranking
- fabricate themes, news, institutions, EPS, revenue, target prices, orders, or financial claims
- change advice guardrails/ranking/logging/evaluation/benchmark contracts
- implement production downloader without a new gate

Local raw scanner reads exactly four aggregate official-format files:

```text
listed stock daily
OTC stock daily
TAIEX benchmark
OTC benchmark
```

Deterministic scanner capabilities may include MA5/10/20/60, 20-day average volume, volume ratio, prior high/low, MA20 distance, RS20/RS60, and benchmark regime.

`market_scan` fallback rules:

- `theme.name = "market_scan"`
- `theme.rank = 999`
- `theme.score = 50`
- add data quality warning
- do not describe it as a real sector/theme
- scanner score/rank belongs in `scanner_metadata`, not `theme.*`

Risk/reward rules:

- `risk.planned_target` must come from structural market levels
- do not use `close + 2R` or other self-fulfilling formulas as primary target
- fallback proxy targets, if useful, belong only in notes/metadata and must not drive RR, hard skip, or ranking
- hard skip is for data validity or clearly unusable trade geometry
- trade-quality concerns should usually be penalty/warning, then downstream guardrails decide final advice

Scanner-only `risk_state = "unknown"` must not be written into v1.2 `StockAdviceContext.market_regime.risk_state`; insufficient regime data needs a deterministic skip/warning/block path before context writing.

---

## 13. Config And Secrets

Expected config path:

```text
config/ai_advisor.yaml
```

Generated logs and secrets must stay uncommitted:

```text
.env
.env.*
secrets.json
reports/ai_advice/*.jsonl
```

Never print API keys in logs, tests, Streamlit UI, or exception traces.

---

## 14. Testing Commands

Use the narrowest relevant command first:

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
pytest tests/test_ai_advisor_evaluator.py
pytest tests/test_ai_advisor_streamlit_smoke.py
pytest tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner_context_writer.py tests/test_ai_advisor_market_scanner_filter_score.py tests/test_ai_advisor_market_scanner_integration.py
```

Full relevant set:

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner_context_writer.py tests/test_ai_advisor_market_scanner_filter_score.py tests/test_ai_advisor_market_scanner_integration.py
```

Release hardening also installs dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

For docs-only governance edits, at minimum inspect diff and line count; run tests only if behavior, commands, or contracts are changed.

---

## 15. Review Stance

When asked to review, prioritize:

- future-data leakage
- evaluation pollution
- JSONL mutation
- denominator drift
- benchmark drift
- non-deterministic ranking/scoring
- scope creep
- fabricated evidence
- untested guardrail behavior
- Real LLM execution sneaking into guard-only scope
- production downloader sneaking in before approval

Report findings first by severity: High, Medium, Low. Then open questions, Go/No-Go, and next action.

---

## 16. Final Principle

Do not make AI sound smarter at the cost of auditability.

When uncertain, choose the path that preserves:

```text
determinism
+ auditability
+ batch workflow speed
+ alpha evaluation integrity
```
