# Market Data Scanner Risk Register

Status: draft  
Related: `docs/market_data_scanner_v1_3_plan.md`

| id | severity | risk | impact | mitigation |
|---|---|---|---|---|
| MDR-001 | High | Official data endpoint format changes | Scanner fails or writes invalid contexts | Start with local raw file adapter; add source-contract tests before downloader |
| MDR-002 | High | Missing sector/theme data | Scanner may fabricate theme fields or produce misleading contexts | Use `theme.name = "market_scan"`, fixed neutral `theme.rank = 999` / `theme.score = 50`, scanner metadata for scanner strength, and data quality warning |
| MDR-003 | High | Risk/target proxy is too optimistic | Candidate quality and alpha evaluation become misleading | Use observed structural targets for primary `planned_target`; keep any fallback proxy in notes/metadata only |
| MDR-004 | Medium | Too many hard skips produce fewer than 20 contexts | Official pilot cannot exercise batch workflow | Use hard skips only for data validity; use penalties/warnings for trade-quality concerns |
| MDR-005 | Medium | Market regime risk_off suppresses all candidates | Scanner misses relative-strength watchlist opportunities | Use risk_off penalty and let guardrails forbid A-grade downstream |
| MDR-006 | Medium | Limit-up flag unavailable or unreliable | No-chase behavior may be inconsistent | If official flag is missing, use deterministic approximation with warning; do not claim official limit-up |
| MDR-007 | Medium | Listed / OTC universe incomplete | Benchmark mapping or candidate coverage becomes wrong | Validate market_type source; emit warnings for unknown market_type |
| MDR-008 | Medium | Download failure after market close | Pilot cannot generate contexts | Cache raw downloads; support local raw file fallback |
| MDR-009 | Low | Node/action/tooling warning unrelated to scanner | CI noise distracts from scanner failures | Track separately as low risk unless CI breaks |
| MDR-010 | High | LLM-generated ranking sneaks into scanner | Product becomes non-deterministic and unauditable | Scanner scoring must be deterministic code with tests |
| MDR-011 | High | Advice or evaluation logs are mutated by scanner | Alpha evaluation integrity is damaged | Scanner must only write context JSON; never edit reports/ai_advice logs |
| MDR-012 | Medium | Turnover/liquidity threshold chosen poorly | Either too many illiquid stocks or too few contexts | Put liquidity floor in config and review after pilot |
| MDR-013 | High | Risk/reward formula becomes self-fulfilling | Scanner overstates RR by constructing target from desired risk multiple | Targets must come from structural market levels; tests must prove low-RR paths are reachable |
| MDR-014 | Medium | `market_scan` fallback is misread as a real sector/theme | LLM or user-facing text may overstate theme strength | Add data quality warnings and require prompt/rendering review before real LLM use |
| MDR-015 | High | Scanner score is placed into `theme.score` | Contexts imply fake theme strength and may bias prompts, rendering, or PM review | Keep `market_scan` `theme.score = 50`; store scanner rank/score and relative strength in scanner metadata |
| MDR-016 | High | Fallback 2R proxy is treated as a structural market target | RR sorting becomes circular and hides weak reward geometry | Forbid pure `close + 2R` in primary `planned_target` and `risk_reward_ratio`; allow it only as labeled notes/metadata |
| MDR-017 | High | No-parameter official OpenAPI candidates do not provide enough history | MA60, RS60, and benchmark regime can be wrong or unavailable if downloader assumes one-call completeness | Require verified historical accumulation before downloader implementation; source-contract docs must state observed history length |
| MDR-018 | Medium | Official source latest dates differ across TWSE and TPEx | Scanner may combine mismatched listed, OTC, TAIEX, and OTC snapshots | Downloader must validate same-date completeness and fail or warn deterministically before context generation |
| MDR-019 | Medium | Listed source lacks official limit-up/down fields while OTC exposes next-day limit prices | No-chase and limit-up handling may be inconsistent by market | Find a listed official limit source or use deterministic approximation with warning; do not label approximations as official |
