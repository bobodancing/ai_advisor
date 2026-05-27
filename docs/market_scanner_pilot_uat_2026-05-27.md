# Formal Scanner Pilot UAT Evidence - 2026-05-27

This note records the formal UAT evidence for the v1.3 Market Scanner local raw pilot flow.

It is a docs-only evidence summary. It does not approve a production downloader, does not include raw CSV contents, and does not include full JSONL contents.

## 1. Pilot Metadata

| field | value |
|---|---|
| pilot_date | 2026-05-27 |
| repository_commit | 2e0ecef |
| raw folder | `data/raw_market/official_pilot_2026-05-27` |
| output context folder | `data/pilot_contexts/official_pilot_2026-05-27` |
| scope | Formal Scanner Pilot UAT over local aggregate official-format raw CSV files |

## 2. Scope Confirmation

| check | result | notes |
|---|---|---|
| No production downloader used | Pass | UAT used pre-existing local aggregate raw CSV inputs. |
| No downloader or scheduler launched | Pass | Scanner CLI and Streamlit fake/demo inspection only. |
| Scanner policy changed | No | No code changes were made during formal UAT execution. |
| Raw CSV contents included in this note | No | Only audit metadata is recorded. |
| Full JSONL contents included in this note | No | Only inventory metadata is recorded. |
| Generated data committed | No | `data/`, generated contexts, and JSONL logs remain out of scope for commit. |

## 3. Local Raw Input Audit

| file | bytes | sha256 |
|---|---:|---|
| `listed_stock_daily.csv` | 388369 | `4af2fa0dd64e00e083c3e6e2741b3ba87c77a4e17c640116967c1c195b51173b` |
| `otc_stock_daily.csv` | 159508 | `0a529a83bd6296e07a42b28d4565cc5e58a73a7a463ce9a9db0d05308c05dadc` |
| `taiex_benchmark.csv` | 5631 | `7ab8b6afe5c404043f14617050d5f62dfff0a5a51db18648286c449c3e247cd7` |
| `otc_benchmark.csv` | 4910 | `263735b018d8dd62269ebf23e7c5192405ae6622f07acc4fd708a9a165f37297` |

## 4. Scanner CLI Summary

Scanner command executed against the four local raw files and wrote generated contexts to:

```text
data/pilot_contexts/official_pilot_2026-05-27
```

| field | value |
|---|---:|
| CLI exit code | 0 |
| input_candidate_count | 81 |
| output_context_count | 26 |
| skipped_count | 55 |

Warnings:

```text
[]
```

Skip reason counts:

| reason | count |
|---|---:|
| `change_pct < -3` | 10 |
| `context writer skipped: structural risk geometry unavailable` | 12 |
| `risk_reward_ratio <= 1.0` | 32 |
| `turnover_value below configured liquidity floor` | 1 |

Penalty counts:

| reason | count |
|---|---:|
| `extended above moving averages; no-chase risk` | 1 |
| `is_overheated == true` | 1 |
| `risk_reward_ratio below small_probe threshold` | 9 |
| `technical position unknown` | 4 |
| `theme lifecycle unknown; market_scan fallback used` | 26 |
| `volume_ratio_20d below 1.2` | 25 |

Source audit:

| source | record_count | skipped_row_count | latest_date |
|---|---:|---:|---|
| listed_stock | 5232 | 0 | 2026-05-26 |
| otc_stock | 2208 | 0 | 2026-05-26 |
| taiex_benchmark | 92 | 0 | 2026-05-26 |
| otc_benchmark | 92 | 0 | 2026-05-26 |

Latest-date check:

| check | result | notes |
|---|---|---|
| Four source latest_date values identical | Pass | All sources latest date was 2026-05-26. |
| Latest-date mismatch warning | N/A | No mismatch warning was emitted. |

## 5. Context Validation

| field | value |
|---|---:|
| total_json_count | 26 |
| valid_count | 26 |
| invalid_count | 0 |

Validation method:

```text
All generated .json files were validated with StockAdviceContext.model_validate.
```

## 6. Streamlit Manual Inspection

