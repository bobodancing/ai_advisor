# AI 建議模組 Spec v1.1 - Build-ready 版

模組名稱：`ai_advisor`
定位：台股板塊輪動交易工作台中的「盤後 AI 交易參謀」。AI 只做決策輔助，不下單、不保證獲利、不替使用者承擔投資責任。

本版目的：把原本偏願景的 `ai_advisor_module_spec_v1.md` 修成 Codex 可直接建造、測試、驗收的 MVP spec。

---

## 0. 資深 PM 與交易員評估

原 spec 的方向正確：AI 不報明牌，而是產生可檢查、可執行、可復盤的交易計畫；也有資料不足不得假裝知道、不得編造新聞或法人資訊、必須有停損與風險揭露等重要限制。

但原 spec 尚不能直接施工，主要缺口如下：

- 缺少資料契約：Codex 不知道 context JSON 哪些欄位必填、型別為何、缺資料怎麼處理。
- 三種功能邊界不清：Daily Advice、Stock Advice、Risk Review 共用 schema 但輸出語意不同。
- Guardrails 只有原則，缺少可執行的降級規則、block 條件與測試驗收。
- LLM client 沒有定義 API 行為、schema validation、錯誤處理、重試策略。
- 缺少 CLI、設定檔、log schema、測試項目與 Definition of Done。

交易邏輯上可保留主軸：「板塊強度 + 龍頭地位 + 技術位置 + 題材生命週期 + 風報比」。第一版不應追求預測神準，而應追求：只在資料充分時給計畫、遇到追高或風報比不足會降級、每個正向建議都有進場觸發、停損與失效條件。

A 級不是「買進」，而是「條件成熟時值得優先處理」。沒有停損、沒有進場觸發、沒有失效條件，一律不能是 A。

---

## 1. MVP 範圍

第一版只做三件事：

1. `Daily AI Advice`：盤後根據大盤與板塊 context 產生明日策略。
2. `Stock Trade Advice`：針對單一股票產生交易計畫。
3. `Risk Review`：針對使用者手動輸入的交易計畫挑錯。

第一版不做：自動下單、即時盤中追蹤、自動查新聞、自動抓法人買賣超、自動產生目標價、公開投顧式推薦、多 provider 完整實作。

---

## 2. 建議專案結構

```text
src/
  ai_advisor/
    __init__.py
    advice_engine.py
    config.py
    context_builder.py
    evaluator.py
    guardrails.py
    llm_client.py
    prompt_templates.py
    report_renderer.py
    schemas.py
config/
  ai_advisor.yaml
  prompts/
    _system_base.md
    daily_market_advice.md
    stock_trade_advice.md
    risk_review.md
examples/
  generate_ai_daily_advice.py
  generate_stock_advice.py
  review_trade_risk.py
tests/
  fixtures/
  test_ai_advisor_schemas.py
  test_ai_advisor_guardrails.py
  test_ai_advisor_renderer.py
  test_ai_advisor_engine.py
reports/
  ai_advice/
    .gitkeep
```

若專案已有既有測試框架、套件管理方式或路徑慣例，Codex 應優先沿用既有模式。

---

## 3. 設定與 Secrets

`.env` 範例：

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

`config/ai_advisor.yaml`：

```yaml
provider: openai
model: ${LLM_MODEL:-gpt-5.5}
reasoning_effort: ${LLM_REASONING_EFFORT:-medium}
temperature: 0.2
max_output_tokens: 3000
prompt_version: v1.1
paths:
  prompt_dir: config/prompts
  output_dir: reports/ai_advice
  log_path: reports/ai_advice/ai_advice_log.jsonl
guardrails:
  min_rr_for_small_probe: 1.5
  min_rr_for_grade_a: 2.0
  max_confidence_when_data_missing: 60
  max_confidence_when_guardrail_downgraded: 70
```

模型名稱必須可配置，不可散落硬編碼在程式內。

---

## 4. LLM Client

`llm_client.py` 需定義抽象介面：

```python
from abc import ABC, abstractmethod
from typing import Any

class LLMClient(ABC):
    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        raise NotImplementedError
```

