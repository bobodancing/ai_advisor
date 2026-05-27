# Human-Pending Decisions

| id | date | status | blocking_area | decision_needed | options | recommended_default | resolution | resolved_at |
|---|---|---|---|---|---|---|---|---|
| HP-001 | 2026-05-24 | resolved | market_data_scanner | Choose long-term product direction for market data source. | A: official TWSE / TPEx after-market public data; B: broker/vendor export; C: local raw market-data files only | A | A: official TWSE / TPEx after-market public data | 2026-05-24 |
| HP-002 | 2026-05-24 | resolved | market_data_scanner | Choose first implementation adapter path. | A: official downloader first; B: local raw file adapter first, then downloader; C: manual CSV only | B | B: local raw file adapter first, then official downloader | 2026-05-24 |
| HP-003 | 2026-05-27 | resolved | market_data_scanner | 是否允許一次性官方資料準備 helper 進行 network fetch，為 watchlist 產生 local aggregate raw CSV？ | A 手動提供四源 raw CSV; B 一次性官方資料準備 helper; C production downloader | B | B | 2026-05-27 |
