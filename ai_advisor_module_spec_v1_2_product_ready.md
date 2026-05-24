# AI Advisor v1.2 Product Spec - Streamlit 批次個股 Alpha Finder

模組名稱：`ai_advisor`

產品定位：個人台股交易台中的「批次個股 Alpha Finder」。第一版協助使用者在盤後快速篩選候選股、產生可檢查的交易計畫，並用 5 個交易日後相對市場指數報酬追蹤 alpha 命中率。

版本目的：將 v1.1 的全功能 AI Advisor MVP 收斂成可先落地的產品閉環。v1.2 只做 `Stock Trade Advice Batch`；`Daily AI Advice` 與 `Risk Review` 移到 Phase 2。

---

## 1. 產品結論

v1.2 的核心不是「AI 幫我解釋股票」，而是「批次找出值得明天優先處理的個股候選」。

第一版使用者是個人交易者，不面向公開使用者，不做投顧式推薦，不自動下單。

成功標準有兩個：

1. 找 alpha 的準確度：可行動候選股在 5 個交易日後是否跑贏市場基準。
2. 省時間：使用者不需要逐檔打開 Markdown，即可在一個網頁表格中完成批次排序、篩選與個股詳情查看。

---

## 2. MVP Scope

### 2.1 In Scope

第一版只做：

- Streamlit 批次個股篩選頁。
- 載入多檔 `StockAdviceContext` JSON。
- 使用 fake/demo mode 產生穩定個股交易建議。
- real LLM mode 在 v1.2 僅提供 API key 檢查、call estimate、max-call guard 與禁止送出保護；真實 API 執行延後到 Phase 2 / v1.3。
- 以固定排序規則列出候選股。
- 點選個股顯示完整交易計畫。
- 寫入 JSONL log。
- 匯入 follow-up CSV 後計算 5 個交易日 alpha hit rate。
- Release hardening 補齊 CI、README、release UAT checklist。
- 若使用者已有盤後 CSV，v1.2.x pilot support 可另行規劃 Scanner Lite / Context Builder，把 CSV 轉成 `StockAdviceContext` JSON。若使用者沒有 CSV 或 context，必須規劃 Phase 2 / v1.3 Market Data Scanner。

### 2.2 Out of Scope

第一版不做：

- `Daily AI Advice`
- `Risk Review`
- 行情資料下載
- 全市場自動 scanner / crawler
- Markdown 解析
- 自動下單
- 即時盤中追蹤
- 公開投顧服務
- 多使用者權限
- 多 provider 完整實作
- real LLM API 真實呼叫 / provider integration

---

## 3. Product Success Metrics

### 3.1 Alpha Hit Rate

主指標：

```text
alpha_hit_rate_5d_vs_market =
  alpha_hit_5d 為 true 的可行動候選數 /
  有完整 follow-up 資料的可行動候選數
```

可行動候選定義：

```text
grade in ["A", "B"]
recommendation in ["wait_pullback", "small_probe"]
was_blocked == false
```

`observe` 不納入主分母，避免把觀察名單誤算成交易 alpha。`observe` 可另行統計為觀察名單品質。

### 3.2 Alpha Horizon

```text
alpha_horizon_days = 5 trading days
```

第一版不自行判斷交易日曆。使用者提供的 follow-up CSV 必須已經是第 5 個交易日後的收盤價。

### 3.3 Market Benchmark

```text
market_type == listed -> benchmark_symbol = TAIEX
market_type == otc    -> benchmark_symbol = OTC
market_type missing   -> benchmark_symbol = TAIEX, 並加入 data_quality_warning
```

### 3.4 Time Saved

v1.2 省時間驗收標準：

- 可一次載入至少 20 檔 stock context。
- 結果頁可在同一表格完成排序與篩選。
- 使用者可點選 row 查看個股交易計畫。
- 使用者不需要逐檔開 Markdown 才能找出候選股。

---

## 4. Primary User Flow

### 4.1 Demo / Fake Mode

1. 使用者開啟 Streamlit app。
2. 選擇 `fake/demo mode`。
3. 上傳多檔 stock context JSON，或指定 fixture folder。
4. 點擊 `Generate Batch Advice`。
5. 系統不呼叫真實 LLM，使用 fake client 產生穩定建議。
6. 結果表顯示排序後候選股。
7. 使用者點選個股查看交易計畫。

