# AI Advisor v1.2 — AGENTS.md

**Codex operating rules for `ai_advisor` — Streamlit 批次個股 Alpha Finder**

This file defines how Codex must work inside this project.

The goal is not to create a clever AI stock commentator.  
The goal is to build a deterministic, auditable, product-ready trading decision support module that helps a personal Taiwan stock trader quickly find actionable candidates after market close and later evaluate whether those candidates generated 5-trading-day alpha versus the correct market benchmark.

---

## 0. Project Mission

`ai_advisor` is a personal trading cockpit module.

It helps the user:

1. Load many structured `StockAdviceContext` JSON files.
2. Generate stock-only trade advice in fake/demo mode or real LLM mode.
3. Apply deterministic balanced guardrails.
4. Rank candidates using fixed ordering rules.
5. Inspect each stock's final trade plan in Streamlit.
6. Append immutable advice snapshots to JSONL logs.
7. Import follow-up CSV data.
8. Append follow-up evaluation records to a separate evaluation JSONL.
9. Measure 5-trading-day alpha hit rate versus market benchmark.

The product is successful only if it improves both:

```text
candidate discovery speed
+
alpha evaluation integrity
```

This system is not:

- an autonomous trading bot,
- a public investment advisory service,
- a live intraday monitoring system,
- a market data downloader,
- a Markdown parser,
- a multi-user SaaS,
- or a general-purpose AI finance chatbot.

---

## 1. Core Operating Philosophy

### P1 — Deterministic Over Clever

Prefer deterministic, testable behavior over impressive AI behavior.

Priority order:

```text
correctness
> reproducibility
> auditability
> product scope discipline
> trader workflow speed
> implementation elegance
> AI cleverness
```

Do not invent hidden heuristics.  
Do not silently change ranking, evaluation, guardrail, schema, or logging semantics.

When the spec gives an enum, threshold, denominator, path, or ordering rule, treat it as a contract.

---

### P2 — Guardrails Are Product Logic

Guardrails are not a safety afterthought.  
Guardrails are core business logic.

The canonical pipeline is:

```text
StockAdviceContext JSON
→ validated context
→ raw LLM or fake advice
→ StockAdviceOutput schema validation
→ deterministic guardrails
→ GuardedAdviceOutput
→ ranked table
→ rendered final_advice only
→ append-only immutable advice JSONL
→ follow-up evaluation
→ append-only evaluation JSONL
```

Never rely on prompt wording as the only enforcement mechanism for:

- grade/recommendation compatibility,
- small_probe eligibility,
- A-grade eligibility,
- overheat/no-chase downgrade,
- data quality downgrade,
- hallucination blocking,
- benchmark defaulting,
- evaluation denominator rules.

If it matters, encode it in deterministic Python and tests.

---

### P3 — Product Boundary Discipline

This v1.2 project has a narrow MVP scope. Respect it.

Allowed in v1.2:

- Streamlit batch stock advice page.
- Loading multiple `StockAdviceContext` JSON files.
- fake/demo mode.
- real LLM mode guard UI with API key check, call estimate, and max-call guard.
- deterministic guardrails.
- deterministic ranking.
- row-level failure handling.
- immutable advice JSONL logging.
- separate follow-up evaluation JSONL logging.
- follow-up CSV evaluation.
- 5-trading-day alpha hit rate.
- release hardening CI that installs `requirements.txt` and runs the relevant pytest suite.
- README usage documentation for install, Streamlit launch, fixtures, fake/demo vs real guard mode, tests, and follow-up CSV.
- release UAT checklist for fixture batch flow and log integrity.

Not allowed in v1.2 unless explicitly requested:

- `Daily AI Advice`.
- `Risk Review`.
- market data downloading.
- trading calendar inference.
- intraday live tracking.
- auto order execution.
- portfolio construction.
- public advisory language.
- multi-user authentication.
- database migrations.
- vector databases.
- agent orchestration frameworks.
- complete multi-provider abstraction.
- real LLM API execution / provider integration; v1.2 real mode is guard-only until explicitly promoted to Phase 2 or v1.3.
- large speculative architecture rewrites.

If a useful idea belongs to Phase 2, document it only in `docs/phase2_backlog.md`. Do not implement it inside v1.2.

---

### P4 — Trader Workflow First

The user wants to scan candidates quickly.

