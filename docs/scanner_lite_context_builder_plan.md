# Scanner Lite / Context Builder Plan

Status: optional bridge only; insufficient when the user has no CSV  
Owner: PM + Codex  
Purpose: convert an existing user-provided after-market CSV into a ready `StockAdviceContext` folder.

Scanner Lite is not a full market scanner. It is a deterministic CSV-to-`StockAdviceContext` builder.

It converts a user-provided after-market CSV into a folder of validated stock context JSON files that AI Advisor v1.2.x can load through Streamlit.

If the user has no CSV, this plan does not solve the blocker. Use `docs/market_data_scanner_v1_3_plan.md` instead.

---

## 1. Product Fit

This task supports the existing AI Advisor product loop:

```text
user-provided after-market CSV
-> deterministic Scanner Lite filtering
-> StockAdviceContext JSON folder
-> Streamlit batch advice
-> append-only advice log
-> follow-up CSV
-> 5-trading-day alpha evaluation
```

It solves:

- the user has no suitable `StockAdviceContext` folder but does have an after-market CSV,
- the user can prepare or export a structured after-market table,
- the user needs 20-50 candidate contexts for official pilot runs.

It does not solve:

- no raw after-market data source at all,
- automatic market data download,
- technical pattern inference,
- trading calendar inference,
- Real LLM execution,
- auto trading.

Those remain out of v1.2.x scope unless explicitly approved.

---

## 2. Input Contract

Input is UTF-8 CSV. Each row is one stock.

Required columns:

```text
date
stock_id
name
market_type
close
change_pct
volume_ratio_20d
theme_name
theme_rank
theme_score
theme_lifecycle
leader_rank
technical_position
is_overheated
is_limit_up
invalid_level
nearest_support
planned_target
risk_reward_ratio
market_risk_state
```

Allowed enum values must match `StockAdviceContext` contracts:

- `market_type`: `listed`, `otc`, `unknown`
- `market_risk_state`: `risk_on`, `neutral`, `risk_off`
- `theme_lifecycle`: `early`, `main_uptrend`, `late_stage`, `fading`, `broken`, `unknown`
- `leader_rank`: `leader_1`, `leader_2`, `follower`, `laggard`, `unknown`
- `technical_position`: `breakout`, `pullback_to_ma5`, `pullback_to_ma10_and_rebound`, `near_ma20_support`, `extended_above_ma`, `breakdown`, `range_bound`, `unknown`

The builder must not invent missing values.

If `market_type` is missing or `unknown`, preserve the existing schema behavior: default benchmark to `TAIEX` and add a data quality warning unless a valid explicit benchmark is supplied.

---

## 3. Filter Policy

The filter is deterministic. It is not an LLM ranking system and must not replace AI Advisor's fixed final ranking.

Scanner Lite should align with the v1.3 market scanner filter policy: hard skip is reserved for invalid data, invalid stop/target geometry, official limit-up rows, breakdown rows, or clearly unusable trade geometry. Do not add hard skips that are more aggressive than `docs/market_data_scanner_v1_3_plan.md` unless this document states a specific rationale.

### 3.1 Hard Skip

Skip a row and report a reason when:

- required CSV columns are missing,
- `stock_id`, `date`, `close`, `invalid_level`, `risk_reward_ratio`, `technical_position`, `theme_lifecycle`, or `market_risk_state` is missing,
- numeric fields cannot be parsed,
- `close <= 0`,
- `risk_reward_ratio <= 1.0`,
- `change_pct < -3`,
- `technical_position == "breakdown"`,
- `invalid_level >= close`,
- `is_limit_up == true`.

Rationale:

- hard skip is reserved for invalid data or clearly unusable trade geometry,
- `risk_reward_ratio <= 1.0` has no positive enough reward/risk to be useful,
- `breakdown` and invalid stop geometry are poor first-pilot inputs,
- official limit-up rows are not suitable for no-chase pilot inputs.

If fewer than the requested minimum contexts remain, do not fabricate or infer data. Return a warning and a skipped-row summary.

### 3.2 Penalties And Warnings

