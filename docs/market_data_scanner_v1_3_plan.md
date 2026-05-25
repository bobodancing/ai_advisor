# Market Data Scanner v1.3 Plan

Status: Gate 0 resolved; M6 official source spike completed
Owner: PM + Codex  
Purpose: solve the blocker where the trader has no CSV and no ready `StockAdviceContext` folder.

Market Data Scanner is the upstream module that obtains after-market market data, computes deterministic candidate features, and writes `StockAdviceContext` JSON files for AI Advisor.

This is not part of v1.2.x runtime behavior. It must be treated as a new scoped project before implementation.

---

## 1. Product Fit

The v1.2.x AI Advisor product loop starts from existing context JSON:

```text
StockAdviceContext JSON folder
-> Streamlit batch advice
-> fixed ranking
-> advice JSONL
-> follow-up CSV
-> 5-trading-day alpha evaluation
```

The user currently lacks the first input. Market Data Scanner creates that missing input:

```text
official after-market market data
-> deterministic market scanner
-> 20-50 StockAdviceContext JSON files
-> AI Advisor Streamlit pilot
```

It solves:

- no context folder,
- no manually prepared CSV,
- need for a repeatable after-market candidate-generation process.

It does not solve:

- real-time intraday monitoring,
- auto trading,
- public investment advice,
- Real LLM API execution,
- broker integration,
- guaranteed alpha.

---

## 2. Required Scope Discipline

Allowed for v1.3 scanner:

- read-only after-market market data ingestion,
- local cache of downloaded raw data,
- deterministic feature calculation,
- deterministic filters and scoring,
- `StockAdviceContext` JSON output,
- tests for all feature and filter logic.

Not allowed in first scanner version:

- intraday live tracking,
- broker API orders,
- LLM-generated ranking,
- discretionary hidden heuristics,
- rewriting advice/evaluation logs,
- changing existing AI Advisor guardrails or ranking,
- changing alpha denominator,
- changing benchmark mapping without PM approval.

Market data source Gate 0 is resolved in `docs/market_data_source_decision.md`.
M6 source findings are recorded in `docs/market_data_source_spike_m6.md`.

Resolved source policy:

```text
Long-term product direction:
  official TWSE / TPEx after-market public data

First implementation:
  local raw market-data file adapter using official-format raw samples,
  then official downloader after source behavior is verified
```

M6 verified current official source/API behavior as a spike only. The observed no-parameter endpoints remain insufficient by themselves for MA60 / RS60, so this is not production downloader approval.

Source policy:

```text
Prefer official TWSE / TPEx after-market data where practical.
Use read-only public data only.
Cache raw downloads locally for reproducibility.
Do not scrape brittle web pages when a stable downloadable endpoint exists.
```

---

## 3. Minimum Data Needed

To generate useful contexts, scanner needs at least 60 trading sessions of daily data for each stock:

```text
date
stock_id
name
market_type
open
high
low
close
volume
turnover_value
```

It also needs benchmark series:

```text
TAIEX daily close
OTC daily close
```

Optional but valuable:

```text
industry / sector category
listed common-stock universe
limit-up / limit-down flags if available
```

If industry/sector data is unavailable in the first version, the scanner may use the deterministic fallback in Section 4.1. It must add a data quality warning and must not pretend to know real themes.

---

## 4. Deterministic Context Field Mapping

Scanner output must validate as `StockAdviceContext`.

Required mappings:

```text
date -> advice candidate date
market_type -> listed / otc
benchmark_symbol -> TAIEX / OTC
stock.stock_id -> stock_id
stock.name -> name
stock.close -> latest close
stock.change_pct -> latest daily pct change
stock.volume_ratio_20d -> latest volume / 20-day average volume
market_regime.risk_state -> benchmark regime calculation
theme.* -> sector/theme calculation or fixed generic market_scan fallback
leader_status.leader_rank -> deterministic rank bucket within sector/theme or scanner universe
technical.position -> deterministic technical position classifier
technical.is_overheated -> deterministic overheat classifier
technical.is_limit_up -> source flag or deterministic approximation with warning
risk.invalid_level -> deterministic invalidation level
risk.nearest_support -> deterministic support level
risk.planned_target -> observed structural target above close
risk.risk_reward_ratio -> calculated reward/risk ratio
```

