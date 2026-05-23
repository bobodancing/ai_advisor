# AI 建議模組 Spec v1.0 — 台股板塊輪動主觀交易工作台

模組名稱：`ai_advisor`  
定位：主觀交易員的 AI 交易參謀  
核心原則：AI 不直接取代交易員下單，只根據系統資料產生「可操作、可檢查、可追蹤」的交易建議。

---

## 1. 功能目標

AI 建議模組要回答五個問題：

1. 今天台股資金流向是否明確？
2. 哪些板塊值得明天優先觀察？
3. 哪些股票是相對好的交易候選？
4. 哪些股票不該追？
5. 如果要交易，應該怎麼設停損、觀察條件與失效條件？

AI 的輸出不是「報明牌」，而是交易計畫：

```text
可觀察 / 可小部位試單 / 只等回測 / 不追價 / 放棄
```

---

## 2. 系統定位

AI 應扮演以下角色：

### 2.1 盤後參謀

根據收盤資料、板塊強度、龍頭排序，產生明日策略。

### 2.2 反方風控官

針對你想買的股票，主動指出錯誤可能性。

### 2.3 交易計畫整理員

把模糊想法轉成：

- 進場條件
- 停損條件
- 加碼條件
- 放棄條件
- 題材退潮條件

### 2.4 復盤教練

追蹤 AI 建議後續結果，分析哪些建議有效、哪些建議常錯。

---

## 3. 明確限制

AI 不允許：

- 在資料缺失時假裝知道
- 編造新聞
- 編造法人買賣超
- 編造即時報價
- 直接輸出「現在市價買進」
- 沒有停損條件就給正向建議
- 忽略大盤環境
- 忽略題材生命週期
- 把補漲末端股評為 A 級
- 把交易建議包裝成保證獲利

---

## 4. 模組架構

新增目錄：

```text
src/
  ai_advisor/
    __init__.py
    llm_client.py
    context_builder.py
    prompt_templates.py
    schemas.py
    advice_engine.py
    guardrails.py
    evaluator.py
    report_renderer.py
```

設定檔：

```text
config/
  ai_advisor.yaml
  prompts/
    daily_market_advice.md
    stock_trade_advice.md
    risk_review.md
    weekly_review.md
```

輸出：

```text
reports/
  ai_advice/
    daily_ai_advice_YYYY-MM-DD.md
    stock_advice_股票代號_YYYY-MM-DD.md
    ai_advice_log.jsonl
```

---

## 5. API Key 設計

### 5.1 不要寫死 API Key

API Key 不可寫進程式碼、README、config YAML、GitHub repo。

使用 `.env` 或系統環境變數：

```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.5
```

`.gitignore` 必須加入：

```text
.env
.env.*
secrets.json
```

### 5.2 Provider 抽象層

`llm_client.py` 要支援多 provider：

```python
class LLMClient:
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        raise NotImplementedError
```

實作：

```text
OpenAIClient
AnthropicClient
GeminiClient
LocalLLMClient
```

第一版先做 `OpenAIClient` 即可，但介面要保留擴充彈性。

---

## 6. Context Builder

LLM 不直接查資料庫，而是吃系統整理好的 context。

### 6.1 Daily Market Context

輸入：

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
      "lifecycle": "主升期",
      "avg_change_pct": 4.2,
      "turnover_change_pct": 138,
      "leader": "3017 奇鋐"
    }
  ],
  "weak_sectors": [],
  "leaders": [],
  "watchlist_candidates": [],
  "no_chase_list": []
}
```

### 6.2 Stock Advice Context

輸入：

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
  "theme": {
    "name": "散熱",
    "rank": 1,
    "score": 86,
    "lifecycle": "主升期"
  },
  "leader_status": {
    "leader_rank": "龍一",
    "leader_score": 91
  },
  "technical": {
    "ma5": 121,
    "ma10": 118,
    "ma20": 110,
    "position": "回測10日線後轉強",
    "is_overheated": false
  },
  "risk": {
    "invalid_level": 116,
    "nearest_support": 118,
    "risk_reward_ratio": 2.1
  }
}
```

