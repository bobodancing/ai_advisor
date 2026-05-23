# Release Hardening Review — 2026-05-23

**Findings**

沒有發現 High / Medium blocker。這輪 Release Hardening 可以過主管 review。

**Review 結論**

- `ci.yml` 符合要求：checkout、Python 3.11、install `requirements.txt`、跑 full relevant pytest set。

- `README.md` 也合格：有安裝、Streamlit 啟動、fixture flow、fake/demo、real LLM guard-only、follow-up CSV、測試、secrets/log 說明。

- `release_uat_checklist.md` 已把 UAT 補齊，並明確標 Real LLM API execution 不屬於 v1.2。

**Verification**

- [executed] `python -m pip install -r requirements.txt` 成功。
- [executed] `pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py` -> `30 passed`。
- [inspected] Streamlit server 可啟動，`http://localhost:8501` 回 `200`，已停止 server，port `8501` 關閉。
- [inspected] `reports/ai_advice` 仍只有 `.gitkeep`，沒有 JSONL 污染。
- [inspected] 搜尋 Real LLM 相關程式，未發現真實 API 呼叫被偷接進 v1.2。

**Residual Risk**

GitHub Actions 還需要在實際 push/PR 後看一次雲端 CI 綠燈；本地已驗證同一組指令可過。整體來看，這輪可以進 Go/No-Go 前最後確認。

**CI Cloud Run**

- GitHub Actions run `#26337008605`: completed / success
- event: `push`
- branch: `main`
- commit: `8018f45`
- job: `ai-advisor-tests` — completed / success
- steps: `Install dependencies`, `Run AI Advisor tests` — success
- duration: 37s (github.com)

**Contract Impact**

- CI：符合 v1.2 Release Hardening 要求。
- 測試範圍：包含 schema / guardrails / batch / evaluator / streamlit smoke。
- Scope discipline：沒有接入 Real LLM 真實呼叫，沒有 scope creep。
- 後續：建議在 Go/No-Go 前把 Node.js 20 actions warning 記成低風險追蹤項。

---

*檔案自動建立於本機工作區 `docs/release_hardening_review_2026-05-23.md`，內容來源由使用者提供的審查摘要。*