Every inferred field must be deterministic and documented in code/tests.

---

### 4.1 Theme And Leader Fallback

The scanner must always output valid `theme.*` and `leader_status.*` fields without inventing unsupported market narratives.

If real sector/theme data is available:

```text
theme.name = source sector/theme name
theme.rank = dense rank by scanner_score within that theme
theme.score = normalized 0-100 scanner score within that theme
theme.lifecycle = deterministic lifecycle if available, otherwise "unknown"
leader_status.leader_rank = percentile bucket within that theme
```

If real sector/theme data is unavailable:

```text
theme.name = "market_scan"
theme.rank = 999
theme.score = 50
theme.lifecycle = "unknown"
leader_status.leader_rank = scanner universe percentile bucket, not a real theme leader rank
scanner_metadata.scanner_rank = dense rank by deterministic scanner score within generated universe
scanner_metadata.scanner_score = normalized 0-100 deterministic scanner score
scanner_metadata.relative_strength_20d_vs_benchmark = calculated relative strength
scanner_metadata.relative_strength_60d_vs_benchmark = calculated relative strength
data_quality_warnings += ["sector/theme data unavailable; market_scan fallback used"]
data_source_notes += ["theme.rank/theme.score are neutral market_scan fallback values, not real sector strength"]
data_source_notes += ["leader_status.leader_rank is a scanner universe bucket, not a true theme leader claim"]
```

Recommended `leader_status.leader_rank` percentile buckets:

```text
percentile <= 10%                  -> leader_1
10% < percentile <= 25%            -> leader_2
25% < percentile <= 60%            -> follower
percentile > 60%                   -> laggard
insufficient ranking data -> unknown
```

When `theme.name = "market_scan"`, `theme.rank` and `theme.score` must remain fixed neutral fallback values. Do not place scanner score, relative strength, or scanner universe rank into `theme.rank` or `theme.score`; doing so creates fake theme strength. Scanner-specific strength belongs in `scanner_metadata` or equivalent non-theme metadata.

Prompts and renderers must not describe `market_scan` fallback as a real sector or narrative theme. If `theme.name == "market_scan"`, user-facing text should treat it as a generic scanner bucket with data quality warnings.

---

## 5. Technical Classifier Proposal

Use simple, testable daily OHLCV rules. Do not use an LLM.

Compute:

```text
MA5, MA10, MA20, MA60
20-day average volume
20-day high / low
60-day high / low
distance from MA20
20-day and 60-day relative strength versus benchmark
```

Suggested `technical.position` rules, evaluated in order:

```text
breakdown:
  close < MA20 and close < prior_20d_low

pullback_to_ma10_and_rebound:
  close >= MA10 and low <= MA10 * 1.015 and close > open

pullback_to_ma5:
  close >= MA5 and low <= MA5 * 1.01 and close > open

near_ma20_support:
  close >= MA20 and low <= MA20 * 1.02

breakout:
  close > prior_20d_high and volume_ratio_20d >= 1.5

extended_above_ma:
  close >= MA20 * 1.12 or close >= MA10 * 1.08

range_bound:
  otherwise, if close >= MA20 * 0.98 and close <= prior_20d_high

unknown:
  insufficient data
```

These rules are intentionally conservative and must be tested with fixture series.

---

## 6. Risk Field Proposal

Risk fields must be deterministic and transparent.

Suggested defaults:

```text
nearest_support = max(valid support levels below close)
  candidates: MA10, MA20, prior_10d_low, prior_20d_low

invalid_level = nearest_support * 0.98

risk_per_share = close - invalid_level

structural_target_candidates_above_close:
  prior_20d_high if prior_20d_high > close
  prior_60d_high if prior_60d_high > close
  measured_range_target if technical.position == "breakout"

measured_range_target:
  prior_20d_high + 0.5 * (prior_20d_high - prior_20d_low)
  only when close > prior_20d_high
  and prior_20d_high > prior_20d_low
  and measured_range_target > close

planned_target = nearest structural target above close
  choose the lowest valid target above close for pullback/range candidates
  choose measured_range_target for breakout when available
  otherwise choose prior_60d_high if above close

risk_reward_ratio = (planned_target - close) / (close - invalid_level)
```

`planned_target` must come from observed structural market levels first. Valid primary sources include prior swing highs, prior range highs, measured range targets, or other documented structural levels derived from actual OHLCV history.