### 4.2 Real LLM Mode

1. 使用者開啟 Streamlit app。
2. 選擇 `real LLM mode`。
3. 系統檢查 `OPENAI_API_KEY`。
4. 使用者載入 stock context JSON。
5. App 顯示本次 estimated LLM calls。
6. 若超過 `max_llm_calls_per_run`，禁止送出。
7. v1.2 release 版不送出真實 LLM API 呼叫，必須顯示 guard-only 狀態。
8. 真實 LLM 執行若要實作，必須先升級 scope 到 Phase 2 / v1.3，並保留單檔失敗不影響整批的契約。

### 4.3 Follow-up Evaluation

1. 使用者匯入 follow-up CSV。
2. 系統根據 `stock_id + advice_date` 對應 log。
3. 計算 `stock_return_5d_pct`、`alpha_5d_pct`、`alpha_hit_5d`。
4. 顯示 `alpha_hit_rate_5d_vs_market`。

---

## 5. Recommended File Structure

```text
src/
  ai_advisor/
    __init__.py
    advice_engine.py
    batch_engine.py
    config.py
    context_builder.py
    evaluator.py
    guardrails.py
    llm_client.py
    prompt_templates.py
    report_renderer.py
    schemas.py

apps/
  ai_advisor_streamlit.py

config/
  ai_advisor.yaml
  prompts/
    _system_base.md
    stock_trade_advice.md

tests/
  fixtures/
    ai_advisor/
      stock_contexts/
      followup_prices_valid.csv
  test_ai_advisor_schemas.py
  test_ai_advisor_guardrails.py
  test_ai_advisor_batch.py
  test_ai_advisor_evaluator.py
  test_ai_advisor_streamlit_smoke.py

reports/
  ai_advice/
    .gitkeep

docs/
  phase2_backlog.md
  ai_advisor_v1_3_market_scanner_roadmap.md
  market_data_source_decision.md
  market_data_scanner_risk_register.md
  release_uat_checklist.md
  scanner_lite_context_builder_plan.md
  market_data_scanner_v1_3_plan.md

.github/
  workflows/
    ci.yml

README.md
```

---

## 6. Configuration

`config/ai_advisor.yaml`:

```yaml
provider: openai
model: ${LLM_MODEL:-gpt-5.5}
reasoning_effort: ${LLM_REASONING_EFFORT:-medium}
temperature: 0.2
max_output_tokens: 3000
prompt_version: v1.2
strategy_profile: balanced

paths:
  prompt_dir: config/prompts
  output_dir: reports/ai_advice
  log_path: reports/ai_advice/ai_advice_log.jsonl

batch:
  min_supported_stocks: 20
  max_stocks_per_run: 50
  max_llm_calls_per_run: 50

evaluation:
  alpha_horizon_days: 5
  horizon_type: trading_days
  default_benchmark: TAIEX

guardrails:
  min_rr_for_small_probe: 1.5
  min_rr_for_grade_a: 2.0
  max_confidence_when_data_missing: 60
  max_confidence_when_guardrail_downgraded: 70
```

`.env`:

```env
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.5
LLM_REASONING_EFFORT=medium
```

`.gitignore` 必須包含：

```text
.env
.env.*
secrets.json
reports/ai_advice/*.jsonl
```

---

## 7. StockAdviceContext

所有 context 必須是 UTF-8 JSON。第一版不解析 Markdown。

若使用者沒有現成 context folder，但已有盤後 CSV，v1.2.x 可另行規劃 Scanner Lite / Context Builder 作為 pilot 支援工具。它只接受使用者提供的盤後 CSV，依固定規則篩選並輸出 `StockAdviceContext` JSON folder。

Scanner Lite 不是行情下載器，也不是自動技術分析器。它不得自行推論不存在的欄位，不得改變既有 guardrails、ranking、logging、benchmark mapping 或 alpha denominator。

詳細規格以 `docs/scanner_lite_context_builder_plan.md` 為準。

