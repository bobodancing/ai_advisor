# Market Scanner Pilot UAT Evidence Template

This is a manual UAT evidence template for the v1.3 Market Scanner local raw pilot flow.

It is not an automated test, not downloader approval, and not evidence that live market-data fetching is production-ready. The pilot input remains four aggregate local official-format raw files only.

## 1. Pilot Metadata

| field | value |
|---|---|
| pilot_date |  |
| operator |  |
| repository_commit |  |
| Python version |  |
| environment notes |  |

## 2. Scope Confirmation

| check | result | notes |
|---|---|---|
| No downloader used |  |  |
| No network fetch used |  |  |
| No scraping used |  |  |
| No one-file-per-date orchestration used |  |  |
| v1.2 guardrails/ranking/logging/evaluation denominator/benchmark mapping unchanged |  |  |
| Streamlit runtime behavior unchanged |  |  |
| Real LLM scope unchanged |  |  |

## 3. Local Raw Inputs

Record the exact four local aggregate raw file paths.

| source | path | exists | operator notes |
|---|---|---|---|
| listed stock daily raw file |  |  |  |
| OTC stock daily raw file |  |  |  |
| TAIEX benchmark raw file |  |  |  |
| OTC benchmark raw file |  |  |  |

## 4. CLI Command

Paste the exact command used:

```bash

```

Expected shape:

```bash
python -m ai_advisor.market_scanner.scanner \
  --listed-stock-file <listed_stock_daily_raw_file> \
  --otc-stock-file <otc_stock_daily_raw_file> \
  --taiex-benchmark-file <taiex_benchmark_raw_file> \
  --otc-benchmark-file <otc_benchmark_raw_file> \
  --output <generated_context_output_folder> \
  --max-output 50
```

CLI exit code:

```text

```

## 5. CLI Summary Evidence

Copy the scanner JSON summary fields here.

| field | value |
|---|---|
| input_candidate_count |  |
| output_context_count |  |
| skipped_count |  |
| warnings |  |
| skip_reason_counts |  |
| penalty_counts |  |

Source audit:

| source | record_count | skipped_row_count | raw_skip_reason_counts | latest_date |
|---|---:|---:|---|---|
| listed_stock |  |  |  |  |
| otc_stock |  |  |  |  |
| taiex_benchmark |  |  |  |  |
| otc_benchmark |  |  |  |  |

Latest-date mismatch:

| check | result | notes |
|---|---|---|
| source latest_date mismatch warning present? |  |  |
| warning copied exactly |  |  |
| operator reviewed mismatch before Streamlit run |  |  |

Reminder: latest-date mismatch is warning-only for this local pilot. Do not infer a trading calendar, do not fabricate missing market data, and do not treat the warning as downloader approval.

## 6. Generated Context Folder

| field | value |
|---|---|
| output context folder path |  |
| generated `.json` count |  |
| count command used, if any |  |

Optional local count command:

```bash
python -c "from pathlib import Path; print(len(list(Path(r'<output_folder>').glob('*.json'))))"
```

## 7. Sample Context Validation

Choose any three generated context JSON files and validate them as `StockAdviceContext`.

| sample | context path | validation result | notes |
|---:|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

Optional validation helper:

```bash
python -c "import json; from pathlib import Path; from ai_advisor.schemas import StockAdviceContext; [StockAdviceContext.model_validate(json.loads(Path(p).read_text(encoding='utf-8'))) for p in [r'<context1>', r'<context2>', r'<context3>']]; print('ok')"
```

## 8. Streamlit Manual UAT

Manual browser inspection is required for this section. Record it as `[inspected]`, not as automated pytest evidence.

| check | result | notes |
|---|---|---|
| Streamlit launched locally |  |  |
| `fake/demo` selected |  |  |
| `folder path` selected |  |  |
| generated context folder loaded |  |  |
| `max batch size` is at least 20 |  |  |
| batch run completed |  |  |
| ranked table displayed |  |  |
| detail view displayed `final_advice` |  |  |
| blocked rows are visible or can be shown |  |  |
| warnings / guardrail reasons can be inspected |  |  |

Paste the generated context folder path used in Streamlit:

```text

```

## 9. Log Integrity

The scanner CLI must not create or modify `reports/ai_advice/*.jsonl`.

Before scanner CLI:

```text
git status --short -- reports/ai_advice

```

After scanner CLI:

```text
git status --short -- reports/ai_advice

```

After Streamlit run:

```text
git status --short -- reports/ai_advice

```

Streamlit batch logging note:

| check | result | notes |
|---|---|---|
| scanner CLI produced or modified JSONL logs? |  | Must be `No` |
| Streamlit batch appended advice log? |  | Record explicitly if yes |
| If Streamlit appended logs, pilot log path recorded |  |  |
| If avoiding persistent pilot logs, test/output folder strategy recorded |  |  |

Pilot recommendation: for rehearsal runs, avoid mixing generated evidence with official pilot logs. If Streamlit appends to `reports/ai_advice/ai_advice_log.jsonl`, record that explicitly and keep generated `.jsonl` files out of Git.

## 10. Manual Outcome

Choose one:

```text
Go / Conditional Go / No-Go
```

Outcome:

```text

```

Blockers:

```text

```

Notes:

```text

```

Operator sign-off:

| field | value |
|---|---|
| reviewed_by |  |
| reviewed_at |  |
