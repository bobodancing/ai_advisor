from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


MarketType = Literal["listed", "otc", "unknown"]
BenchmarkSymbol = Literal["TAIEX", "OTC", "unknown"]
RiskState = Literal["risk_on", "neutral", "risk_off"]
ThemeLifecycle = Literal["early", "main_uptrend", "late_stage", "fading", "broken", "unknown"]
LeaderRank = Literal["leader_1", "leader_2", "follower", "laggard", "unknown"]
TechnicalPosition = Literal[
    "breakout",
    "pullback_to_ma5",
    "pullback_to_ma10_and_rebound",
    "near_ma20_support",
    "extended_above_ma",
    "breakdown",
    "range_bound",
    "unknown",
]
Recommendation = Literal["observe", "wait_pullback", "small_probe", "avoid_chasing", "reject"]
Grade = Literal["A", "B", "C", "Reject"]


class AdvisorBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class StockInfo(AdvisorBaseModel):
    stock_id: str | None = None
    name: str | None = None
    close: float | None = None
    change_pct: float | None = None
    volume_ratio_20d: float | None = None

    @field_validator("stock_id", mode="before")
    @classmethod
    def coerce_stock_id(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


class MarketRegime(AdvisorBaseModel):
    risk_state: RiskState | None = None


class ThemeInfo(AdvisorBaseModel):
    name: str | None = None
    rank: int | None = None
    score: float | None = None
    lifecycle: ThemeLifecycle | None = None


class LeaderStatus(AdvisorBaseModel):
    leader_rank: LeaderRank | None = None


class TechnicalInfo(AdvisorBaseModel):
    position: TechnicalPosition | None = None
    is_overheated: bool | None = None
    is_limit_up: bool | None = False


class RiskInfo(AdvisorBaseModel):
    invalid_level: float | None = None
    risk_reward_ratio: float | None = None
    nearest_support: float | None = None
    planned_target: float | None = None


class EvidenceItem(AdvisorBaseModel):
    field: str
    value: str | int | float | bool | None


class StockAdviceContext(AdvisorBaseModel):
    date: str | None = None
    market_type: MarketType | None = None
    benchmark_symbol: BenchmarkSymbol | None = None
    stock: StockInfo = Field(default_factory=StockInfo)
    market_regime: MarketRegime = Field(default_factory=MarketRegime)
    theme: ThemeInfo = Field(default_factory=ThemeInfo)
    leader_status: LeaderStatus = Field(default_factory=LeaderStatus)
    technical: TechnicalInfo = Field(default_factory=TechnicalInfo)
    risk: RiskInfo = Field(default_factory=RiskInfo)
    data_source_notes: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_benchmark(self) -> "StockAdviceContext":
        warnings = list(self.data_quality_warnings)

        def add_warning(message: str) -> None:
            if message not in warnings:
                warnings.append(message)

        if self.market_type == "listed":
            self.benchmark_symbol = "TAIEX"
        elif self.market_type == "otc":
            self.benchmark_symbol = "OTC"
        else:
            self.market_type = "unknown"
            if self.benchmark_symbol in {"TAIEX", "OTC"}:
                add_warning("market_type missing or unknown; explicit benchmark_symbol preserved")
            else:
                self.benchmark_symbol = "TAIEX"
                add_warning("market_type missing or unknown; default benchmark_symbol set to TAIEX")

        self.data_quality_warnings = warnings
        return self

    def missing_required_fields(self) -> list[str]:
        required_paths = [
            "date",
            "stock.stock_id",
            "stock.name",
            "stock.close",
            "stock.change_pct",
            "stock.volume_ratio_20d",
            "market_regime.risk_state",
            "theme.name",
            "theme.rank",
            "theme.score",
            "theme.lifecycle",
            "leader_status.leader_rank",
            "technical.position",
            "technical.is_overheated",
            "risk.invalid_level",
            "risk.risk_reward_ratio",
        ]
        missing: list[str] = []
        for path in required_paths:
            value = get_context_path(self, path)
            if value is None or value == "":
                missing.append(path)
        return missing


class StockAdviceOutput(AdvisorBaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: Recommendation
    grade: Grade
    confidence: int = Field(ge=0, le=100)
    summary: str
    bull_case: list[str]
    bear_case: list[str]
    entry_conditions: list[str]
    stop_loss_plan: list[str]
    take_profit_plan: list[str]
    invalidation_conditions: list[str]
    next_session_confirmation: list[str]
    risk_flags: list[str]
    evidence: list[EvidenceItem]
    data_quality_warnings: list[str]


class ContextSummary(AdvisorBaseModel):
    advice_date: str | None
    stock_id: str | None
    stock_name: str | None
    advice_close: float | None
    market_type: MarketType
    benchmark_symbol: BenchmarkSymbol
    input_context_hash: str | None = None


class GuardrailResult(AdvisorBaseModel):
    was_downgraded: bool
    was_blocked: bool
    final_grade: Grade
    final_recommendation: Recommendation
    reasons: list[str]
    hallucination_suspected: bool
    error_message: str | None = None


class GuardedAdviceOutput(AdvisorBaseModel):
    raw_advice: StockAdviceOutput | None
    final_advice: StockAdviceOutput
    context_summary: ContextSummary
    guardrail_result: GuardrailResult


class RankedStockAdvice(AdvisorBaseModel):
    rank: int
    stock_id: str
    stock_name: str
    grade: Grade
    recommendation: Recommendation
    confidence: int
    risk_flags_count: int
    data_quality_warnings_count: int
    was_blocked: bool
    guardrail_reasons: list[str]
    guarded_advice: GuardedAdviceOutput


class AdviceLogEntry(AdvisorBaseModel):
    timestamp: str
    advice_type: str = "stock_batch"
    advice_date: str | None
    stock_id: str | None
    stock_name: str | None
    advice_close: float | None
    market_type: MarketType
    benchmark_symbol: BenchmarkSymbol
    input_context_hash: str | None
    model: str
    prompt_version: str
    strategy_profile: str
    raw_recommendation: Recommendation | None
    raw_grade: Grade | None
    final_recommendation: Recommendation
    final_grade: Grade
    confidence: int
    was_downgraded: bool
    was_blocked: bool
    hallucination_suspected: bool
    guardrail_reasons: list[str]
    stock_return_5d_pct: float | None = None
    benchmark_return_5d_pct: float | None = None
    alpha_5d_pct: float | None = None
    alpha_hit_5d: bool | None = None
    was_useful: bool | None = None
    human_feedback: str | None = None


def get_context_path(context: StockAdviceContext, path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, BaseModel):
            if hasattr(current, part):
                current = getattr(current, part)
            elif current.model_extra and part in current.model_extra:
                current = current.model_extra[part]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def validate_stock_advice_output(data: Any) -> StockAdviceOutput:
    try:
        if isinstance(data, StockAdviceOutput):
            return data
        return StockAdviceOutput.model_validate(data)
    except ValidationError:
        raise