Streamlit fake/demo inspection used the generated context folder:

```text
data/pilot_contexts/official_pilot_2026-05-27
```

| check | result | notes |
|---|---|---|
| Streamlit launched locally | Inspected | Manual browser inspection completed during UAT. |
| `fake/demo` selected | Pass | Fake/demo mode was selected. |
| `folder path` selected | Pass | Generated context folder path was used. |
| max batch size >= 20 | Pass | Set to 50. |
| batch run completed | Pass | Batch metrics displayed 26 rows. |
| actionable candidates displayed | Pass | 17 actionable candidates. |
| ranked table displayed | Pass | Ranked table rendered with candidate rows. |
| detail view displayed `final_advice` | Pass | Detail sections showed conclusion, core reasons, bull/bear case, entry, stop loss, take profit, invalidation, next-session confirmation, and data quality warnings. |
| blocked rows visible or toggle available | Pass | `show blocked rows` toggle was available and checked. |
| warnings and guardrail reasons inspectable | Pass | Table included `guardrail_reasons`; detail view showed data quality warnings. |

## 7. JSONL Inventory

The scanner CLI must not create or modify `reports/ai_advice/*.jsonl`. Inventory was captured before scanner, after scanner, and after Streamlit.

Before scanner:

| file | exists | line_count | bytes | sha256 |
|---|---|---:|---:|---|
| `reports/ai_advice/ai_advice_log.jsonl` | true | 17 | 12574 | `cc8f3f6ec96e90f9a6a32fbc0f22e41c88e9a6233498a037bb848900586b5a12` |
| `reports/ai_advice/ai_advice_evaluation.jsonl` | false | 0 | 0 | N/A |

After scanner:

| file | exists | line_count | bytes | sha256 |
|---|---|---:|---:|---|
| `reports/ai_advice/ai_advice_log.jsonl` | true | 17 | 12574 | `cc8f3f6ec96e90f9a6a32fbc0f22e41c88e9a6233498a037bb848900586b5a12` |
| `reports/ai_advice/ai_advice_evaluation.jsonl` | false | 0 | 0 | N/A |

Scanner JSONL comparison:

| check | result | notes |
|---|---|---|
| scanner CLI created JSONL logs | No | Evaluation log remained absent. |
| scanner CLI modified existing JSONL line_count | No | Advice log stayed at 17 lines. |
| scanner CLI modified existing JSONL sha256 | No | Advice log sha256 was unchanged. |

After Streamlit:

| file | exists | line_count | bytes | sha256 |
|---|---|---:|---:|---|
| `reports/ai_advice/ai_advice_log.jsonl` | true | 43 | 31792 | `1ed3411a0fc071280d535c431d7a8a93c6cc51bb5f66a34ea5bba540f4570b4b` |
| `reports/ai_advice/ai_advice_evaluation.jsonl` | false | 0 | 0 | N/A |

Streamlit logging note:

| check | result | notes |
|---|---|---|
| Streamlit batch appended advice log | Yes | Fake/demo batch appended 26 UAT advice lines to the ignored advice log. |
| Evaluation log appended | No | No follow-up CSV processing was performed. |
| JSONL committed | No | JSONL files are ignored and were not committed. |

## 8. Go Decision

```text
Go
```

Formal Scanner Pilot UAT passes. The scanner produced at least 20 valid contexts, all generated contexts validated as `StockAdviceContext`, scanner CLI did not mutate JSONL logs, and Streamlit fake/demo inspection displayed the ranked table and final advice detail flow.

## 9. Residual Risks

| risk | note |
|---|---|
| market_scan fallback | All 26 output contexts carried `theme lifecycle unknown; market_scan fallback used`, so theme lifecycle remains fallback-quality evidence. |
| no official limit-up flag | Official same-day limit-up flag was unavailable in the pilot raw inputs, so limit-up handling remains limited by source availability. |
| UAT advice log mixed with rehearsal lines | Existing ignored `ai_advice_log.jsonl` had 17 lines before UAT and 43 lines after Streamlit, so the local log contains both pre-UAT rehearsal lines and formal UAT fake/demo append lines. |