若使用者連盤後 CSV 都沒有，真正需要的是 Phase 2 / v1.3 Market Data Scanner。該模組需要讀取市場資料、計算技術與風險欄位、輸出 context folder，且必須獨立規劃與審查。詳細規格以 `docs/market_data_scanner_v1_3_plan.md` 為準。

### 7.1 Required Fields

```text
date
stock.stock_id
stock.name
stock.close
stock.change_pct
stock.volume_ratio_20d
market_regime.risk_state
theme.name
theme.rank
theme.score
theme.lifecycle
leader_status.leader_rank
technical.position
technical.is_overheated
risk.invalid_level
risk.risk_reward_ratio
```

### 7.2 Recommended Fields

```text
market_type
benchmark_symbol
technical.is_limit_up
risk.nearest_support
risk.planned_target
data_source_notes
```

若 `market_type` 缺失：

```text
market_type = "unknown"
benchmark_symbol = "TAIEX"
data_quality_warnings += ["market_type missing; default benchmark_symbol set to TAIEX"]
```

### 7.3 Example

```json
{
  "date": "2026-05-23",
  "market_type": "listed",
  "benchmark_symbol": "TAIEX",
  "stock": {
    "stock_id": "3017",
    "name": "奇鋐",
    "close": 123.5,
    "change_pct": 3.2,
    "volume_ratio_20d": 1.8
  },
  "market_regime": {
    "risk_state": "risk_on",
    "taiex_change_pct": 0.83,
    "otc_change_pct": 1.21
  },
  "theme": {
    "name": "散熱",
    "rank": 1,
    "score": 86,
    "lifecycle": "main_uptrend"
  },
  "leader_status": {
    "leader_rank": "leader_1",
    "leader_score": 91
  },
  "technical": {
    "ma5": 121,
    "ma10": 118,
    "ma20": 110,
    "position": "pullback_to_ma10_and_rebound",
    "is_overheated": false,
    "is_limit_up": false
  },
  "risk": {
    "invalid_level": 116,
    "nearest_support": 118,
    "planned_target": 140,
    "risk_reward_ratio": 2.1
  },
  "data_source_notes": []
}
```

### 7.4 Enums

```text
market_type: listed / otc / unknown
benchmark_symbol: TAIEX / OTC / unknown
risk_state: risk_on / neutral / risk_off
theme.lifecycle: early / main_uptrend / late_stage / fading / broken / unknown
leader_rank: leader_1 / leader_2 / follower / laggard / unknown
technical.position:
  breakout
  pullback_to_ma5
  pullback_to_ma10_and_rebound
  near_ma20_support
  extended_above_ma
  breakdown
  range_bound
  unknown
```

---

## 8. StockAdviceOutput

LLM raw output 必須符合固定 schema。Renderer 只能顯示通過 guardrails 後的 `final_advice`。

```text
recommendation: observe / wait_pullback / small_probe / avoid_chasing / reject
grade: A / B / C / Reject
confidence: 0-100
summary: string
bull_case: list[string]
bear_case: list[string]
entry_conditions: list[string]
stop_loss_plan: list[string]
take_profit_plan: list[string]
invalidation_conditions: list[string]
next_session_confirmation: list[string]
risk_flags: list[string]
evidence: list[{field: string, value: string|number|boolean}]
data_quality_warnings: list[string]
```

`GuardedAdviceOutput`:

```text
raw_advice: StockAdviceOutput
final_advice: StockAdviceOutput
context_summary:
  advice_date: string
  stock_id: string
  stock_name: string
  advice_close: number
  market_type: listed / otc / unknown
  benchmark_symbol: TAIEX / OTC / unknown
guardrail_result:
  was_downgraded: bool
  was_blocked: bool
  final_grade: A / B / C / Reject
  final_recommendation: observe / wait_pullback / small_probe / avoid_chasing / reject
  reasons: list[string]
  hallucination_suspected: bool
  error_message: string | null
```

---

## 9. Recommendation Semantics

```text
observe          可觀察，尚未形成交易計畫
wait_pullback    只等回測，不追價
small_probe      可小部位試單，但必須有停損與觸發條件
avoid_chasing    不追價，條件太差或過熱
reject           放棄，資料或風險條件不合格
```

Grade 限制：

