# Market Data Source Decision

Status: draft / human-gated  
Related: `humanpending.md`, `docs/market_data_scanner_v1_3_plan.md`

This ADR records the market data source decision for the v1.3 Market Data Scanner.

---

## Context

AI Advisor v1.2.x starts from `StockAdviceContext` JSON files. The user currently has no context folder and no after-market CSV.

Therefore v1.3 needs an upstream Market Data Scanner that can obtain or ingest after-market market data, calculate deterministic features, and write context JSON files.

The scanner should not begin with brittle scraping or paid-provider assumptions.

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
open
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
open
```

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