第一版只需完成 `OpenAIClient`：

- 使用 OpenAI Responses API 與 Structured Outputs。
- 從 `OPENAI_API_KEY` 讀 key。
- 使用設定檔或環境變數指定 model。
- 回傳 dict 前必須通過本地 schema validation。
- API 失敗、refusal、schema 不符都要丟出或回傳 engine 可處理的錯誤狀態。
- 測試不得呼叫真實 API，需提供 fake client。

建議例外：

```python
class LLMConfigurationError(Exception): ...
class LLMRequestError(Exception): ...
class LLMResponseValidationError(Exception): ...
```

---

## 5. 資料契約

所有 context 檔案必須是 UTF-8 JSON。第一版不要從 Markdown 反推結構化資料；Markdown 只能當人讀報告。

共用規則：

- 日期格式：`YYYY-MM-DD`
- 股票代號：4 到 6 碼字串，例如 `2330`、`3017`、`006208`
- 百分比：`3.2` 表示 3.2%，不是 `0.032`
- 金額與股數欄位名稱需明確，不可混用

### 5.1 DailyMarketContext

建議檔名：`reports/context/daily_market_context_YYYY-MM-DD.json`

必填欄位：

```text
date
market_regime.taiex_change_pct
market_regime.otc_change_pct
market_regime.market_turnover
market_regime.risk_state
top_sectors
```

範例：

```json
{
  "date": "2026-05-23",
  "market_regime": {
    "taiex_change_pct": 0.83,
    "otc_change_pct": 1.21,
    "market_turnover": 420000000000,
    "risk_state": "risk_on"
  },
  "top_sectors": [
    {
      "theme": "散熱",
      "rank": 1,
      "score": 86,
      "lifecycle": "main_uptrend",
      "avg_change_pct": 4.2,
      "turnover_change_pct": 138,
      "leader_stock_id": "3017",
      "leader_name": "奇鋐"
    }
  ],
  "weak_sectors": [],
  "leaders": [],
  "watchlist_candidates": [],
  "no_chase_list": [],
  "data_source_notes": []
}
```

Enum：

```text
risk_state: risk_on / neutral / risk_off
lifecycle: early / main_uptrend / late_stage / fading / broken / unknown
```

### 5.2 StockAdviceContext

建議檔名：`reports/context/stock_股票代號_context_YYYY-MM-DD.json`

必填欄位：

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

範例：

```json
{
  "date": "2026-05-23",
  "stock": {
    "stock_id": "3017",
    "name": "奇鋐",
    "close": 123.5,
    "change_pct": 3.2,
    "volume_ratio_20d": 1.8
  },
  "market_regime": {"risk_state": "risk_on", "taiex_change_pct": 0.83, "otc_change_pct": 1.21},
  "theme": {"name": "散熱", "rank": 1, "score": 86, "lifecycle": "main_uptrend"},
  "leader_status": {"leader_rank": "leader_1", "leader_score": 91},
  "technical": {
    "ma5": 121,
    "ma10": 118,
    "ma20": 110,
    "position": "pullback_to_ma10_and_rebound",
    "is_overheated": false,
    "is_limit_up": false
  },
  "risk": {"invalid_level": 116, "nearest_support": 118, "planned_target": 140, "risk_reward_ratio": 2.1},
  "data_source_notes": []
}
```

Enum：

```text
leader_rank: leader_1 / leader_2 / follower / laggard / unknown
technical.position:
  breakout / pullback_to_ma5 / pullback_to_ma10_and_rebound /
  near_ma20_support / extended_above_ma / breakdown / range_bound / unknown
```

### 5.3 RiskReviewInput

必填欄位：`date`、`stock_id`、`planned_entry`、`planned_stop`、`reason`

```json
{
  "date": "2026-05-23",
  "stock_id": "3017",
  "stock_name": "奇鋐",
  "planned_entry": 123.5,
  "planned_stop": 116,
  "planned_target": 140,
  "position_size_note": "小部位試單，不超過單筆風險上限",
  "reason": "散熱板塊主升，奇鋐回測10日線後轉強",
  "supporting_context_path": "reports/context/stock_3017_context_2026-05-23.json"
}
```