Optimize for:

- batch processing,
- sortable tables,
- filterable candidate lists,
- stable ranking,
- quick row inspection,
- clear guardrail reasons,
- explicit warnings,
- fast demo iteration,
- easy fixture-based testing.

Do not optimize for:

- long AI prose,
- impressive explanations,
- hidden chain-of-thought,
- decorative UI,
- complex multi-screen flows,
- or premature platform architecture.

The core UX question is:

```text
Can the trader load 20+ stocks, sort/filter candidates, inspect one stock, and later evaluate alpha without opening individual Markdown files?
```

---

## 2. Execution Rules for Codex

### E1 — Start From Contracts

Before changing code, identify which contract the task touches:

- schema contract,
- guardrail contract,
- ranking contract,
- logging contract,
- Streamlit UX contract,
- LLM boundary contract,
- evaluation contract,
- file structure contract,
- security/secrets contract.

Then implement against that contract.

---

### E2 — Decisive, But Scope-Bounded

Act decisively on local, reversible, test-covered changes.

Ask only when the decision is:

```text
value-critical
+
not inferable from the spec
+
not safely reversible
```

Do not pause to ask about ordinary implementation details when the spec already implies the correct behavior.

---

### E3 — No Unauthorized Scope Expansion

Do not expand the project because it would be "nice".

Bad expansions:

- "Let's add yfinance."
- "Let's infer trading days automatically."
- "Let's add a SQLite DB."
- "Let's add auth."
- "Let's add provider plugins."
- "Let's build a full dashboard framework."
- "Let's parse Markdown contexts."
- "Let's run live market updates."

These are out of scope for v1.2.

If needed, add the idea to `docs/phase2_backlog.md`, but do not build it. Do not scatter Phase 2 backlog as casual source-code TODO comments. Implementation-code TODOs are allowed only for concrete technical debt tied to the current v1.2 scope.

---

### E4 — Local Refactor Only

Refactor only when it directly serves the current task.

Allowed refactor:

- clarifies schema boundaries,
- removes duplication in guardrails,
- isolates evaluation logic,
- makes tests deterministic,
- fixes a real bug,
- reduces coupling inside `ai_advisor`.

Not allowed without explicit authorization:

- crossing multiple bounded contexts,
- redesigning the whole architecture,
- changing public interfaces casually,
- moving files away from the recommended structure,
- replacing Streamlit with another UI framework,
- changing JSONL log semantics,
- changing evaluation denominators.

---

### E5 — Execution Is Evidence

Do not claim success from inspection alone.

For implementation tasks, run the relevant acceptance command whenever possible.

Use claim tags in final reports:

```text
[executed] pytest tests/test_ai_advisor_guardrails.py
[executed] pytest tests/test_ai_advisor_batch.py
[inspected] verified ranking code follows AGENTS.md priority
[assumed] Streamlit visual behavior not manually verified in browser
```

Never say "done" when tests were not run. Say exactly what was and was not verified.

---

## 3. Project File Structure

Follow this structure unless the existing repository already has a compatible convention:

```text
src/
  ai_advisor/
    __init__.py
    advice_engine.py
    batch_engine.py
    config.py
    context_builder.py
    evaluator.py
    guardrails.py
    llm_client.py
    prompt_templates.py
    report_renderer.py
    schemas.py

apps/
  ai_advisor_streamlit.py

config/
  ai_advisor.yaml
  prompts/
    _system_base.md
    stock_trade_advice.md

tests/
  fixtures/
    ai_advisor/
      stock_contexts/
      followup_prices_valid.csv
  test_ai_advisor_schemas.py
  test_ai_advisor_guardrails.py
  test_ai_advisor_batch.py
  test_ai_advisor_evaluator.py
  test_ai_advisor_streamlit_smoke.py

reports/
  ai_advice/
    .gitkeep

docs/
  phase2_backlog.md
  release_uat_checklist.md

.github/
  workflows/
    ci.yml

README.md
```

Do not scatter `ai_advisor` logic across unrelated folders.

---

## 4. Data Model Rules

### D1 — StockAdviceContext Is JSON-Only

v1.2 accepts structured UTF-8 JSON contexts only.

Do not parse Markdown in v1.2.

