from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ai_advisor.market_scanner import rank_scanner_candidates, scan_market_candidates
from ai_advisor.market_scanner.schemas import (
    BenchmarkDailyRecord,
    DailyStockRecord,
    ScannerConfig,
    ScannerPassCandidate,
    ScannerTechnicalPosition,
)
from ai_advisor.schemas import StockAdviceContext


def test_hard_skip_for_low_risk_reward_is_deterministic() -> None:
    result = scan_market_candidates(
        [stock_series("3001", target_above_close=1.0)],
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=0),
    )

    assert result.candidates == []
    assert len(result.skipped_candidates) == 1
    assert result.skipped_candidates[0].reason == "risk_reward_ratio <= 1.0"
    assert result.summary.skip_reason_counts == {"risk_reward_ratio <= 1.0": 1}


def test_penalty_rows_may_still_be_output_and_low_positive_rr_path_is_reachable() -> None:
    result = scan_market_candidates(
        [stock_series("3002", target_above_close=4.0, latest_volume=1_000_000)],
        {"TAIEX": benchmark_series(start_close=200, step=-1)},
        ScannerConfig(min_output_warning_threshold=0),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert 1.0 < candidate.risk_reward_ratio < 1.5
    assert "risk_reward_ratio below small_probe threshold" in candidate.penalties
    assert "volume_ratio_20d below 1.2" in candidate.penalties
    assert "market risk_off; guardrails will forbid A-grade" in candidate.penalties
    assert result.summary.penalty_candidate_count == 1


def test_score_ordering_is_stable_by_fixed_priority() -> None:
    result = scan_market_candidates(
        [
            stock_series("3003", target_above_close=8.0),
            stock_series("3002", target_above_close=12.0),
            stock_series("3001", target_above_close=12.0),
        ],
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=0),
    )

    assert [candidate.stock_id for candidate in result.candidates] == ["3001", "3002", "3003"]
    assert [candidate.scanner_rank for candidate in result.candidates] == [1, 2, 3]
    assert result.candidates[0].scanner_score == 100.0
    assert result.candidates[0].context_data["scanner_metadata"]["scanner_rank"] == 1


def test_technical_position_preference_is_part_of_ordering_contract() -> None:
    candidates = [
        candidate_for_ordering("4003", "extended_above_ma"),
        candidate_for_ordering("4002", "breakout"),
        candidate_for_ordering("4001", "pullback_to_ma10_and_rebound"),
    ]

    ranked = rank_scanner_candidates(candidates)

    assert [candidate.stock_id for candidate in ranked] == ["4001", "4002", "4003"]


def test_sorting_tie_breakers_follow_fixed_priority() -> None:
    assert [
        candidate.stock_id
        for candidate in rank_scanner_candidates(
            [
                candidate_for_ordering("4102", rs20=2),
                candidate_for_ordering("4101", rs20=3),
            ]
        )
    ] == ["4101", "4102"]
    assert [
        candidate.stock_id
        for candidate in rank_scanner_candidates(
            [
                candidate_for_ordering("4202", rs60=2),
                candidate_for_ordering("4201", rs60=3),
            ]
        )
    ] == ["4201", "4202"]
    assert [
        candidate.stock_id
        for candidate in rank_scanner_candidates(
            [
                candidate_for_ordering("4302", volume_ratio=1.3),
                candidate_for_ordering("4301", volume_ratio=1.8),
            ]
        )
    ] == ["4301", "4302"]
    assert [
        candidate.stock_id
        for candidate in rank_scanner_candidates(
            [
                candidate_for_ordering("4402", distance=4),
                candidate_for_ordering("4401", distance=1),
            ]
        )
    ] == ["4401", "4402"]
    assert [
        candidate.stock_id
        for candidate in rank_scanner_candidates(
            [
                candidate_for_ordering("4502"),
                candidate_for_ordering("4501"),
            ]
        )
    ] == ["4501", "4502"]


def test_context_result_warnings_are_preserved_in_m4_output() -> None:
    result = scan_market_candidates(
        [stock_series("3050", target_above_close=10.0, length=60)],
        {"TAIEX": benchmark_series(length=60)},
        ScannerConfig(min_output_warning_threshold=0),
    )

    candidate = result.candidates[0]
    assert candidate.relative_strength_60d_vs_benchmark is None
    assert "insufficient stock data for relative_strength_60d_vs_benchmark: need 61, got 60" in candidate.context_data["data_quality_warnings"]


def test_twenty_plus_fixture_candidates_produce_20_contexts_without_warning() -> None:
    stock_universe = [stock_series(str(3100 + index), target_above_close=10 + index * 0.1) for index in range(20)]

    result = scan_market_candidates(
        stock_universe,
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=20, max_output=50),
    )

    assert result.summary.output_context_count == 20
    assert result.summary.warnings == []
    assert len(result.candidates) == 20
    for candidate in result.candidates:
        StockAdviceContext.model_validate(candidate.context_data)


