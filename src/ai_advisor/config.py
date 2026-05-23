from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardrailConfig:
    min_rr_for_small_probe: float = 1.5
    min_rr_for_grade_a: float = 2.0
    max_confidence_when_data_missing: int = 60
    max_confidence_when_guardrail_downgraded: int = 70


@dataclass(frozen=True)
class AdvisorConfig:
    provider: str = "openai"
    model: str = "fake-demo"
    prompt_version: str = "v1.2"
    strategy_profile: str = "balanced"
    log_path: str = "reports/ai_advice/ai_advice_log.jsonl"
    evaluation_log_path: str = "reports/ai_advice/ai_advice_evaluation.jsonl"
    max_stocks_per_run: int = 50
    max_llm_calls_per_run: int = 50
    guardrails: GuardrailConfig = GuardrailConfig()


DEFAULT_CONFIG = AdvisorConfig()


def ensure_output_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