```text
A       只能搭配 wait_pullback 或 small_probe
B       可搭配 observe / wait_pullback / small_probe
C       只能搭配 observe / wait_pullback / avoid_chasing
Reject  只能搭配 avoid_chasing / reject
```

---

## 10. Balanced Guardrails

Guardrails 必須是 deterministic code，不可只靠 prompt。

### 10.1 Data Guard

若缺必填資料：

```text
final_grade <= C
final_recommendation in [observe, avoid_chasing, reject]
confidence <= 60
data_quality_warnings 必須列出缺少欄位
```

若缺以下任一欄位，禁止 `small_probe`：

```text
risk.invalid_level
risk.risk_reward_ratio
technical.position
theme.lifecycle
market_regime.risk_state
```

### 10.2 Balanced Risk Guard

```text
A 級仍需 risk.risk_reward_ratio >= 2.0
small_probe 允許 risk.risk_reward_ratio >= 1.5
is_overheated == true 不可 small_probe
late_stage 不可 A，但可 wait_pullback
fading / broken 一律 avoid_chasing 或 reject
risk.invalid_level is null 不可正向建議
market_regime.risk_state == risk_off 不可 A
```

### 10.3 No Chase Guard

下列情況預設降為 `wait_pullback` 或 `avoid_chasing`：

```text
technical.position == extended_above_ma
technical.is_limit_up == true
stock.change_pct >= 7
```

若無法判斷是否接近支撐，只記錄 risk flag，不強制 block。

### 10.4 Evidence-based Hallucination Guard

以下詞彙本身不一定錯，但必須能在 evidence 中對應到 context 欄位：

```text
新聞
法人
外資
投信
營收
EPS
目標價
財報
訂單
```

若回覆含有上述詞彙且沒有 evidence 對應來源：

```text
hallucination_suspected = true
was_blocked = true
```

若 evidence 有對應欄位，允許顯示，但仍需在報告中呈現來源欄位。

---

## 11. Batch Engine Interfaces

新增：

```python
def generate_stock_batch_advice(
    context_paths: list[str],
) -> list[GuardedAdviceOutput]:
    ...


def rank_stock_advices(
    outputs: list[GuardedAdviceOutput],
) -> list[RankedStockAdvice]:
    ...


def update_followup_returns(
    log_path: str,
    followup_csv_path: str,
) -> AlphaSummary:
    ...
```

單檔失敗行為：

```text
單檔 context validation failed -> 產生 blocked row，不中斷整批
單檔 LLM request failed -> 產生 error row，不中斷整批
單檔 hallucination suspected -> 產生 blocked row，不中斷整批
```

---

## 12. Ranking Rules

排序規則必須固定，避免實作自行猜測。

排序優先序：

```text
1. was_blocked == false 在前
2. grade: A > B > C > Reject
3. recommendation: small_probe > wait_pullback > observe > avoid_chasing > reject
4. confidence 高到低
5. risk_flags 數量少到多
6. stock_id 升冪，作為穩定排序 fallback
```

結果表至少顯示：

```text
rank
stock_id
stock_name
grade
recommendation
confidence
risk_flags_count
data_quality_warnings_count
was_blocked
guardrail_reasons
```

---

## 13. Streamlit App Spec

執行方式：

```bash
streamlit run apps/ai_advisor_streamlit.py
```

### 13.1 Sidebar Controls

```text
mode: fake/demo / real LLM
context input: upload JSON files / folder path
max batch size
show blocked rows: true / false
follow-up CSV uploader
```

### 13.2 Main Views

```text
Batch Results
  排序表、filter、summary metrics

Stock Detail
  結論、核心理由、bull case、bear case、進場、停損、停利、失效、隔日確認、資料品質

Alpha Evaluation
  可行動候選數、follow-up 完整筆數、alpha hit rate、平均 alpha_5d_pct
```

### 13.3 Safety UI

所有頁面需顯示：

```text
交易決策輔助，不是保證獲利或下單指令。
```

real LLM mode 送出前需顯示：

```text
estimated_llm_calls = number_of_valid_contexts
```

若超過 `max_llm_calls_per_run`，禁止送出。

---

## 14. Follow-up CSV

檔名建議：

```text
followup_prices_YYYY-MM-DD.csv
```

欄位：