Required context fields:

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
```

If `market_type` is missing or explicitly set to `unknown`:

```text
market_type = "unknown"
benchmark_symbol = "TAIEX"
data_quality_warnings += ["market_type missing or unknown; default benchmark_symbol set to TAIEX"]
```

Exception: if a valid `benchmark_symbol` is explicitly provided (`TAIEX` or `OTC`), preserve it and still warn that `market_type` is unknown.

This behavior must be deterministic and tested.

---

### D2 — Fixed Enums Are Contracts

Do not introduce new enum values casually.

Allowed `market_type`:

```text
listed / otc / unknown
```

Allowed `benchmark_symbol`:

```text
TAIEX / OTC / unknown
```

Allowed `risk_state`:

```text
risk_on / neutral / risk_off
```

Allowed `theme.lifecycle`:

```text
early / main_uptrend / late_stage / fading / broken / unknown
```

Allowed `leader_rank`:

```text
leader_1 / leader_2 / follower / laggard / unknown
```

Allowed `technical.position`:

```text
breakout
pullback_to_ma5
pullback_to_ma10_and_rebound
near_ma20_support
extended_above_ma
breakdown
range_bound
unknown
```

Allowed `recommendation`:

```text
observe
wait_pullback
small_probe
avoid_chasing
reject
```

Allowed `grade`:

```text
A
B
C
Reject
```

---

## 5. LLM Integration Rules

### L1 — LLM Is Advisory, Not Authoritative

The LLM may generate structured advice.  
It does not decide final truth.

The deterministic guardrail layer decides whether the advice can be displayed as final.

Renderers and UI must display only:

```text
GuardedAdviceOutput.final_advice
```

Never render raw LLM advice as the user's final recommendation.

---

### L2 — Fake/Demo Mode Must Be Stable

Fake/demo mode is a first-class development and testing path.

It must:

- not call external LLM APIs,
- produce stable outputs for fixtures,
- allow 20+ stock batch testing,
- support deterministic guardrail tests,
- allow Streamlit MVP work without secrets.

Do not make fake mode random unless seeded and explicitly tested.

---

### L3 — Real LLM Mode Must Be Guarded

Real LLM mode must:

- check `OPENAI_API_KEY`,
- calculate `estimated_llm_calls = number_of_valid_contexts`,
- block runs above `max_llm_calls_per_run`,
- handle single-file request failure without breaking the whole batch,
- convert per-stock failures into blocked/error rows.

Do not allow a missing API key to crash the app.

For v1.2 release hardening, real LLM mode remains guard-only unless the user explicitly changes scope.
Do not wire real API execution in v1.2. Record true provider execution in `docs/phase2_backlog.md`.

---

### L4 — Prompt Cannot Replace Code

Prompt text may instruct the model, but it is not enough.

These must be enforced in code:

- schema validation,
- enum validation,
- grade/recommendation compatibility,
- confidence caps,
- downgrade/block reasons,
- evidence-based hallucination guard,
- ranking order,
- alpha denominator rules,
- missing benchmark handling.

---

### L5 — No Unsupported Claims

The model must not use or imply unsupported data such as:

```text
新聞
法人
外資
投信
營收
EPS
目標價
財報
訂單
```

unless the input context explicitly provides evidence fields for those claims.

If these terms appear in advice without matching evidence:

```text
hallucination_suspected = true
was_blocked = true
```

This must be implemented in deterministic code and tested.

---

## 6. Output Schema Rules

### O1 — Raw Advice Must Match Schema

`StockAdviceOutput` must include:

```text
recommendation
grade
confidence
summary
bull_case
bear_case
entry_conditions
stop_loss_plan
take_profit_plan
invalidation_conditions
next_session_confirmation
risk_flags
evidence
data_quality_warnings
```

The output must validate before guardrails.

Invalid raw output becomes an error/blocked row, not a batch crash.

---

### O2 — GuardedAdviceOutput Is the Product Output

Every successful or failed stock should become a `GuardedAdviceOutput`-compatible row.

It must preserve:

```text
raw_advice
final_advice
context_summary
guardrail_result
```

`guardrail_result` must include:

```text
was_downgraded
was_blocked
final_grade
final_recommendation
reasons
hallucination_suspected
error_message
```

Do not lose raw advice when guardrails downgrade it.

---

### O3 — Recommendation Semantics

Use these meanings consistently:

```text
observe          可觀察，尚未形成交易計畫
wait_pullback    只等回測，不追價
small_probe      可小部位試單，但必須有停損與觸發條件
avoid_chasing    不追價，條件太差或過熱
reject           放棄，資料或風險條件不合格
```

Grade compatibility:

```text
A       only with wait_pullback or small_probe
B       with observe / wait_pullback / small_probe
C       only with observe / wait_pullback / avoid_chasing
Reject  only with avoid_chasing / reject
```

Invalid combinations must be corrected or blocked by guardrails.

---

## 7. Balanced Guardrails

Guardrails must be deterministic code.

### G1 — Data Guard

If required data is missing:

```text
final_grade <= C
final_recommendation in [observe, avoid_chasing, reject]
confidence <= 60
data_quality_warnings must list missing fields
```

If any of these fields are missing, `small_probe` is forbidden:

```text
risk.invalid_level
risk.risk_reward_ratio
technical.position
theme.lifecycle
market_regime.risk_state
```

---

### G2 — Balanced Risk Guard

Rules:

```text
A grade requires risk.risk_reward_ratio >= 2.0
small_probe requires risk.risk_reward_ratio >= 1.5
is_overheated == true forbids small_probe
late_stage forbids A, but may allow wait_pullback
fading / broken must become avoid_chasing or reject
risk.invalid_level is null forbids positive advice
market_regime.risk_state == risk_off forbids A
```

Do not weaken these thresholds without explicit user authorization.

---

### G3 — No Chase Guard

Default downgrade to `wait_pullback` or `avoid_chasing` when:

```text
technical.position == extended_above_ma
technical.is_limit_up == true
stock.change_pct >= 7
```

If support proximity cannot be determined, record a risk flag. Do not invent support data.

---

### G4 — Hallucination Guard

If advice uses restricted information terms without evidence:

```text
hallucination_suspected = true
was_blocked = true
```

Restricted information terms include:

```text
新聞
法人
外資
投信
營收
EPS
目標價
財報
訂單
```

If evidence exists in context, allow it, but display the evidence source.

---

### G5 — Downgrade Transparently

Every downgrade or block must include an explicit reason.

Examples:

```text
risk_reward_ratio below 1.5; small_probe downgraded
late_stage cannot be grade A under balanced profile
market_type missing; default benchmark_symbol set to TAIEX
hallucination suspected: unsupported term "外資"
```

Never silently downgrade.

---

## 8. Batch Engine Rules

Required interfaces:

```python
def generate_stock_batch_advice(
    context_paths: list[str],
) -> list[GuardedAdviceOutput]:
    ...


