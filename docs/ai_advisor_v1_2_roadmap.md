# AI Advisor v1.2 Roadmap

Project: Streamlit 批次個股 Alpha Finder

Roadmap owner: 產品統籌 / PM

Created: 2026-05-23

Target MVP release: 2026-06-12

---

## 1. Roadmap 原則

v1.2 只交付 `Stock Trade Advice Batch`。任何 `Daily AI Advice`、`Risk Review`、行情下載、交易日曆推斷、自動下單、資料庫、auth、多 provider，都不進 v1.2。

交付順序固定：

```text
Session F: Stock Batch Core
-> Session G: Streamlit MVP
-> Session H: Follow-up Evaluation
-> Hardening / Release Review
```

每個階段都必須符合 `AGENTS.md` 與 `ai_advisor_module_spec_v1_2_product_ready.md`。

---

## 2. Milestone Timeline

| Milestone | Deadline | Owner | Exit Criteria | Status |
|---|---:|---|---|---|
| M0 - Kickoff Readiness | 2026-05-24 | PM + Codex | 新 session 讀完 `AGENTS.md` 與 v1.2 spec，確認只做 Session F | Not started |
| M1 - Session F Stock Batch Core | 2026-05-29 | Codex | schema、fake client、balanced guardrails、batch engine、ranking、immutable advice log 完成且測試通過 | Not started |
| M2 - Session F Review / Fix Buffer | 2026-05-31 | PM + Codex | 修完 M1 review findings，無 High/Medium blocker | Not started |
| M3 - Session G Streamlit MVP | 2026-06-05 | Codex | Streamlit 可載入 20+ fixtures、fake/demo mode、real LLM guard、結果表、詳情頁 | Not started |
| M4 - Session H Follow-up Evaluation | 2026-06-09 | Codex | follow-up CSV 讀取、evaluation JSONL、5 trading day alpha hit rate 完成 | Not started |
| M5 - Release Hardening | 2026-06-11 | PM + Codex | 完整相關測試通過，文件與 DoD 對齊，無 scope creep | Not started |
| M6 - v1.2 MVP Go/No-Go | 2026-06-12 | PM | 決定可否進入個人盤後試用 | Not started |

---

## 3. Session F - Stock Batch Core

Deadline: 2026-05-29

### Scope

- 建立 stock-only schema。
- 建立 fake/demo LLM client。
- 建立 balanced guardrails。
- 建立 batch engine。
- 建立 fixed ranking function。
- 建立 immutable advice JSONL logger。

### Required Behaviors

- `market_type` missing 或 `unknown` 不失敗，預設 TAIEX 並加 warning。
- `small_probe` 需要 `risk_reward_ratio >= 1.5`。
- `A` 需要 `risk_reward_ratio >= 2.0`。
- `is_overheated = true` 不可 `small_probe`。
- `late_stage` 不可 A，但可 `wait_pullback`。
- `fading / broken` 必須降為 `avoid_chasing` 或 `reject`。
- Restricted terms 有 evidence 不 block，無 evidence block。
- 單檔 validation / LLM failure 不可中斷 batch。
- Advice log alpha placeholder 欄位建立時必須是 `null`。

