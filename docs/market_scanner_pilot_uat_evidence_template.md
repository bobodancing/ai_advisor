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

Record the exact four local aggregate raw file paths and raw file audit metadata before running the scanner CLI.

| source | path | exists | bytes | sha256 | last_modified_utc | operator notes |
|---|---|---|---:|---|---|---|
| listed stock daily raw file |  |  |  |  |  |  |
| OTC stock daily raw file |  |  |  |  |  |  |
| TAIEX benchmark raw file |  |  |  |  |  |  |
| OTC benchmark raw file |  |  |  |  |  |  |

Optional local raw file audit helper:

```powershell
$files = [ordered]@{
  listed_stock = "<listed_stock_daily_raw_file>"
  otc_stock = "<otc_stock_daily_raw_file>"
  taiex_benchmark = "<taiex_benchmark_raw_file>"
  otc_benchmark = "<otc_benchmark_raw_file>"
}

$files.GetEnumerator() | ForEach-Object {
  if (Test-Path -LiteralPath $_.Value) {
    $item = Get-Item -LiteralPath $_.Value
    [PSCustomObject]@{
      source = $_.Key
      path = $item.FullName
      exists = $true
      bytes = $item.Length
      sha256 = (Get-FileHash -Algorithm SHA256 -Path $item.FullName).Hash.ToLowerInvariant()
      last_modified_utc = $item.LastWriteTimeUtc.ToString("o")
    }
  } else {
    [PSCustomObject]@{
      source = $_.Key
      path = $_.Value
      exists = $false
      bytes = $null
      sha256 = $null
      last_modified_utc = $null
    }
  }
} | ConvertTo-Json -Depth 3
```

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
| four source latest_date values identical? |  |  |
| if mismatched, warning copied exactly |  |  |
| if identical, marked `N/A / no mismatch` |  |  |
| operator reviewed mismatch before Streamlit run |  |  |

Reminder: if the four source `latest_date` values are not identical, copy the scanner warning exactly. If they are identical, fill `N/A / no mismatch`. Do not infer a trading calendar, do not fabricate missing market data, and do not treat the warning as downloader approval.

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

## 7. Context Validation

Validate every generated `.json` file in the output folder as `StockAdviceContext`. Record the aggregate counts before any Streamlit run.

| field | value |
|---|---|
| total_json_count |  |
| valid_count |  |
| invalid_count |  |
| validation command used |  |

Required all-context validation helper:

```powershell
$env:CONTEXT_DIR = "<output_folder>"
@'
import json
import os
from pathlib import Path

from ai_advisor.schemas import StockAdviceContext

folder = Path(os.environ["CONTEXT_DIR"])
paths = sorted(folder.glob("*.json"))
invalid = []

for path in paths:
    try:
        StockAdviceContext.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:
        invalid.append({"path": str(path), "error": str(exc).splitlines()[0]})

result = {
    "folder": str(folder),
    "total_json_count": len(paths),
    "valid_count": len(paths) - len(invalid),
    "invalid_count": len(invalid),
    "invalid_samples": invalid[:10],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(1 if invalid else 0)
'@ | python -
```

Manual sample spot-check: choose any three generated context JSON files and validate or inspect them as `StockAdviceContext`.

| sample | context path | validation result | notes |
|---:|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

Optional three-sample validation helper:

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

Important: `reports/ai_advice/*.jsonl` files are gitignored, so `git status --short -- reports/ai_advice` is not sufficient evidence of log integrity. Record a JSONL inventory before the scanner CLI, after the scanner CLI, and after the Streamlit run. Compare `line_count` and `sha256` across inventories.

JSONL inventory helper:

```powershell
@'
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path.cwd()
log_dir = root / "reports" / "ai_advice"
expected = [
    log_dir / "ai_advice_log.jsonl",
    log_dir / "ai_advice_evaluation.jsonl",
]
discovered = sorted(log_dir.glob("*.jsonl")) if log_dir.exists() else []
paths = sorted({*expected, *discovered}, key=lambda path: str(path))

inventory = []
for path in paths:
    if path.exists():
        data = path.read_bytes()
        stat = path.stat()
        inventory.append({
            "exists": True,
            "path": str(path),
            "bytes": len(data),
            "line_count": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0),
            "sha256": hashlib.sha256(data).hexdigest(),
            "last_modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    else:
        inventory.append({
            "exists": False,
            "path": str(path),
            "bytes": None,
            "line_count": None,
            "sha256": None,
            "last_modified_utc": None,
        })

print(json.dumps(inventory, ensure_ascii=False, indent=2))
'@ | python -
```

Before scanner CLI JSONL inventory:

```json

```

After scanner CLI JSONL inventory:

```json

```

Scanner CLI JSONL comparison:

| check | result | notes |
|---|---|---|
| scanner CLI created JSONL logs? |  | Must be `No` unless investigating an unexpected failure |
| scanner CLI modified existing JSONL `line_count`? |  | Must be `No` |
| scanner CLI modified existing JSONL `sha256`? |  | Must be `No` |

After Streamlit run JSONL inventory:

```json

```

Streamlit batch logging note:

| check | result | notes |
|---|---|---|
| Streamlit batch appended advice log? |  | Record explicitly if yes |
| If Streamlit appended advice log, `line_count` change recorded? |  |  |
| If Streamlit appended advice log, `sha256` change recorded? |  |  |
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