`planned_target` 可缺，但缺少時不能計算完整風報比，建議必須降級。

---

## 6. 輸出 Schema

所有 LLM 原始回覆必須符合 `AdviceOutput`：

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

`advice_engine.py` 必須在 guardrails 後輸出 `GuardedAdviceOutput`：

```text
raw_advice: AdviceOutput
final_advice: AdviceOutput
guardrail_result:
  was_downgraded: bool
  was_blocked: bool
  final_grade: A / B / C / Reject
  final_recommendation: observe / wait_pullback / small_probe / avoid_chasing / reject
  reasons: list[string]
  hallucination_suspected: bool
```

Renderer 只能顯示 `final_advice`。若 `was_blocked = true`，不可顯示 raw LLM 建議。

---

## 7. 建議語意與限制

Recommendation：

```text
observe          可觀察，尚未形成交易計畫
wait_pullback    只等回測，不追價
small_probe      可小部位試單，但必須有停損與觸發條件
avoid_chasing    不追價，條件太差或過熱
reject           放棄，資料或風險條件不合格
```

Grade：

```text
A       條件完整，板塊、龍頭、風報比、停損與觸發條件都明確
B       可列入候選，但至少一項條件未完全成熟
C       只能觀察，不足以形成交易
Reject  應放棄或資料不足
```

Grade 與 recommendation 對應：

```text
A       只能搭配 wait_pullback 或 small_probe
B       可搭配 observe / wait_pullback / small_probe
C       只能搭配 observe / wait_pullback / avoid_chasing
Reject  只能搭配 reject / avoid_chasing
```

---

## 8. Deterministic Guardrails

Guardrails 必須是程式碼，不可只靠 prompt。

### 8.1 Data Guard

若缺必填資料：

```text
final grade <= C
final recommendation 只能是 observe / avoid_chasing / reject
confidence 不得高於 60
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

### 8.2 Risk Guard

任一條件成立，不可給 A：

```text
risk.risk_reward_ratio < 2.0
technical.is_overheated == true
theme.lifecycle in [late_stage, fading, broken, unknown]
leader_status.leader_rank not in [leader_1, leader_2]
risk.invalid_level is null
stock.volume_ratio_20d >= 3 and stock.change_pct <= 0
market_regime.risk_state == risk_off
```

任一條件成立，不可給 `small_probe`：

```text
risk.risk_reward_ratio < 1.5
technical.is_overheated == true
theme.lifecycle in [fading, broken]
risk.invalid_level is null
stop_loss_plan is empty
```

### 8.3 No Chase Guard

任一條件成立，預設降為 `avoid_chasing` 或 `wait_pullback`：

```text
technical.position == extended_above_ma
technical.is_limit_up == true
stock.change_pct >= 7
stock.volume_ratio_20d >= 3 and close not near support
```

第一版如果無法判斷 `close not near support`，只記錄 risk flag，不強制降級。

### 8.4 Hallucination Guard

若 AI 回覆提到 context 沒提供的新聞、法人買賣超、目標價、財報、產業消息、籌碼資料，需標記 `hallucination_suspected = true` 並 block。

第一版可用黑名單詞加 evidence 檢查：

```python
HALLUCINATION_KEYWORDS = ["新聞", "法人", "外資", "投信", "營收", "EPS", "目標價", "財報", "訂單"]
```

---

## 9. Prompt 要求

`config/prompts/_system_base.md`：

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

Daily prompt 重點：判斷資金是否集中、明日優先板塊、不宜追價方向、隔日盤中確認訊號。

Stock prompt 重點：先判斷板塊、龍頭地位、題材生命週期，再判斷技術位置；追高、停損不明、風報比不足必須降級。

Risk prompt 重點：以反方風控官角度挑錯，檢查是否追高、停損是否合理、風報比是否足夠、是否需要等待更好條件。

---

## 10. 模組責任

```text
schemas.py
  定義 DailyMarketContext、StockAdviceContext、RiskReviewInput、AdviceOutput、GuardrailResult、GuardedAdviceOutput、AdviceLogEntry。