### Acceptance Commands

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
```

### PM Review Checklist

- 沒有實作 Daily / Risk / 行情下載。
- 沒有改 alpha denominator。
- 沒有讓 prompt 取代 deterministic guardrails。
- Ranking 符合 AGENTS.md 固定順序。
- Advice log 不會在 evaluation 階段被 mutation。

---

## 4. Session G - Streamlit MVP

Deadline: 2026-06-05

### Scope

- 建立 `apps/ai_advisor_streamlit.py`。
- 支援 upload JSON files 或 folder path。
- 支援 fake/demo mode 與 real LLM mode。
- 顯示 estimated LLM calls 與 max call guard。
- 顯示 Batch Results、Stock Detail、Alpha Evaluation views。
- 結果表支援排序、篩選、點選單檔詳情。

### Required Behaviors

- fake/demo mode 不需要 secrets。
- real LLM mode 缺 `OPENAI_API_KEY` 不可 crash。
- 超過 `max_llm_calls_per_run` 必須禁止送出。
- 頁面顯示免責文字：`交易決策輔助，不是保證獲利或下單指令。`
- blocked/error rows 可顯示，但不可中斷整批。

### Automated Acceptance

```bash
pytest tests/test_ai_advisor_streamlit_smoke.py
```

### Manual Verification

```bash
streamlit run apps/ai_advisor_streamlit.py
```

Manual verification 必須：

1. 啟動 server。
2. 開啟顯示的 local URL。
3. 檢查 sidebar controls、Batch Results、Stock Detail、Alpha Evaluation。
4. 停止 server process。
5. 在回報中標記為 `[inspected]`，不是 automated acceptance。

---

## 5. Session H - Follow-up Evaluation

Deadline: 2026-06-09

### Scope

- 建立 follow-up CSV reader。
- 建立 `ai_advice_evaluation.jsonl` append-only evaluation log。
- 計算 `stock_return_5d_pct`、`alpha_5d_pct`、`alpha_hit_5d`。
- 計算 `alpha_hit_rate_5d_vs_market`。
- 缺 follow-up 或 benchmark return 時顯示 warning。

### Required Behaviors

- 讀取 `ai_advice_log.jsonl`，但不得 mutate。
- evaluation record append 到 `reports/ai_advice/ai_advice_evaluation.jsonl`。
- 可行動候選分母只包含：

```text
grade in ["A", "B"]
recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
```

- `observe` 不進主分母。
- 缺 `benchmark_return_5d_pct` 不進分母，並顯示 warning。
- 5 日指 5 trading days，由 CSV 保證，系統不推斷交易日曆。

### Acceptance Commands

```bash
pytest tests/test_ai_advisor_evaluator.py
```

---

## 6. Release Hardening

Deadline: 2026-06-11

### Required Checks

```bash
pytest tests/test_ai_advisor_schemas.py \
       tests/test_ai_advisor_guardrails.py \
       tests/test_ai_advisor_batch.py \
       tests/test_ai_advisor_evaluator.py \
       tests/test_ai_advisor_streamlit_smoke.py
```

### Release Review Checklist

- `AGENTS.md` rules obeyed。
- v1.2 spec DoD met。
- No secrets committed。
- Streamlit app is primary entry point。
- fake/demo mode can process at least 20 fixture stocks。
- real LLM mode has API key check and max-call guard。
- Results table supports ranking/filter/detail inspection。
- Single-stock failures do not interrupt batch。
- Advice snapshot log immutable。
- Evaluation log separate and append-only。
- `observe` excluded from alpha denominator。
- Phase 2 ideas recorded only in `docs/phase2_backlog.md`。

---

## 7. Go / No-Go

Deadline: 2026-06-12

### Go Criteria

- All release hardening checks pass。
- No High or Medium product blocker remains。
- PM can run fake/demo mode on 20+ fixtures。
- PM can inspect one stock detail from the table。
- PM can import follow-up CSV and see alpha hit rate。

### No-Go Criteria

- Any deterministic guardrail is only enforced by prompt。
- Ranking differs from AGENTS.md。
- Advice log is mutated by evaluation。
- Follow-up alpha denominator includes `observe`。
- Streamlit cannot load fixture folder。
- Batch failure in one stock stops the entire run。

---

## 8. Phase 2 Parking Lot

Phase 2 items must be recorded in:

```text
docs/phase2_backlog.md
```

Known Phase 2 candidates:

- Daily AI Advice
- Risk Review
- 行情下載與交易日曆
- 板塊基準 alpha
- 人工回饋 UI
- 交易計畫版本比較
- 多 provider 支援

Do not implement these before v1.2 Go/No-Go.

---

## 9. Current Project Status

As of 2026-05-23:

- Product spec v1.2 exists。
- `AGENTS.md` is approved for implementation governance。
- Roadmap is created。
- Implementation has not started。

Next action:

```text
Open a new Codex session and request Session F - Stock Batch Core only.
```
