from __future__ import annotations

from dataclasses import dataclass, field

from ai_advisor.schemas import EvidenceItem, StockAdviceContext, StockAdviceOutput


class LLMClientError(RuntimeError):
    pass


@dataclass
class FakeStockAdviceClient:
    """Stable fake/demo client. It never calls external APIs."""

    fail_stock_ids: set[str] = field(default_factory=set)

    def generate_stock_advice(self, context: StockAdviceContext) -> StockAdviceOutput:
        stock_id = context.stock.stock_id or ""
        if stock_id in self.fail_stock_ids:
            raise LLMClientError(f"fake LLM failure for stock_id={stock_id}")

        rr = context.risk.risk_reward_ratio or 0.0
        lifecycle = context.theme.lifecycle or "unknown"
        risk_state = context.market_regime.risk_state or "neutral"
        position = context.technical.position or "unknown"
        invalid_level = context.risk.invalid_level

        if rr >= 2.0 and lifecycle in {"early", "main_uptrend"} and risk_state != "risk_off":
            grade = "A"
            recommendation = "small_probe"
            confidence = 82
        elif rr >= 1.5 and lifecycle not in {"fading", "broken"}:
            grade = "B"
            recommendation = "small_probe"
            confidence = 74
        elif lifecycle in {"fading", "broken"}:
            grade = "C"
            recommendation = "avoid_chasing"
            confidence = 58
        else:
            grade = "C"
            recommendation = "wait_pullback"
            confidence = 62

        evidence = [
            EvidenceItem(field="risk.risk_reward_ratio", value=rr),
            EvidenceItem(field="theme.lifecycle", value=lifecycle),
            EvidenceItem(field="technical.position", value=position),
            EvidenceItem(field="market_regime.risk_state", value=risk_state),
        ]
        if invalid_level is not None:
            evidence.append(EvidenceItem(field="risk.invalid_level", value=invalid_level))

        risk_flags: list[str] = []
        if context.technical.is_overheated:
            risk_flags.append("technical.is_overheated")
        if context.technical.is_limit_up:
            risk_flags.append("technical.is_limit_up")
        if context.stock.change_pct is not None and context.stock.change_pct >= 7:
            risk_flags.append("stock.change_pct >= 7")

        stock_name = context.stock.name or stock_id or "unknown stock"
        return StockAdviceOutput(
            recommendation=recommendation,
            grade=grade,
            confidence=confidence,
            summary=f"{stock_name} batch demo advice based only on structured context.",
            bull_case=[
                f"Theme lifecycle is {lifecycle}.",
                f"Risk reward ratio is {rr}.",
            ],
            bear_case=[
                f"Technical position is {position}.",
                "Plan is invalid if required risk controls are missing.",
            ],
            entry_conditions=[
                "Enter only after next-session strength confirms the planned setup.",
            ],
            stop_loss_plan=[
                f"Stop at invalid_level {invalid_level}." if invalid_level is not None else "No stop because invalid_level is missing.",
            ],
            take_profit_plan=[
                "Scale out near planned target if the context provides one; otherwise review manually.",
            ],
            invalidation_conditions=[
                "Invalidate if price loses the provided invalid_level or theme lifecycle deteriorates.",
            ],
            next_session_confirmation=[
                "Confirm volume and price action remain consistent with the structured context.",
            ],
            risk_flags=risk_flags,
            evidence=evidence,
            data_quality_warnings=list(context.data_quality_warnings),
        )