config.py
  讀 YAML、.env、環境變數，驗證必要設定。

context_builder.py
  讀 JSON context，做 validation，回傳 typed model。第一版不解析 Markdown。

prompt_templates.py
  載入 prompt，注入 deterministic JSON context。

llm_client.py
  定義 LLMClient、OpenAIClient、fake client、LLM 例外。

guardrails.py
  執行 Data/Risk/No Chase/Hallucination guards，必要時降級或 block。

advice_engine.py
  串接 context、prompt、LLM、guardrails、renderer、logging。提供 generate_daily_advice、generate_stock_advice、review_trade_risk。

report_renderer.py
  將 GuardedAdviceOutput 轉 Markdown。blocked 時不可顯示 raw advice。

evaluator.py
  append JSONL log。第一版不必計算績效，但預留 followup return 欄位。
```

---

## 11. CLI 與輸出

Daily：

```bash
python examples/generate_ai_daily_advice.py --date 2026-05-23 --context reports/context/daily_market_context_2026-05-23.json
```

Stock：

```bash
python examples/generate_stock_advice.py --stock-id 3017 --date 2026-05-23 --context reports/context/stock_3017_context_2026-05-23.json
```

Risk：

```bash
python examples/review_trade_risk.py --input trade_plan_3017_2026-05-23.json
```

Markdown 報告都必須包含：

```text
標題
交易決策輔助免責聲明
結論：建議、等級、信心、guardrail 狀態
核心理由
Bull Case
Bear Case
進場條件
停損條件
停利或分批出場計畫
失效條件
隔日確認訊號
資料品質警告
```

若 `was_blocked = true`，報告只顯示 block 原因、資料品質警告與下一步，不顯示 raw advice。

---

## 12. Log Schema

每次成功或 blocked advice 都 append 到 `reports/ai_advice/ai_advice_log.jsonl`：

```json
{
  "timestamp": "2026-05-23T18:30:00+08:00",
  "advice_type": "stock",
  "date": "2026-05-23",
  "stock_id": "3017",
  "input_context_hash": "sha256...",
  "model": "gpt-5.5",
  "prompt_version": "v1.1",
  "raw_recommendation": "small_probe",
  "raw_grade": "A",
  "final_recommendation": "wait_pullback",
  "final_grade": "B",
  "confidence": 70,
  "was_downgraded": true,
  "was_blocked": false,
  "hallucination_suspected": false,
  "guardrail_reasons": ["risk_reward_ratio < 2.0"],
  "followup_1d_return": null,
  "followup_3d_return": null,
  "followup_5d_return": null,
  "was_useful": null,
  "human_feedback": null
}
```

---

## 13. 錯誤處理

- 缺 `OPENAI_API_KEY`：CLI 顯示清楚錯誤，不產生空報告，不寫成功 log。
- Context 不合法：列出缺欄位，不呼叫 LLM，可產生 blocked report。
- LLM 回覆不合法：最多重試 1 次，仍失敗則 blocked 並 log。
- Hallucination suspected：`was_blocked = true`，Markdown 不顯示 raw advice。
- 測試環境：不得依賴真 API key 或網路。

---

## 14. 測試驗收

Schema tests：

- 合法 DailyMarketContext 通過。
- 缺 `market_regime.risk_state` 失敗。
- 合法 StockAdviceContext 通過。
- `AdviceOutput` enum 錯誤時 validation 失敗。

Guardrail tests：

- `risk_reward_ratio < 2.0` 不可 A。
- `risk_reward_ratio < 1.5` 不可 `small_probe`。
- `technical.is_overheated = true` 不可 A，也不可 `small_probe`。
- `theme.lifecycle = broken` 必須降級。
- 缺停損時不可輸出正向建議。
- 出現未提供的法人或新聞字眼時 block。

Renderer tests：

- blocked advice 不顯示 raw LLM 建議。
- 正常 advice 產生 Markdown 標題與結論區。
- data_quality_warnings 會出現在報告。

Engine tests：

- fake LLM client 可完整跑完 daily advice、stock advice、risk review。
- LLM validation error 會重試一次。
- log 會 append 可 parse 的 JSONL。

CLI smoke tests：

```bash
python examples/generate_ai_daily_advice.py --date 2026-05-23 --context tests/fixtures/daily_market_context_valid.json
python examples/generate_stock_advice.py --stock-id 3017 --date 2026-05-23 --context tests/fixtures/stock_3017_context_valid.json
python examples/review_trade_risk.py --input tests/fixtures/risk_review_input_valid.json
```

---

## 15. Codex 開發任務拆分

Session F - 基礎架構：

1. 建立 `src/ai_advisor`。
2. 建立 config、schema、validation。
3. 建立 LLMClient、OpenAIClient、fake client。
4. 建立 guardrails 與 JSONL logger。
5. 驗收：schema 與 guardrail tests 通過，無 API key 仍可跑測試。

Session G - Daily AI Advice：

1. 建 daily prompt、engine、renderer、CLI、fixtures。
2. 驗收：fake client 可產出 daily report，缺資料會有 warnings。

Session H - Stock Trade Advice：

1. 建 stock prompt、engine、renderer、CLI、fixtures。
2. 驗收：A 級必須有停損、風報比、進場條件、失效條件；過熱股不可 small_probe。

Session I - Risk Review：

1. 建 risk prompt、engine、renderer、CLI、fixtures。
2. 驗收：缺 planned target 降級；停損數值不合理 blocked；supporting context 不足需揭露。

Session J - 復盤 log 基礎：

1. 統一 log schema。
2. 建讀取 JSONL helper。
3. 預留 followup return 欄位。
4. 驗收：每行 JSONL 可 parse，可依 advice_type、grade、recommendation 統計。

---

## 16. Definition of Done

MVP 完成最低標準：

- 三個 CLI 都可用 fake client 跑通。
- Schema validation 與 guardrails 測試通過。
- 有 API key 時 OpenAIClient 可產生 structured output。
- 缺資料、過熱、風報比不足、疑似 hallucination 都會被降級或 block。
- Markdown 報告可讀，且不顯示被 block 的 raw advice。
- 每次成功或 blocked advice 都有 JSONL log。
- 專案內沒有 secrets。

---

## 17. 實務交易原則範例

可接受：

```text
3017 屬於散熱板塊，板塊強度排名第 1，題材處於主升期，且為龍一。
但目前短線漲幅偏高，不適合直接追。
建議：wait_pullback
條件：回測 10 日線不破、回檔量縮、隔日紅 K 轉強。
停損：跌破前低或 20 日線。
失效：散熱板塊跌出前 5，或龍一轉弱。
```

不可接受：

```text
買 3017，目標價 150。
```

除非 `150` 是使用者輸入的 planned target 或 context 明確提供的阻力區，否則 AI 不可自行產生目標價。

---

## 18. 外部參考

本 spec 於 2026-05-23 檢查：

- OpenAI Structured Outputs：用於要求模型輸出符合 JSON Schema。
- OpenAI Responses API：第一版 OpenAIClient 建議使用的 API 介面。
- OpenAI Models：模型名稱需維持可配置，範例使用 `gpt-5.5`，但實作不得硬編碼依賴單一模型。
- TWSE 交易制度、結算與交易規則：未來若擴充回測或下單模組，需考量交易時間、T+2 結算、漲跌幅限制等市場約束。

連結：

```text
https://platform.openai.com/docs/guides/structured-outputs
https://platform.openai.com/docs/api-reference/responses/create
https://developers.openai.com/api/docs/models/gpt-5.5/
https://www.twse.com.tw/en/page/products/trading/introduce.html
https://www.twse.com.tw/en/clearing/clearing/features.html
https://twse-regulation.twse.com.tw/ENG/EN/law/DOC01.aspx?FLCODE=fl007304&FLNO=63
```