```csv
stock_id,advice_date,close_5d,benchmark_return_5d_pct
3017,2026-05-23,130.0,1.2
```

計算：

```text
stock_return_5d_pct = (close_5d - advice_close) / advice_close * 100
alpha_5d_pct = stock_return_5d_pct - benchmark_return_5d_pct
alpha_hit_5d = alpha_5d_pct > 0
```

若缺 `benchmark_return_5d_pct`：

```text
該筆不計入 alpha hit rate 分母
顯示 warning
```

---

## 15. AdviceLogEntry

每次 advice 都 append 到：

```text
reports/ai_advice/ai_advice_log.jsonl
```

欄位：

```json
{
  "timestamp": "2026-05-23T18:30:00+08:00",
  "advice_type": "stock_batch",
  "advice_date": "2026-05-23",
  "stock_id": "3017",
  "stock_name": "奇鋐",
  "advice_close": 123.5,
  "market_type": "listed",
  "benchmark_symbol": "TAIEX",
  "input_context_hash": "sha256...",
  "model": "gpt-5.5",
  "prompt_version": "v1.2",
  "strategy_profile": "balanced",
  "raw_recommendation": "small_probe",
  "raw_grade": "A",
  "final_recommendation": "wait_pullback",
  "final_grade": "B",
  "confidence": 70,
  "was_downgraded": true,
  "was_blocked": false,
  "hallucination_suspected": false,
  "guardrail_reasons": ["late_stage cannot be grade A under balanced profile"],
  "stock_return_5d_pct": null,
  "benchmark_return_5d_pct": null,
  "alpha_5d_pct": null,
  "alpha_hit_5d": null,
  "was_useful": null,
  "human_feedback": null
}
```

---

## 16. Prompt Requirements

`config/prompts/_system_base.md`:

```text
你是一位資深台股交易員，專長是板塊輪動、資金流向、題材生命週期與技術線輔助交易。

你的任務不是預測股價，也不是報明牌，而是根據輸入資料產生可執行、可檢查、風險明確的交易建議。

硬性規則：
1. 只能使用輸入資料，不可編造資料。
2. 如果資料不足，必須寫在 data_quality_warnings。
3. 不可給出沒有停損條件的正向交易建議。
4. 技術線只能作為進出場輔助，不可凌駕板塊與資金流。
5. 對追高、補漲末端、題材退潮要嚴格。
6. 必須同時提出 bull case 與 bear case。
7. 建議必須落在固定 enum。
8. 不可使用新聞、法人、財報、目標價，除非輸入資料明確提供。
9. evidence 必須引用輸入 context 中存在的欄位與值。
```

`config/prompts/stock_trade_advice.md`:

```text
以下是單一台股的結構化交易 context。請產生交易計畫，並輸出符合 JSON schema 的結果。

重點：
- 先判斷板塊、龍頭地位與題材生命週期。
- 再判斷技術位置是否適合交易。
- 若追高、停損不明、風報比不足，必須降級。
- 正向建議必須包含進場觸發、停損、停利或分批出場、失效條件。
- 不要使用 context 沒有提供的新聞、法人、財報、目標價。

<stock_context>
{{ context_json }}
</stock_context>
```

---

## 17. Tests

### 17.1 Schema Tests

- 合法 `StockAdviceContext` 通過。
- 缺 `market_type` 不失敗，但產生 warning 並預設 TAIEX。
- `StockAdviceOutput` enum 錯誤時 validation 失敗。

### 17.2 Guardrail Tests

- balanced profile 下，條件完整且 `risk_reward_ratio >= 1.5` 可給 `small_probe`。
- `risk_reward_ratio < 1.5` 不可 `small_probe`。
- `is_overheated = true` 不可 `small_probe`。
- `late_stage` 不可 A，但可 `wait_pullback`。
- `fading / broken` 必須降為 `avoid_chasing` 或 `reject`。
- 黑名單詞有 evidence 時不 block，無 evidence 時 block。

### 17.3 Batch Tests

- 至少 20 檔 fixture 可批次處理。
- 單檔 LLM 失敗不會中斷整批。
- 單檔 validation 失敗不會中斷整批。
- 排序結果符合固定排序規則。

### 17.4 Streamlit Smoke Tests