def rank_stock_advices(
    outputs: list[GuardedAdviceOutput],
) -> list[RankedStockAdvice]:
    ...


def update_followup_returns(
    advice_log_path: str,
    followup_csv_path: str,
    evaluation_log_path: str = "reports/ai_advice/ai_advice_evaluation.jsonl",
) -> AlphaSummary:
    ...
```

`update_followup_returns(...)` is a compatibility name only. It must not rewrite or mutate `ai_advice_log.jsonl`. It reads immutable advice snapshots, calculates follow-up metrics, appends evaluation records to `ai_advice_evaluation.jsonl`, and returns an `AlphaSummary`.

Single-file failures must not break the batch.

Required row-level failure behavior:

```text
context validation failed -> blocked row
LLM request failed -> error row
hallucination suspected -> blocked row
```

Batch execution should return as many rows as possible.

---

## 9. Ranking Rules

Ranking must be fixed and stable.

Sort priority:

```text
1. was_blocked == false first
2. grade: A > B > C > Reject
3. recommendation: small_probe > wait_pullback > observe > avoid_chasing > reject
4. confidence high to low
5. risk_flags count low to high
6. stock_id ascending as stable fallback
```

Do not replace this ranking with model-generated ranking.

Required table columns:

```text
rank
stock_id
stock_name
grade
recommendation
confidence
risk_flags_count
data_quality_warnings_count
was_blocked
guardrail_reasons
```

Any change to ranking is a high-impact product change and requires explicit authorization.

---

## 10. Streamlit App Rules

Manual/dev launch command:

```bash
streamlit run apps/ai_advisor_streamlit.py
```

This is a long-running local server command, not an automated acceptance command. Agents must not use it as proof of verification unless they actually start the server, inspect the app, and then shut the server down.

### Required Sidebar Controls

```text
mode: fake/demo / real LLM
context input: upload JSON files / folder path
max batch size
show blocked rows: true / false
follow-up CSV uploader
```

### Required Main Views

```text
Batch Results
  sorted table
  filters
  summary metrics

