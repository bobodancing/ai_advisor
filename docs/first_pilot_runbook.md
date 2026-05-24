# AI Advisor v1.2.1 First Pilot Runbook

This runbook is for the first personal after-market pilot of AI Advisor v1.2.1.

Safety reminder:

```text
交易決策輔助，不是保證獲利或下單指令。
```

Use the system to organize candidate review and later evaluate 5-trading-day alpha. Do not treat any output as guaranteed profit or an automatic order instruction.

## 1. Preflight Checks

1. Confirm the working tree is on the intended release:

```bash
git status --short --branch
git show --no-patch --format="%H %D %s" v1.2.1^{}
```

Expected release commit:

```text
93625075ba0b502f4fe809cbf1ecd348c9097146
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Optional confidence check before a pilot:

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py
```

4. Confirm generated logs are not committed:

```bash
git ls-files reports/ai_advice
```

Expected tracked file:

```text
reports/ai_advice/.gitkeep
```

## 2. Dry Run vs Official Pilot

Treat fixture checks, automation-assisted browser runs, and operator rehearsal runs as dry runs. Dry runs may append valid snapshots to the append-only advice log, and that is expected behavior.

For the first official pilot, start from a clean `reports/ai_advice` state or from a state where previous pilot artifacts have already been archived outside the repository. If `reports/ai_advice/ai_advice_log.jsonl` already exists, do not delete it casually. Manually back it up or move it to a private archive outside the Git repository before starting the official pilot.

The committed repository should still track only:

```text
reports/ai_advice/.gitkeep
```

## 3. Start Streamlit

From the repository root:

```bash
python -m streamlit run apps/ai_advisor_streamlit.py
```

For operator-led pilots, this equivalent launch command avoids the first-run browser/email prompt:

```bash
python -m streamlit run apps/ai_advisor_streamlit.py --server.headless true --browser.gatherUsageStats false
```

Open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

Confirm the safety notice is visible.

## 4. Select Fake/Demo Mode

In the sidebar:

1. Choose `fake/demo`.
2. Keep `show blocked rows` enabled for the first review pass.
3. Keep `max batch size` at `20` or higher.

For v1.2.1, `real LLM` mode is guard-only. It can show API key status, estimated calls, and max-call blocking, but it must not execute a real LLM API call.

## 5. Load Contexts

For a fixture pilot:

1. Choose `folder path`.
2. Enter:

```text
tests/fixtures/ai_advisor/stock_contexts
```

3. Click `Run batch advice`.

For a real after-market pilot:

1. Prepare a folder of structured UTF-8 `StockAdviceContext` JSON files.
2. Confirm each file uses structured JSON, not Markdown.
3. Choose `folder path`.
4. Enter the real context folder path.
5. Click `Run batch advice`.

## 6. Check Batch Results

In `Batch Results`:

1. Confirm rows are sorted by the fixed v1.2 ranking.
2. Review `grade`, `recommendation`, `confidence`, `was_blocked`, and `guardrail_reasons`.
3. Use grade and recommendation filters to focus on actionable candidates.
4. Treat actionable candidates as:

```text
grade in ["A", "B"]
recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
```

5. Keep blocked rows visible during the first pilot so data quality and guardrail behavior are easy to audit.

## 7. Inspect Stock Detail

In `Stock Detail`:

1. Select one candidate from the loaded batch.
2. Review the conclusion and core reasons.
3. Check bull case and bear case.
4. Confirm entry plan, stop loss, take profit, invalidation, and next-session confirmation.
5. Read data quality warnings before making any manual trading decision.

Only use `final_advice` as the product recommendation. Raw advice is retained for auditability but is not the final user-facing recommendation.

## 8. Retain Advice Logs

Advice snapshots are generated locally at:

```text
reports/ai_advice/ai_advice_log.jsonl
```

Pilot handling rules:

- Keep this file as the immutable advice snapshot for that pilot run.
- Do not edit, reorder, deduplicate, or rewrite historical advice rows.
- Do not commit generated `.jsonl` logs to Git.
- If you need an external pilot archive, store a copy outside the repository or in a private non-Git location with the pilot date in the filename.

The alpha placeholder fields inside advice snapshots should remain `null` at advice creation time.

## 9. Pilot Metrics Reporting

Because advice logs are append-only, Streamlit reruns can create multiple snapshots for the same context. Official pilot notes should report both raw log volume and unique context volume:

- `jsonl_line_count`: total non-empty lines in `reports/ai_advice/ai_advice_log.jsonl`.
- `unique_context_count`: unique `stock_id + advice_date + input_context_hash` rows.
- `duplicate_snapshot_count`: `jsonl_line_count - unique_context_count`.
- `blocked_unique_count`: blocked rows counted after de-duplicating by `stock_id + advice_date + input_context_hash`.
- `actionable_unique_candidate_count`: unique rows where `grade in ["A", "B"]`, `recommendation in ["wait_pullback", "small_probe"]`, and `was_blocked == false`.
- `complete_followup_count`: actionable unique candidates with complete follow-up evaluation records.

## 10. Prepare Follow-Up CSV After 5 Trading Days

After the 5th trading day close, prepare a CSV with:

```csv
stock_id,advice_date,close_5d,benchmark_return_5d_pct
3017,2026-05-23,130.0,1.2
```

Rules:

- `close_5d` is the stock close on the 5th trading day after advice.
- `benchmark_return_5d_pct` must already be calculated versus the correct market benchmark.
- v1.2.1 does not infer trading calendars.
- Rows missing `benchmark_return_5d_pct` are excluded from the main alpha denominator and should be reviewed as data quality gaps.

## 11. Import Follow-Up CSV

In Streamlit:

1. Confirm the original `reports/ai_advice/ai_advice_log.jsonl` for the pilot is present.
2. Upload the follow-up CSV in the sidebar.
3. Open `Alpha Evaluation`.
4. Click `Process follow-up CSV`.
5. Confirm evaluation records are appended to:

```text
reports/ai_advice/ai_advice_evaluation.jsonl
```

The evaluation step must not mutate `reports/ai_advice/ai_advice_log.jsonl`.

## 12. Interpret Alpha Hit Rate

Main metric:

```text
alpha_hit_rate_5d_vs_market =
  alpha_hit_5d true count among actionable candidates with complete follow-up /
  actionable candidates with complete follow-up
```

Interpretation:

- `alpha_5d_pct > 0` means the stock beat the provided benchmark return over the 5-trading-day horizon.
- `observe` rows are excluded from the main denominator.
- Blocked rows are excluded from actionable candidate evaluation.
- A small sample is directional only; review trade quality and data quality together.

## 13. Record Pilot Observations

After each pilot, record:

- pilot date and advice date,
- context folder used,
- `jsonl_line_count`,
- `unique_context_count`,
- `duplicate_snapshot_count`,
- `blocked_unique_count`,
- `actionable_unique_candidate_count`,
- `complete_followup_count`,
- top candidates reviewed manually,
- guardrail reasons the trader considered useful,
- guardrail reasons the trader considered questionable or needing PM review,
- any missing or suspicious context fields,
- whether any candidate was manually traded,
- follow-up CSV date after 5 trading days,
- alpha hit rate and average `alpha_5d_pct`,
- notes for Phase 2 only if they do not change v1.2 scope.

The CODEX operator is a pilot scribe only. The operator should not decide whether a guardrail reason is useful, questionable, or trade-relevant; record the trader's judgment without turning it into a buy/sell recommendation.

Keep Phase 2 ideas in `docs/phase2_backlog.md`; do not implement them during the v1.2 pilot.