- 可載入 fixture folder。
- 可切換 fake/demo mode 與 real LLM mode。
- 可顯示排序表。
- 可點選單檔查看交易計畫。
- 可匯入 follow-up CSV 並顯示 5 日 alpha hit rate。

### 17.5 Evaluation Tests

- 可行動候選 5 個交易日後相對市場報酬為正時，`alpha_hit_5d = true`。
- `observe` 不進 alpha hit rate 主分母。
- 缺 `benchmark_return_5d_pct` 時不計入分母並顯示 warning。

---

## 18. Codex Implementation Sessions

### Session F - Stock Batch Core

任務：

1. 建立 stock-only schema。
2. 建立 fake/demo LLM client。
3. 建立 balanced guardrails。
4. 建立 batch engine。
5. 建立 ranking function。
6. 建立 JSONL logger。

驗收：

```bash
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py
```

### Session G - Streamlit MVP

任務：

1. 建立 `apps/ai_advisor_streamlit.py`。
2. 支援 upload JSON files 或 folder path。
3. 支援 fake/demo mode 與 real LLM mode。
4. 顯示 batch results、stock detail、alpha evaluation。
5. 顯示 estimated LLM calls 與 max batch size。
6. real LLM mode 在 v1.2 只做 guard-only，不執行真實 API 呼叫。

驗收：

```bash
streamlit run apps/ai_advisor_streamlit.py
pytest tests/test_ai_advisor_streamlit_smoke.py
```

### Session H - Follow-up Evaluation

任務：

1. 建立 follow-up CSV reader。
2. 更新 JSONL 或產生 evaluation summary。
3. 計算 alpha hit rate。
4. 顯示 missing follow-up warnings。

驗收：

```bash
pytest tests/test_ai_advisor_evaluator.py
```

### Session I - Release Hardening

任務：

1. 建立 GitHub Actions CI：安裝 `requirements.txt`，執行 full relevant pytest set。
2. 建立 `README.md`：安裝、啟動 Streamlit、fixture folder、fake/demo mode、real LLM guard-only、follow-up CSV、測試指令。
3. 建立 `docs/release_uat_checklist.md`：手動驗收 batch flow、follow-up CSV、advice log immutable、evaluation log append-only。
4. 實際跑一次 release hardening 測試並回報。
5. 不整合 real LLM 真實呼叫；若發現需求，寫入 Phase 2 backlog。

驗收：

```bash
python -m pip install -r requirements.txt
pytest tests/test_ai_advisor_schemas.py tests/test_ai_advisor_guardrails.py tests/test_ai_advisor_batch.py tests/test_ai_advisor_evaluator.py tests/test_ai_advisor_streamlit_smoke.py
```

---

## 19. Definition of Done

v1.2 完成最低標準：

- Streamlit app 是主要入口。
- 可使用 fake/demo mode 批次處理至少 20 檔 fixture。
- real LLM mode 有 API key 檢查、LLM call estimate、max call guard；v1.2 不要求真實 API 執行。
- 結果表可排序、篩選、點選個股詳情。
- 單檔失敗不會中斷整批。
- balanced guardrails 測試通過。
- evidence-based hallucination guard 測試通過。
- JSONL log 包含 advice close、market type、benchmark、alpha 欄位。
- 匯入 follow-up CSV 後能計算 5 個交易日 alpha hit rate。
- `observe` 不計入 alpha hit rate 主分母。
- GitHub Actions CI 會安裝依賴並執行 full relevant pytest set。
- README 說明安裝、啟動、fixtures、fake/demo 與 real guard-only 模式、follow-up CSV、測試方式。
- release UAT checklist 記錄實際資料流程與 JSONL append-only / immutability 驗收點。
- 專案內沒有 secrets。

---

## 20. Phase 2 Backlog

Phase 2 才做：

- Daily AI Advice
- Risk Review
- 行情下載與交易日曆
- 板塊基準 alpha
- 人工回饋 UI
- 交易計畫版本比較
- 多 provider 支援
- real LLM API 真實執行與 provider integration

---

## 21. Final Principle

v1.2 的產品重點不是讓 AI 寫很多文字，而是讓使用者更快找出可行動候選，並能在 5 個交易日後檢查它是否真的抓到 alpha。
