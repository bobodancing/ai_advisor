# Market Data Source Spike M6

Status: completed spike, not downloader implementation
Observed date: 2026-05-25
Related: `docs/market_data_source_decision.md`, `docs/market_data_scanner_v1_3_plan.md`, `docs/market_data_scanner_risk_register.md`

This document records observed behavior for official TWSE / TPEx candidate sources for the v1.3 Market Data Scanner.

This is a source behavior verification spike only. It is not a production downloader design, not a downloader usage manual, and not approval to add scheduling, brittle scraping, or market-data inference.

---

## Scope Guardrails

M6 did not change:

- v1.2 advice guardrails,
- v1.2 ranking,
- advice or evaluation JSONL logging,
- alpha denominator rules,
- benchmark mapping rules,
- Streamlit behavior,
- Real LLM scope.

M6 did not touch `reports/ai_advice/*.jsonl`.

Observation method:

- fetched official OpenAPI specs and public endpoints directly,
- checked default JSON behavior and `Accept: text/csv` behavior,
- recorded field names, dates, number formats, limit-price availability, and history length,
- added only small source-contract fixtures for local raw adapter parsing.

---

## Official Specs Checked

TWSE OpenAPI spec:

```text
https://openapi.twse.com.tw/v1/swagger.json
```

TPEx OpenAPI spec:

```text
https://www.tpex.org.tw/openapi/swagger.json
```

The checked candidate paths have no query parameters in the OpenAPI specs. Current no-parameter behavior therefore must be treated as a latest/current-period feed, not a complete historical downloader contract.

---

## Listed Stock Daily Prices

Candidate URL:

```text
https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 1362
distinct observed Date: 1150522
```

Observed JSON fields:

```text
Date
Code
Name
TradeVolume
TradeValue
OpeningPrice
HighestPrice
LowestPrice
ClosingPrice
Change
Transaction
```

Observed CSV behavior with `Accept: text/csv`:

```text
content-type: text/csv
headers:
日期, 證券代號, 證券名稱, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
```

Observed date format:

```text
ROC compact date, e.g. 1150522
```

Observed numeric format:

```text
numbers are strings
JSON sample values did not include thousands separators
CSV values are quoted strings
Change may be unsigned positive text such as 25.0000
```

Limit-up / limit-down:

```text
not present in observed STOCK_DAY_ALL fields
```

History sufficiency:

```text
not sufficient by itself for MA60 / RS60
observed feed was one trading date only
```

M6 assessment:

```text
Useful as a daily official-format listed stock snapshot.
Not sufficient as the only source for historical scanner features.
Needs official same-date validation and a separate strategy for historical accumulation.
Needs a separate listed limit-up/down source or deterministic approximation with warning.
Includes non-common instruments, so universe filtering remains required.
```

---

## OTC Stock Daily Prices

Candidate URL:

```text
https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 10357
distinct observed Date: 1150525
```

Observed JSON fields:

```text
Date
SecuritiesCompanyCode
CompanyName
Close
Change
Open
High
Low
Average
TradingShares
TransactionAmount
TransactionNumber
LatestBidPrice
LatesAskPrice
Capitals
NextReferencePrice
NextLimitUp
NextLimitDown
```

Observed CSV behavior with `Accept: text/csv`:

```text
content-type: text/csv
headers:
資料日期, 代號, 名稱, 收盤, 漲跌, 開盤, 最高, 最低, 均價, 成交股數, 成交金額, 成交筆數,
最後買價, 最後賣價, 發行股數, 次日參考價, 次日漲停價, 次日跌停價
```

Observed date format:

```text
ROC compact date, e.g. 1150525
```

Observed numeric format:

```text
numbers are strings
Change may include explicit plus sign, e.g. +71.00
CSV values are quoted strings
```

Limit-up / limit-down:

```text
NextLimitUp and NextLimitDown are present
```

History sufficiency:

```text
not sufficient by itself for MA60 / RS60
observed feed was one trading date only
```

M6 assessment:

```text
Useful as a daily official-format OTC snapshot.
Not sufficient as the only source for historical scanner features.
Has next-day limit price fields, but those must not be treated as official same-day limit-up flags.
Includes many non-common instruments, so universe filtering remains required.
```

---

## TAIEX Benchmark Series

Candidate URL A:

```text
https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 15
observed date range: 1150504 to 1150522
```

Observed fields:

```text
Date
OpeningIndex
HighestIndex
LowestIndex
ClosingIndex
```

Observed CSV headers with `Accept: text/csv`:

```text
日期, 開盤指數, 最高指數, 最低指數, 收盤指數
```

Candidate URL B:

```text
https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 267
distinct observed 日期: 1150522
```

Observed fields:

```text
日期
指數
收盤指數
漲跌
漲跌點數
漲跌百分比
特殊處理註記
```

Important parse note:

```text
For MI_INDEX, 漲跌 is a sign field and 漲跌點數 is the numeric change field.
The 發行量加權股價指數 row is the TAIEX row candidate.
```

Observed date formats:

```text
ROC compact date, e.g. 1150522
```

History sufficiency:

```text
not sufficient by itself for MA60 / RS60
MI_5MINS_HIST observed month-to-date only
MI_INDEX observed one trading date only
```

M6 assessment:

```text
MI_5MINS_HIST is the cleaner OHLC TAIEX series candidate but observed history is too short.
MI_INDEX is useful for same-day close/change cross-checking but is a multi-index table, not a long series.
A production downloader still needs verified historical accumulation behavior before scanner use.
```

---

## OTC Benchmark Series

Candidate URL A:

```text
https://www.tpex.org.tw/openapi/v1/tpex_index
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 16
observed date range: 20260504 to 20260525
```

Observed fields:

```text
Date
Open
High
Low
Close
Change
```

Observed CSV headers with `Accept: text/csv`:

```text
資料日期, 開市, 最高價, 最低價, 收市, 漲跌
```

Candidate URL B:

```text
https://www.tpex.org.tw/openapi/v1/tpex_daily_trading_index
```

Observed default JSON behavior:

```text
status: 200
content-type: application/json
rows: 16
observed date range: 1150504 to 1150525
```

Observed fields:

```text
Date
TradeVolume
TradeAmount
NumberOfTransactions
TPExIndex
Change
```

Observed CSV headers with `Accept: text/csv`:

```text
交易日期, 成交股數, 成交金額, 筆數, 櫃買指數, 漲跌
```

Observed date formats:

```text
tpex_index uses Gregorian compact date, e.g. 20260525
tpex_daily_trading_index uses ROC compact date, e.g. 1150525
```

History sufficiency:

```text
not sufficient by itself for MA60 / RS60
both observed feeds were current-month short series
```

M6 assessment:

```text
tpex_index is the cleaner OTC OHLC benchmark candidate.
tpex_daily_trading_index is useful if volume/value are needed, but has no OHLC fields.
Neither observed no-parameter endpoint is enough for MA60 / RS60 without historical accumulation.
```

---

## Cross-Source Observations

Encoding:

```text
JSON and CSV responses decoded as UTF-8.
CSV content-type did not include a charset in the observed responses.
Local raw adapter should keep using UTF-8 with BOM tolerance for saved fixtures.
```

Date normalization needed:

```text
ROC compact: 1150522
Gregorian compact: 20260525
Existing adapter normalization must support both.
```

Numeric normalization needed:

```text
numeric fields are strings
CSV fields may be quoted
some benchmark fields include comma thousands separators
stock Change may be +71.00, 25.0000, or - style text depending on source
MI_INDEX separates sign and numeric change across two fields
```

Same-date completeness risk:

```text
On 2026-05-25, observed TWSE stock / TAIEX candidates returned 1150522,
while observed TPEx stock / OTC candidates returned 1150525.

This may be update timing, market-calendar, or endpoint freshness behavior.
A production downloader must validate source dates before combining listed, OTC, TAIEX, and OTC snapshots.
```

History gap:

```text
The checked no-parameter OpenAPI candidates do not provide enough history for MA60 or RS60 in one call.
The downloader cannot assume these endpoints alone satisfy scanner history requirements.
```

---

## Source-Contract Fixtures Added

Small official-format fixtures were added to protect local raw adapter parsing:

```text
tests/fixtures/ai_advisor/market_scanner/listed_stock_day_all_official_csv_sample.csv
tests/fixtures/ai_advisor/market_scanner/otc_daily_close_quotes_official_csv_sample.csv
tests/fixtures/ai_advisor/market_scanner/taiex_mi_index_official_csv_sample.csv
tests/fixtures/ai_advisor/market_scanner/otc_index_official_csv_sample.csv
```

The fixtures are intentionally small and are not a market data cache.

Covered source-contract behaviors:

- official Chinese CSV headers,
- ROC compact date parsing,
- Gregorian compact date parsing,
- signed and unsigned numeric strings,
- comma thousands separators in benchmark change fields,
- TPEx next limit-up / next limit-down fields,
- MI_INDEX filtering to the TAIEX row,
- non-common instrument filtering for ETF-like codes.

---

## Gaps Before Downloader Implementation

The following remain unresolved and must not be hidden inside downloader code:

- verify how to obtain at least 60 trading sessions for listed and OTC stock OHLCV,
- verify how to obtain at least 60 trading sessions for TAIEX and OTC benchmarks,
- verify after-market update timing and stale-source behavior,
- enforce same-date completeness before generating a scanner snapshot,
- choose canonical TAIEX and OTC benchmark endpoints after history behavior is verified,
- find or reject an official listed limit-up / limit-down source,
- certify ordinary common-stock universe filtering beyond the current M1 heuristic,
- define cache naming and retention policy for official downloads,
- document retry/failure behavior without adding automatic scheduling.

M6 conclusion:

```text
Official source direction remains feasible, but the observed no-parameter endpoints are not enough
to implement a production downloader safely. Keep local raw official-format adapter as the scanner
contract until historical and update-timing behavior are verified.
```