Apply deterministic penalties and warnings when:

- `1.0 < risk_reward_ratio < 1.5`,
- `theme_score < 70`,
- `volume_ratio_20d < 1.2`,
- `change_pct >= 7` and not official limit-up,
- `theme_lifecycle in ["fading", "broken", "unknown"]`,
- `technical_position == "unknown"`,
- `market_risk_state == "risk_off"`,
- `is_overheated == true`.

Specifically, these conditions are penalties/warnings rather than hard skips:

- `market_risk_state == "risk_off"`,
- `change_pct >= 7` and not official limit-up,
- `1.0 < risk_reward_ratio < 1.5`,
- `theme_lifecycle == "unknown"`.

Rows with penalties may still be emitted as lower-priority contexts. Existing AI Advisor guardrails remain responsible for final downgrade/block decisions.

### 3.3 Preferred Candidate Signals

Among rows that pass hard skip, score and sort deterministically before writing up to `max_output` contexts.

Recommended scoring order:

```text
1. theme_score high to low
2. risk_reward_ratio high to low
3. leader_rank: leader_1 > leader_2 > follower > laggard > unknown
4. theme_lifecycle: early > main_uptrend > late_stage
5. technical_position:
   pullback_to_ma10_and_rebound
   > pullback_to_ma5
   > near_ma20_support
   > breakout
   > range_bound
   > extended_above_ma
6. volume_ratio_20d high to low
7. change_pct closer to 0-5% preferred over deeply negative or near no-chase threshold
8. stock_id ascending as stable fallback
```

### 3.4 Output Size

Default targets:

```text
min_output_warning_threshold = 20
max_output = 50
```

If fewer than 20 contexts are generated, the command still writes valid contexts but exits with a visible warning.

The summary must report:

- input row count,
- generated context count,
- skipped row count,
- skip reasons grouped by reason,
- output folder,
- warning when generated context count is below 20.

---

## 4. Output Contract

Output is one UTF-8 JSON file per stock.

Each output JSON must validate as `StockAdviceContext`.

Recommended file name:

```text
{stock_id}.json
```

Output folder example:

```text
data/pilot_contexts/2026-05-24
```

Generated context values should map directly:

```text
date -> date
stock_id/name/close/change_pct/volume_ratio_20d -> stock.*
market_risk_state -> market_regime.risk_state
theme_name/theme_rank/theme_score/theme_lifecycle -> theme.*
leader_rank -> leader_status.leader_rank
technical_position/is_overheated/is_limit_up -> technical.*
invalid_level/nearest_support/planned_target/risk_reward_ratio -> risk.*
```

Do not add unsupported evidence such as news, EPS, institution flow, or price targets unless explicit source columns are added and tested later.

---

## 5. Implementation Scope

Expected additions:

- `src/ai_advisor/context_builder.py`
- `tests/fixtures/ai_advisor/scanner_input_valid.csv`
- `tests/test_ai_advisor_context_builder.py`
- small README / runbook references

Suggested dev command:

```bash
python -m ai_advisor.context_builder --input data/scanner_input/sample.csv --output data/pilot_contexts/2026-05-24 --max 50
```

The command must not call external APIs.

---

## 6. Required Tests

- valid CSV rows generate valid `StockAdviceContext` JSON files,
- at least 25 fixture rows can generate at least 20 contexts,
- invalid enum rows are skipped with reasons,
- missing required fields are skipped with reasons,
- missing `market_type` does not fail and produces the existing benchmark warning,
- `max_output` limit is enforced,
- hard skip filters are deterministic,
- output JSON files can be loaded by existing batch advice flow.

Acceptance commands:

```bash
pytest tests/test_ai_advisor_context_builder.py
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_context_builder.py tests/test_ai_advisor_streamlit_smoke.py
```

---

## 7. Non-Goals

- no market data download,
- no trading calendar inference,
- no Markdown parsing,
- no automatic technical-position inference,
- no Real LLM API execution,
- no new AI ranking layer,
- no changes to advice ranking or alpha denominator,
- no auto trading.