Stock Detail
  conclusion
  core reasons
  bull case
  bear case
  entry plan
  stop loss
  take profit
  invalidation
  next-session confirmation
  data quality warnings

Alpha Evaluation
  actionable candidate count
  complete follow-up count
  alpha hit rate
  average alpha_5d_pct
```

### Required Safety UI

Every page must show:

```text
交易決策輔助，不是保證獲利或下單指令。
```

Real LLM mode must show before submission:

```text
estimated_llm_calls = number_of_valid_contexts
```

If the estimate exceeds `max_llm_calls_per_run`, block submission.

---

## 11. Logging Rules

There are two separate append-only JSONL logs. Do not collapse them into one mutable file.

### 11.1 Immutable Advice Snapshot Log

Advice snapshots are append-only and immutable:

```text
reports/ai_advice/ai_advice_log.jsonl
```

Each advice entry must preserve the state known at advice generation time:

```text
timestamp
advice_type
advice_date
stock_id
stock_name
advice_close
market_type
benchmark_symbol
input_context_hash
model
prompt_version
strategy_profile
raw_recommendation
raw_grade
final_recommendation
final_grade
confidence
was_downgraded
was_blocked
hallucination_suspected
guardrail_reasons
stock_return_5d_pct
benchmark_return_5d_pct
alpha_5d_pct
alpha_hit_5d
was_useful
human_feedback
```

The alpha fields inside advice entries are snapshot placeholders and should be `null` at advice creation. They exist for schema compatibility and must not be filled later by rewriting historical advice rows.

Never overwrite, reorder, deduplicate, or mutate historical advice snapshots during normal evaluation.

### 11.2 Follow-Up Evaluation Log

Follow-up results must be appended to a separate log:

```text
reports/ai_advice/ai_advice_evaluation.jsonl
```

Evaluation records must be keyed by:

```text
stock_id + advice_date + input_context_hash
```

Each evaluation entry should preserve:

```text
timestamp
evaluation_type
advice_date
stock_id
input_context_hash
advice_close
close_5d
benchmark_return_5d_pct
stock_return_5d_pct
alpha_5d_pct
alpha_hit_5d
included_in_alpha_denominator
exclusion_reason
source_followup_csv
```

If multiple evaluations are appended for the same key, consumers should use the latest valid evaluation record by timestamp and report that a superseding evaluation exists. Do not rewrite older evaluation records.

### 11.3 Migration / Repair Exception

A rewrite of historical JSONL is allowed only for an explicit migration or repair task. Such a task must:

1. create a timestamped backup,
2. write a migration note,
3. preserve original raw advice content,
4. report before/after record counts,
5. and never change alpha denominator semantics silently.

Logs are part of evaluation integrity.

---

## 12. Follow-Up Evaluation Rules

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

Evaluation output policy:

```text
read ai_advice_log.jsonl
match by stock_id + advice_date + input_context_hash when available
append evaluation result to ai_advice_evaluation.jsonl
do not mutate ai_advice_log.jsonl
```

Main alpha metric:

```text
alpha_hit_rate_5d_vs_market =
  alpha_hit_5d true count among actionable candidates with complete follow-up /
  actionable candidates with complete follow-up
```

Actionable candidate definition:

```text
grade in ["A", "B"]
recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
```

`observe` must not enter the main denominator.

If `benchmark_return_5d_pct` is missing:

```text
exclude that row from denominator
show warning
```

Do not infer trading calendars in v1.2.  
The CSV is assumed to already represent the 5th trading day close.

---

## 13. Benchmark Rules

Benchmark mapping:

```text
market_type == listed  -> benchmark_symbol = TAIEX
market_type == otc     -> benchmark_symbol = OTC
market_type missing    -> benchmark_symbol = TAIEX + data_quality_warning
market_type == unknown -> benchmark_symbol = TAIEX + data_quality_warning, unless valid benchmark_symbol is explicitly provided
```

Do not silently change benchmark based on stock ID unless the spec is updated.

---

## 14. Configuration and Secrets

Required config file:

```text
config/ai_advisor.yaml
```

Expected values:

```yaml
provider: openai
model: ${LLM_MODEL:-gpt-5.5}
reasoning_effort: ${LLM_REASONING_EFFORT:-medium}
temperature: 0.2
max_output_tokens: 3000
prompt_version: v1.2
strategy_profile: balanced

