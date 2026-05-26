# Market Scanner Pilot Runbook

This runbook is for the v1.3 Market Scanner pilot readiness path.

The scanner pilot creates `StockAdviceContext` JSON files from local raw official-format market data files, then loads the generated context folder through the existing AI Advisor Streamlit fake/demo flow.

It is not a live downloader, not a network fetcher, not a scraper, and not production downloader approval.

## 1. Scope Boundary

Allowed:

- four aggregate local official-format raw files,
- deterministic local parsing,
- deterministic scanner indicators, filters, and scoring,
- generated `StockAdviceContext` JSON files,
- existing Streamlit fake/demo batch advice flow.

Not allowed:

- live market data download,
- network fetch,
- scraping,
- one-file-per-date folder orchestration,
- changes to v1.2 guardrails, ranking, logging, evaluation denominator, benchmark mapping, Streamlit behavior, or Real LLM scope.

## 2. Required Input Shape

Prepare exactly four aggregate local files:

```text
listed stock daily raw file
OTC stock daily raw file
TAIEX benchmark raw file
OTC benchmark raw file
```

Each file should contain at least 60 sessions for the scanner pilot universe or benchmark series. The scanner groups stock rows by `market_type + stock_id`, maps listed stocks to `TAIEX`, maps OTC stocks to `OTC`, and writes context JSON files only when `--output` is provided.

The raw files may be CSV or JSON as supported by the local raw adapter. They must already exist on disk before the scanner command runs.

## 3. Install

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 4. Generate Contexts

Example local-only command:

```bash
python -m ai_advisor.market_scanner.scanner \
  --listed-stock-file data/raw_market/2026-05-24/listed_stock_daily.csv \
  --otc-stock-file data/raw_market/2026-05-24/otc_stock_daily.csv \
  --taiex-benchmark-file data/raw_market/2026-05-24/taiex_benchmark.csv \
  --otc-benchmark-file data/raw_market/2026-05-24/otc_benchmark.csv \
  --output data/pilot_contexts/2026-05-24 \
  --max-output 50
```

Expected command behavior:

- reads only the four local files,
- groups stock rows by market and stock id,
- uses `TAIEX` for listed stocks and `OTC` for OTC stocks,
- writes generated context JSON files to the output folder,
- prints a JSON summary with input count, output count, skipped count, warnings, skip reasons, penalty counts, and per-source raw audit metadata.

The JSON summary includes `source_audit` for:

```text
listed_stock
otc_stock
taiex_benchmark
otc_benchmark
```

For each source, check:

```text
record_count
skipped_row_count
raw_skip_reason_counts
latest_date
```

If the four source `latest_date` values are not identical, the scanner adds a deterministic warning. The pilot treats this as warning-only: it does not infer a trading calendar, does not exit non-zero, and does not block context generation. The operator should record the mismatch before using the generated folder.

If fewer than 20 contexts are generated, review the printed warnings and skip reasons. Do not fabricate missing market facts to reach 20.

## 5. Python API

The CLI is a thin wrapper over the local-only Python API:

```python
from ai_advisor.market_scanner import scan_local_raw_market_data
from ai_advisor.market_scanner.schemas import ScannerConfig

result = scan_local_raw_market_data(
    listed_stock_file="data/raw_market/2026-05-24/listed_stock_daily.csv",
    otc_stock_file="data/raw_market/2026-05-24/otc_stock_daily.csv",
    taiex_benchmark_file="data/raw_market/2026-05-24/taiex_benchmark.csv",
    otc_benchmark_file="data/raw_market/2026-05-24/otc_benchmark.csv",
    config=ScannerConfig(max_output=50, min_output_warning_threshold=20),
    output_dir="data/pilot_contexts/2026-05-24",
)
```

## 6. Load Generated Contexts In Streamlit

Start Streamlit:

```bash
python -m streamlit run apps/ai_advisor_streamlit.py
```

In the sidebar:

1. Select `fake/demo`.
2. Select `folder path`.
3. Enter the generated context folder, for example:

```text
data/pilot_contexts/2026-05-24
```

4. Keep `max batch size` at `20` or higher.
5. Click `Run batch advice`.
6. Review `Batch Results` and inspect candidate details.

Manual Streamlit browser UAT remains separate from the automated scanner integration test. Report browser inspection as `[inspected]`.

Use `docs/market_scanner_pilot_uat_evidence_template.md` to record manual pilot evidence consistently.

## 7. Log Integrity

The scanner command writes context JSON files only. It must not create, edit, reorder, deduplicate, or mutate:

```text
reports/ai_advice/ai_advice_log.jsonl
reports/ai_advice/ai_advice_evaluation.jsonl
```

Those logs are created or appended only by the existing AI Advisor advice and follow-up evaluation flows.

## 8. Pilot Checklist

- Four local aggregate raw files are present.
- Each file has enough history for MA60 / RS60 logic.
- `python -m ai_advisor.market_scanner.scanner --help` works.
- Scanner command prints a local summary and writes context JSON files.
- `source_audit` is reviewed for each source.
- Raw skipped rows and `raw_skip_reason_counts` are reviewed.
- Four source `latest_date` values are checked; any mismatch warning is recorded.
- Generated folder contains at least 20 valid contexts for a pilot-sized input set.
- Streamlit fake/demo loads the generated folder and shows a ranked table.
- Manual UAT evidence is recorded in `docs/market_scanner_pilot_uat_evidence_template.md` or a private copy of that template.
- No downloader, network fetch, scraping, or one-file-per-date orchestration was used.