Do not include a pure `close + 2R` or `close + N * risk_per_share` value as a primary `planned_target` candidate. Such targets are formula outputs, not observed structural targets, and they must not enter primary `risk.planned_target`, `risk.risk_reward_ratio`, or RR-based sorting.

If a fallback 2R proxy is useful for operator diagnostics, store it only in `data_source_notes`, `scanner_metadata`, or equivalent metadata. It must be clearly labeled as a fallback proxy and must not drive `risk_reward_ratio`, hard skip/pass decisions, or preferred candidate ordering.

If no valid support below close exists:

```text
technical.position = unknown or range_bound
skip row with reason "no valid support below close"
```

If `planned_target <= close`, skip with reason:

```text
no positive reward target
```

These are scanner proxies, not guarantees. Output contexts should include `data_source_notes` explaining that support/target/risk-reward are scanner-derived.

Do not cap `planned_target` at `prior_60d_high` when the stock is already near or above that level. Otherwise new-high candidates can be incorrectly skipped as having no upside.

If no structural target above close exists, skip with reason:

```text
no structural target above close
```

Alternatively, if PM explicitly wants broader pilot coverage, the scanner may emit a low-priority warning context only when `risk.planned_target` remains a documented structural target. It must not synthesize `planned_target = close + 2R` to make the row pass.

---

## 7. Market Regime Proposal

Calculate by benchmark:

```text
risk_on:
  benchmark close > MA20 and MA20 >= MA60

neutral:
  benchmark close >= MA20 * 0.98

risk_off:
  benchmark close < MA20 * 0.98 or MA20 < MA60
```

Listed stocks use TAIEX. OTC stocks use OTC.

Do not infer trading calendars beyond the downloaded daily series.

M2 indicator logic may return scanner-only `risk_state = "unknown"` when benchmark data is insufficient. M3 context writing must not write that value into v1.2 `StockAdviceContext.market_regime.risk_state`; insufficient regime data must cause a deterministic skip or warning/block path instead.

---

## 8. Filter Policy

The scanner filter should produce enough contexts while still respecting the no-chase / balanced-risk product philosophy.

M4 owns hard skip policy, penalty policy, and final scanner score. M3 structural risk derivation exists only to support valid `StockAdviceContext` schema output and must not be treated as final scanner policy.

Initial configurable defaults:

```text
min_turnover_value = 20_000_000 TWD
min_output_warning_threshold = 20
max_output = 50
```

These are first-pilot defaults, not permanent product law. The scanner must keep them in configuration so PM can tune after pilot evidence.

### 8.1 Hard Skip

Skip and report reason when:

```text
insufficient history for MA60
market_type not listed/otc
close <= 0
turnover_value below configured liquidity floor
change_pct < -3
technical.position == "breakdown"
risk.nearest_support missing
risk.invalid_level missing
risk.invalid_level >= close
risk.risk_reward_ratio <= 1.0
planned_target <= close
is_limit_up == true
```

Hard skip is for data validity or clearly unusable trade geometry. Do not use hard skip for every condition that would merely downgrade advice under v1.2 guardrails.

Because `planned_target` must come from structural market levels, `risk_reward_ratio <= 1.0` is meaningful and should not be made impossible by formula construction.

Do not hard-skip `theme.lifecycle == unknown` in the first market-data scanner if theme data is unavailable. Instead, add a data quality warning and penalize score. Otherwise the scanner may produce too few contexts.

### 8.2 Penalties And Warnings

Apply deterministic scoring penalties and warnings when:

```text
1.0 < risk_reward_ratio < 1.5
volume_ratio_20d < 1.2 but liquidity floor is satisfied
change_pct >= 7 and not official limit-up
market_regime.risk_state == risk_off
technical.position == "extended_above_ma"
technical.position == "unknown"
theme.lifecycle == "unknown"
theme.lifecycle in ["fading", "broken"] when real sector/theme lifecycle is available
is_overheated == true
```

Recommended warnings:

```text
risk_reward_ratio below small_probe threshold
no-chase penalty: change_pct >= 7
market risk_off; guardrails will forbid A-grade
extended above moving averages; no-chase risk
theme lifecycle unknown; market_scan fallback used
```

Rows with penalties may still be written as lower-priority contexts. The AI Advisor guardrails remain responsible for final downgrade/block decisions.