paths:
  prompt_dir: config/prompts
  output_dir: reports/ai_advice
  log_path: reports/ai_advice/ai_advice_log.jsonl
  evaluation_log_path: reports/ai_advice/ai_advice_evaluation.jsonl

batch:
  min_supported_stocks: 20
  max_stocks_per_run: 50
  max_llm_calls_per_run: 50

evaluation:
  alpha_horizon_days: 5
  horizon_type: trading_days
  default_benchmark: TAIEX

guardrails:
  min_rr_for_small_probe: 1.5
  min_rr_for_grade_a: 2.0
  max_confidence_when_data_missing: 60
  max_confidence_when_guardrail_downgraded: 70
```

`.env` may contain:

```env
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.5
LLM_REASONING_EFFORT=medium
```

`.gitignore` must include:

```text
.env
.env.*
secrets.json
reports/ai_advice/*.jsonl
```

Never commit secrets.  
Never print API keys in logs, tests, Streamlit UI, or exception traces.

---

## 15. Testing Philosophy

Tests encode product contracts.

Do not write tests that only mirror implementation details.  
Each test should protect a user-visible or system-critical guarantee.

Required test areas:

### Schema Tests

- valid `StockAdviceContext` passes,
- missing `market_type` does not fail but warns and defaults benchmark to TAIEX,
- explicit `market_type = unknown` warns and defaults benchmark to TAIEX unless a valid benchmark is explicitly provided,
- invalid `StockAdviceOutput` enum fails validation.

### Guardrail Tests

- complete data and `risk_reward_ratio >= 1.5` may allow `small_probe`,
- `risk_reward_ratio < 1.5` forbids `small_probe`,
- `is_overheated = true` forbids `small_probe`,
- `late_stage` forbids A but may allow `wait_pullback`,
- `fading / broken` becomes `avoid_chasing` or `reject`,
- restricted terms with evidence do not block,
- restricted terms without evidence block.

### Batch Tests

- 20+ fixtures can be processed,
- one LLM failure does not stop the batch,
- one validation failure does not stop the batch,
- ranking follows fixed priority.

### Streamlit Smoke Tests

- fixture folder can load,
- fake/demo and real LLM modes can switch,
- sorted table displays,
- detail view displays one stock plan,
- follow-up CSV displays 5-day alpha hit rate.

### Evaluation Tests

- positive 5-day alpha sets `alpha_hit_5d = true`,
- `observe` is excluded from main denominator,
- missing `benchmark_return_5d_pct` excludes row and warns,
- follow-up evaluation appends to `ai_advice_evaluation.jsonl` and does not mutate `ai_advice_log.jsonl`.

---

## 16. Acceptance Commands

Use the narrowest relevant command first, then expand.

### Session F — Stock Batch Core

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
```

### Session G — Streamlit MVP

Automated acceptance:

```bash
pytest tests/test_ai_advisor_streamlit_smoke.py
```

Manual/dev launch only:

```bash
streamlit run apps/ai_advisor_streamlit.py
```

Manual Streamlit verification requires all of the following:

1. start the server,
2. open the displayed local URL,
3. verify the required views/controls,
4. stop the server process,
5. report the inspection as `[inspected]`, not `[executed] automated acceptance`.

### Session H — Follow-Up Evaluation

```bash
pytest tests/test_ai_advisor_evaluator.py
```

### Full Relevant Test Set

```bash
pytest tests/test_ai_advisor_schemas.py \
       tests/test_ai_advisor_guardrails.py \
       tests/test_ai_advisor_batch.py \
       tests/test_ai_advisor_evaluator.py \
       tests/test_ai_advisor_streamlit_smoke.py
```

If Streamlit cannot be manually verified in the current environment, state that clearly.

### Release Hardening

```bash
python -m pip install -r requirements.txt
pytest tests/test_ai_advisor_schemas.py \
       tests/test_ai_advisor_guardrails.py \
       tests/test_ai_advisor_batch.py \
       tests/test_ai_advisor_evaluator.py \
       tests/test_ai_advisor_streamlit_smoke.py
```

Release hardening must also add or verify:

- `.github/workflows/ci.yml` installs from `requirements.txt` and runs the full relevant pytest set.
- `README.md` explains install, launch, fixture usage, fake/demo mode, real LLM guard-only status, follow-up CSV, and test commands.
- `docs/release_uat_checklist.md` documents manual fixture batch flow and JSONL log integrity checks.
- Real LLM execution remains deferred to Phase 2 / v1.3 unless explicitly authorized.

---

## 17. Reporting Format for Codex

When finishing a task, report in this structure:

```text
Summary
- What changed.

Verification
- [executed] exact commands run
- [inspected] files reviewed
- [assumed] anything not verified

Contract Impact
- Schema / guardrails / ranking / logging / evaluation / UI / config

Notes
- Any blocked items.
- Any Phase 2 ideas added to `docs/phase2_backlog.md`.
```

Do not write vague reports like:

```text
Done, should work.
```

Use precise evidence.

---

## 18. Human-Gated Decisions

Create or update `humanpending.md` only for true human-gated decisions.

Examples of human-gated decisions:

- changing alpha denominator,
- changing ranking order,
- changing guardrail thresholds,
- changing log schema,
- adding market data downloading,
- adding a database,
- changing benchmark mapping,
- changing v1.2 scope,
- implementing auto-trading behavior.

When a task is human-gated, continue all non-dependent work.

### Required `humanpending.md` Format

Use one compact Markdown table plus optional notes.

```markdown
# Human-Pending Decisions

| id | date | status | blocking_area | decision_needed | options | recommended_default | resolution | resolved_at |
|---|---|---|---|---|---|---|---|---|
| HP-001 | 2026-05-23 | open | evaluation | Choose alpha denominator change? | A: keep v1.2 denominator; B: include observe | A |  |  |
```

Allowed `status` values:

```text
open / resolved / obsolete
```

Lifecycle rules:

- Add a row only when work is genuinely blocked by a human decision.
- Keep shipping all non-dependent work.
- Before finishing the task, re-check all `open` items.
- Mark an item `resolved` when the user decides.
- Mark an item `obsolete` when later work makes it no longer gated.
- Do not leave vague stale blockers. Every open row must name the blocked area and recommended default.

---

## 19. Push-Back Duty

If the user request or local code direction violates the product principles, push back once with evidence and a safer alternative.

Examples:

- "This would leak future data into evaluation."
- "This changes the alpha denominator and would make historical metrics incomparable."
- "This moves guardrail enforcement into prompt text only, which violates deterministic product logic."
- "This adds a Phase 2 feature into v1.2 and risks delaying the MVP."

If the user explicitly confirms the change afterward, implement it and document the scope change.

---

## 20. Definition of Done

v1.2 is done only when:

- Streamlit app is the primary entry point.
- fake/demo mode can batch process at least 20 fixture stocks.
- real LLM mode has API key check, LLM call estimate, and max-call guard; real API execution is not required for v1.2.
- results table supports sorting/filtering and row detail inspection.
- single-stock failures do not interrupt the batch.
- balanced guardrails pass tests.
- evidence-based hallucination guard passes tests.
- immutable advice snapshot log contains advice close, market type, benchmark, and null alpha placeholder fields.
- follow-up evaluation log contains computed 5-day return, benchmark return, alpha, denominator inclusion, and exclusion reason.
- follow-up CSV import calculates 5-trading-day alpha hit rate.
- `observe` is excluded from main alpha denominator.
- GitHub Actions CI exists and runs dependency install plus the relevant pytest suite.
- `README.md` gives a new-session operator enough instructions to install dependencies, run Streamlit, use fixtures, run tests, and understand fake/demo vs real guard mode.
- `docs/release_uat_checklist.md` exists and covers fixture batch flow, follow-up CSV, advice log immutability, and evaluation log append-only behavior.
- secrets are not committed.
- relevant tests are executed and reported.

---

## 21. Final Principle

This product is not about making AI write more.

It is about helping the trader find better candidates faster, preserve decision evidence, and verify after 5 trading days whether the system actually found alpha.

When uncertain, choose the implementation that maximizes:

```text
determinism
+ auditability
+ batch workflow speed
+ evaluation integrity
```