---

## 7. AI 建議類型

### 7.1 Daily AI Advice

指令：

```bash
python examples/generate_ai_daily_advice.py --date 2026-05-23
```

輸出：

```markdown
# AI 盤後建議 YYYY-MM-DD

## 今日總結
## 明日主策略
## 優先觀察板塊
## 優先觀察個股
## 不宜追價名單
## 風險提醒
## 明日盤中確認訊號
```

### 7.2 Stock Trade Advice

指令：

```bash
python examples/generate_stock_advice.py --stock-id 3017 --date 2026-05-23
```

輸出：

```markdown
# AI 個股交易建議：3017 奇鋐

## 結論
- 建議：只等回測 / 可小部位試單 / 不追價 / 放棄
- 等級：A / B / C / Reject
- 信心：0~100

## 理由
## 進場條件
## 停損條件
## 加碼條件
## 放棄條件
## 反方風險
```

### 7.3 Risk Review

輸入你想做的交易：

```json
{
  "stock_id": "3017",
  "planned_entry": 123.5,
  "planned_stop": 116,
  "planned_target": 140,
  "reason": "散熱板塊主升，奇鋐回測10日線後轉強"
}
```

AI 輸出：

```text
這筆交易是否合理？
是不是追高？
停損是否太寬？
風報比是否足夠？
是否有更好的等待條件？
```

---

## 8. 結構化輸出 Schema

AI 回覆必須符合固定 JSON schema。

範例：

```json
{
  "type": "object",
  "properties": {
    "recommendation": {
      "type": "string",
      "enum": ["observe", "wait_pullback", "small_probe", "avoid_chasing", "reject"]
    },
    "grade": {
      "type": "string",
      "enum": ["A", "B", "C", "Reject"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    },
    "summary": {
      "type": "string"
    },
    "bull_case": {
      "type": "array",
      "items": {"type": "string"}
    },
    "bear_case": {
      "type": "array",
      "items": {"type": "string"}
    },
    "entry_conditions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "stop_loss_plan": {
      "type": "array",
      "items": {"type": "string"}
    },
    "take_profit_plan": {
      "type": "array",
      "items": {"type": "string"}
    },
    "invalidation_conditions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "data_quality_warnings": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": [
    "recommendation",
    "grade",
    "confidence",
    "summary",
    "bull_case",
    "bear_case",
    "entry_conditions",
    "stop_loss_plan",
    "take_profit_plan",
    "invalidation_conditions",
    "data_quality_warnings"
  ],
  "additionalProperties": false
}
```

---

## 9. Prompt 模板

### 9.1 System Prompt

```text
你是一位資深台股交易員，專長是板塊輪動、資金流向、題材生命週期與技術線輔助交易。

你的任務不是預測股價，也不是報明牌，而是根據輸入資料產生可執行、可檢查、風險明確的交易建議。

規則：
1. 只能使用輸入資料，不可編造資料。
2. 如果資料不足，必須明確寫在 data_quality_warnings。
3. 不可給出沒有停損條件的正向交易建議。
4. 技術線只能作為進出場輔助，不可凌駕板塊與資金流。
5. 對追高、補漲末端、題材退潮要嚴格。
6. 必須同時提出 bull case 與 bear case。
7. 建議必須落在固定 enum：
   observe / wait_pullback / small_probe / avoid_chasing / reject
```

### 9.2 User Prompt

```text
以下是今日盤後資料，請根據資料產生 AI 建議。

<market_context>
{{ market_context_json }}
</market_context>

請輸出符合 JSON schema 的結果。
```

---

## 10. Guardrails

### 10.1 Data Guard

在送給 LLM 前檢查：