def test_max_output_is_respected() -> None:
    result = scan_market_candidates(
        [
            stock_series("3010", target_above_close=10.0),
            stock_series("3011", target_above_close=11.0),
            stock_series("3012", target_above_close=12.0),
        ],
        {"TAIEX": benchmark_series()},
        ScannerConfig(max_output=2, min_output_warning_threshold=0),
    )

    assert result.summary.output_context_count == 2
    assert len(result.candidates) == 2
    assert "max_output applied: kept 2 of 3 pass candidates" in result.summary.warnings


def test_fewer_than_20_outputs_warns_without_fabricating_contexts() -> None:
    result = scan_market_candidates(
        [stock_series("3020", target_above_close=10.0)],
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=20),
    )

    assert result.summary.output_context_count == 1
    assert len(result.candidates) == 1
    assert result.summary.warnings == ["fewer than 20 contexts generated: 1"]


def test_market_scan_fallback_keeps_theme_neutral_and_scanner_strength_in_metadata() -> None:
    result = scan_market_candidates(
        [stock_series("3030", target_above_close=10.0)],
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=0),
    )

    context_data = result.candidates[0].context_data
    assert context_data["theme"] == {"name": "market_scan", "rank": 999, "score": 50.0, "lifecycle": "unknown"}
    assert "scanner_score" not in context_data["theme"]
    assert "relative_strength_20d_vs_benchmark" not in context_data["theme"]
    assert context_data["scanner_metadata"]["scanner_score"] == 100.0
    assert context_data["scanner_metadata"]["relative_strength_20d_vs_benchmark"] is not None


def test_scanner_writes_contexts_without_mutating_advice_or_evaluation_logs(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "ai_advice"
    reports_dir.mkdir(parents=True)
    advice_log = reports_dir / "ai_advice_log.jsonl"
    evaluation_log = reports_dir / "ai_advice_evaluation.jsonl"
    advice_log.write_text("advice sentinel\n", encoding="utf-8")
    evaluation_log.write_text("evaluation sentinel\n", encoding="utf-8")

    result = scan_market_candidates(
        [stock_series("3040", target_above_close=10.0)],
        {"TAIEX": benchmark_series()},
        ScannerConfig(min_output_warning_threshold=0),
        output_dir=tmp_path / "contexts",
    )

    assert result.candidates[0].context_path is not None
    assert Path(result.candidates[0].context_path).exists()
    assert advice_log.read_text(encoding="utf-8") == "advice sentinel\n"
    assert evaluation_log.read_text(encoding="utf-8") == "evaluation sentinel\n"


def stock_series(
    stock_id: str,
    *,
    target_above_close: float,
    latest_volume: int = 2_000_000,
    market_type: str = "listed",
    length: int = 61,
) -> list[DailyStockRecord]:
    start = date(2024, 1, 1)
    latest_close = 100 + (length - 1) * 0.2
    records: list[DailyStockRecord] = []
    for i in range(length):
        close = 100 + i * 0.2
        high = close + 0.5
        if i == length - 2:
            high = latest_close + target_above_close
        volume = latest_volume if i == 60 else 1_000_000
        records.append(
            DailyStockRecord(
                source="filter-score-fixture",
                market_type=market_type,
                date=(start + timedelta(days=i)).isoformat(),
                stock_id=stock_id,
                name=f"Stock {stock_id}",
                open=close - 0.2,
                high=high,
                low=close - 0.5,
                close=close,
                volume=volume,
                turnover_value=50_000_000,
                is_limit_up=False,
            )
        )
    return records


def benchmark_series(
    *,
    symbol: str = "TAIEX",
    start_close: float = 100,
    step: float = 0.2,
    length: int = 61,
) -> list[BenchmarkDailyRecord]:
    start = date(2024, 1, 1)
    records: list[BenchmarkDailyRecord] = []
    for i in range(length):
        records.append(
            BenchmarkDailyRecord(
                source="filter-score-fixture",
                benchmark_symbol=symbol,
                date=(start + timedelta(days=i)).isoformat(),
                close=start_close + i * step,
            )
        )
    return records


def candidate_for_ordering(
    stock_id: str,
    technical_position: ScannerTechnicalPosition = "pullback_to_ma10_and_rebound",
    *,
    rs20: float = 1.0,
    rs60: float = 1.0,
    volume_ratio: float = 1.5,
    distance: float = 2.0,
) -> ScannerPassCandidate:
    return ScannerPassCandidate(
        stock_id=stock_id,
        stock_name=f"Stock {stock_id}",
        market_type="listed",
        date="2024-03-01",
        risk_reward_ratio=2.0,
        relative_strength_20d_vs_benchmark=rs20,
        relative_strength_60d_vs_benchmark=rs60,
        volume_ratio_20d=volume_ratio,
        technical_position=technical_position,
        distance_from_ma20=distance,
        context_data={"theme": {"name": "market_scan", "rank": 999, "score": 50}, "scanner_metadata": {}},
    )