### 8.3 Preferred Candidate Score

Sort pass rows by:

```text
1. risk_reward_ratio high to low
2. relative_strength_20d_vs_benchmark high to low
3. relative_strength_60d_vs_benchmark high to low
4. volume_ratio_20d high to low
5. technical.position preference:
   pullback_to_ma10_and_rebound
   > pullback_to_ma5
   > near_ma20_support
   > breakout
   > range_bound
   > extended_above_ma
6. lower distance above MA20 preferred
7. stock_id ascending
```

Rationale:

- risk/reward comes first because guardrails and trader usefulness depend on it,
- relative strength keeps the scanner aligned with alpha discovery,
- volume expansion helps find active candidates,
- pullback/rebound candidates are prioritized over chase-prone extensions.

### 8.4 Output Size

Defaults:

```text
min_output_warning_threshold = 20
max_output = 50
```

If fewer than 20 contexts remain:

- write valid contexts that exist,
- warn clearly,
- include skipped-row summary,
- optionally include second-tier penalty rows to reach the minimum, but mark them with explicit warnings,
- do not fabricate missing values.

---

## 9. Implementation Shape

Recommended bounded context:

```text
src/ai_advisor/market_scanner/
  __init__.py
  sources.py
  indicators.py
  scanner.py
  context_writer.py

tests/
  fixtures/
    ai_advisor/
      market_scanner/
        listed_prices_sample.csv
        otc_prices_sample.csv
        benchmark_prices_sample.csv
  test_ai_advisor_market_scanner_indicators.py
  test_ai_advisor_market_scanner.py
```

Suggested command:

```bash
python -m ai_advisor.market_scanner.scanner --date 2026-05-24 --output data/pilot_contexts/2026-05-24 --max 50
```

If live download adapters are not ready, first implementation may support a local raw market-data folder:

```bash
python -m ai_advisor.market_scanner.scanner --input data/raw_market/2026-05-24 --output data/pilot_contexts/2026-05-24 --max 50
```

---

## 10. Required Tests

- indicator calculations are deterministic,
- benchmark regime classification works for listed and OTC,
- technical position classifier covers all enum outputs,
- risk fields produce valid positive reward/risk or skip with reason,
- hard skip rules are deterministic,
- score ordering is stable,
- generated JSON files validate as `StockAdviceContext`,
- `market_scan` fallback fills `theme.*` and `leader_status.*` deterministically and includes data quality warnings,
- `market_scan` fallback keeps `theme.rank = 999`, `theme.score = 50`, and stores scanner strength in `scanner_metadata`, not `theme.*`,
- `planned_target` is selected from structural market targets and never from `close + N * risk_per_share`,
- fallback 2R proxy values, if present, are metadata/notes only and do not drive `risk_reward_ratio` or RR sorting,
- fixture cases prove `risk_reward_ratio <= 1.0` and `1.0 < risk_reward_ratio < 1.5` paths are reachable,
- output count respects `max_output`,
- fewer than 20 output contexts produces warning, not fabricated data,
- scanner does not mutate advice/evaluation logs.

Before generated `market_scan` contexts are used with any real LLM mode, prompt/rendering behavior must be reviewed so `market_scan` is not described as a real sector or narrative theme.

M5 integration check is automated integration/smoke verification only. Manual Streamlit browser UAT has not been executed and remains for release/UAT or a later manual acceptance pass.

Acceptance commands:

```bash
pytest tests/test_ai_advisor_market_scanner_indicators.py tests/test_ai_advisor_market_scanner.py
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_market_scanner.py tests/test_ai_advisor_streamlit_smoke.py
```

---

## 11. Gate 0 Source Decisions

Resolved on 2026-05-24 and recorded in `humanpending.md` and `docs/market_data_source_decision.md`.

```text
HP-001 product direction data source:
  accepted A. official TWSE / TPEx after-market public data

HP-002 first implementation adapter path:
  accepted B. local raw file adapter first, then downloader
```

The scanner must not begin with brittle scraping or paid-provider assumptions unless explicitly approved.

Recommended implementation order:

```text
1. local raw market-data file adapter
2. deterministic indicators / scanner / context writer
3. official TWSE / TPEx downloader after source shape is verified
```

Risk register: `docs/market_data_scanner_risk_register.md`.