```text
- 是否有日期
- 是否有大盤狀態
- 是否有板塊分數
- 是否有股票收盤價
- 是否有技術位置
- 是否有停損候選點
```

缺資料時：

```text
禁止輸出 A 級
禁止輸出 small_probe
只能 observe / avoid_chasing / reject
```

### 10.2 Risk Guard

若符合以下條件，AI 不可給 A 級：

```text
- risk_reward_ratio < 1.5
- stock is overheated
- theme lifecycle is 退潮期 / 崩解期
- leader_status 不是龍一或龍二
- invalid_level 缺失
- volume abnormal but price cannot advance
```

### 10.3 Hallucination Guard

AI 回覆中若出現輸入資料不存在的：

```text
- 新聞
- 法人買賣超
- 目標價
- 未提供的財報
- 未提供的產業消息
```

系統要標記：

```text
hallucination_suspected = true
```

並拒絕顯示該建議。

---

## 11. AI 建議評估系統

每次 AI 建議都存到：

```text
reports/ai_advice/ai_advice_log.jsonl
```

欄位：

```json
{
  "timestamp": "...",
  "date": "...",
  "stock_id": "...",
  "input_context_hash": "...",
  "recommendation": "...",
  "grade": "...",
  "confidence": 82,
  "model": "gpt-5.5",
  "prompt_version": "v1",
  "followup_1d_return": null,
  "followup_3d_return": null,
  "followup_5d_return": null,
  "was_useful": null,
  "human_feedback": null
}
```

未來可以統計：

```text
- AI A 級建議 5 日後平均報酬
- AI Reject 是否成功避開下跌
- 哪些板塊 AI 判斷準
- 哪些型態 AI 常誤判
```

---

## 12. 第一版 MVP

第一版只做三個功能：

### MVP 1：Daily AI Advice

根據每日板塊輪動報告，產生明日策略。

### MVP 2：Stock Trade Advice

輸入股票代號，輸出交易建議卡。

### MVP 3：Risk Review

輸入你想做的交易，AI 幫你挑錯。

---

## 13. Codex 開發任務

### Session F：AI Advisor 基礎架構

```text
請建立 src/ai_advisor 模組。

需求：
1. 支援 .env 讀取 OPENAI_API_KEY
2. 建立 LLMClient 抽象介面
3. 建立 OpenAIClient
4. 支援 structured JSON output
5. 建立 schemas.py
6. 建立 guardrails.py
7. 不要把 API key 寫進 repo
8. 所有 AI 回覆都要存 log
```

### Session G：Daily AI Advice

```text
請建立 Daily AI Advice 功能。

輸入：
- reports/daily/daily_market_report_YYYY-MM-DD.md
- 或 structured market_context.json

輸出：
- reports/ai_advice/daily_ai_advice_YYYY-MM-DD.md
- reports/ai_advice/ai_advice_log.jsonl

限制：
- AI 只能根據 context 回答
- 缺資料要明確標示
- 不可編造新聞或即時報價
```

### Session H：Stock Trade Advice

```text
請建立 Stock Trade Advice 功能。

輸入：
- stock_id
- date
- stock context
- theme context
- leader context
- technical context
- risk context

輸出：
- A/B/C/Reject
- recommendation enum
- bull case
- bear case
- entry conditions
- stop loss plan
- invalidation conditions
```

---

## 14. 最終原則

AI 可以給「實際建議」，但建議必須長這樣：

```text
不是：買 3017。
而是：

3017 屬於散熱龍一，板塊強度排名第 1，題材處於主升期。
但目前短線漲幅偏高，不適合直接追。
建議：wait_pullback
條件：
1. 回測 10 日線不破
2. 回檔量縮
3. 隔日出現紅 K 轉強
停損：
跌破前低或 20 日線
失效：
散熱板塊跌出前 5，或龍二同步轉弱
```

這樣的 AI 建議才值得信任、可執行、可復盤。
