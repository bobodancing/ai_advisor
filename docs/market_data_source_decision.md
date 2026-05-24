# Market Data Source Decision

Status: accepted / Gate 0 resolved
Related: `humanpending.md`, `docs/market_data_scanner_v1_3_plan.md`

This ADR records the market data source decision for the v1.3 Market Data Scanner.

---

## Context

AI Advisor v1.2.x starts from `StockAdviceContext` JSON files. The user currently has no context folder and no after-market CSV.

Therefore v1.3 needs an upstream Market Data Scanner that can obtain or ingest after-market market data, calculate deterministic features, and write context JSON files.

The scanner should not begin with brittle scraping or paid-provider assumptions.

---

## Decision Summary

Resolved on: 2026-05-24

```text
HP-001 = A
Long-term product direction uses official TWSE / TPEx after-market public data.

HP-002 = B
First implementation starts with a local raw market-data file adapter, then adds the official downloader after source behavior is verified.
```

The local raw adapter is not a permanent manual-data requirement. It is the first engineering step that lets scanner logic, indicators, filters, and context writing be tested against official-format raw data before live download behavior is added.

---

## Decision 1: Product Direction Data Source

Options:

```text
A. official TWSE / TPEx after-market public data
B. broker/vendor export
C. local raw market-data files only
```

Recommended product direction:

```text
A. official TWSE / TPEx after-market public data
```

Reason:

- aligns with Taiwan market coverage,
- avoids broker-specific lock-in,
- supports repeatable after-market scanning,
- keeps scanner read-only.

Status:

```text
accepted: A
```

---

## Decision 2: First Implementation Path

Options:

```text
A. implement official downloader first
B. implement local raw file adapter first, then downloader
C. require manual CSV forever
```

Recommended first implementation:

```text
B. implement local raw file adapter first, then downloader
```

Reason:

- separates scanner logic from data-source instability,
- lets tests validate indicators, filters, scoring, and context writing first,
- reduces risk from official endpoint format changes,
- still preserves official data as the product direction.

Status:

```text
accepted: B
```

---

## Initial Official Source Candidates

Initial source check performed on 2026-05-24 found reachable official candidates. These candidates make the source direction feasible, but they are not yet a completed source contract.

Listed stock daily price candidate:

```text
https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
Observed fields include:
Date, Code, Name, TradeVolume, TradeValue, OpeningPrice, HighestPrice,
LowestPrice, ClosingPrice, Change, Transaction
```

OTC stock daily price candidate:

```text
https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes
Observed fields include:
Date, SecuritiesCompanyCode, CompanyName, Close, Change, Open, High, Low,
TradingShares, TransactionAmount, TransactionNumber, NextReferencePrice,
NextLimitUp, NextLimitDown
```

Listed benchmark candidates:

```text
https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX
https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST
```

OTC benchmark candidates:

```text
https://www.tpex.org.tw/openapi/v1/tpex_index
https://www.tpex.org.tw/openapi/v1/tpex_daily_trading_index
```

Known certification gaps before live downloader implementation:

- obtain enough historical sessions for MA60 and relative-strength windows,
- filter ordinary listed / OTC stocks from ETFs, bonds, warrants, and other instruments,
- choose the canonical TAIEX benchmark source and OTC benchmark source,
- verify limit-up / limit-down parity for listed and OTC stocks,
- normalize ROC calendar dates and Gregorian dates,
- normalize numeric strings with commas, signs, blanks, and special text,
- verify after-market update timing and failure modes,
- record source samples as fixtures and protect them with source-contract tests.

---

## Required Source Verification Before Downloader

Before coding an official downloader, verify current behavior for:

- listed stock daily prices,
- OTC stock daily prices,
- TAIEX daily benchmark series,
- OTC daily benchmark series,
- stock name and market type mapping,
- limit-up / limit-down availability,
- file encoding and numeric formats,
- update timing after market close,
- historical range availability,
- rate limits or anti-automation constraints.

Record source URLs, sample files, and observed columns before implementation.
