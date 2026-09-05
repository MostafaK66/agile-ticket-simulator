"""Application orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from agile_ticket_simulator.analytics import build_daily_metrics
from agile_ticket_simulator.artifacts import write_artifacts
from agile_ticket_simulator.config import AppConfig, ForecastConfig
from agile_ticket_simulator.forecasting import ForecastResult, forecast_daily_metrics
from agile_ticket_simulator.generator import SimulationResult, TicketGenerator

Generator = Callable[[AppConfig], SimulationResult]
Analyzer = Callable[[pd.DataFrame], pd.DataFrame]
Forecaster = Callable[[pd.DataFrame, ForecastConfig], ForecastResult]
Writer = Callable[
    [SimulationResult, pd.DataFrame, ForecastResult | None, AppConfig], tuple[Path, ...]
]


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Counts and locations from a successful run."""

    ticket_count: int
    event_count: int
    daily_row_count: int
    forecast_row_count: int
    artifact_paths: tuple[Path, ...]


class SimulationService:
    """Coordinate generation, analytics, forecasting, and persistence."""

    def __init__(
        self,
        *,
        generator: Generator | None = None,
        analyzer: Analyzer = build_daily_metrics,
        forecaster: Forecaster = forecast_daily_metrics,
        writer: Writer = write_artifacts,
    ) -> None:
        self._generator = generator or TicketGenerator().generate
        self._analyzer = analyzer
        self._forecaster = forecaster
        self._writer = writer

    def run(self, config: AppConfig) -> RunSummary:
        """Execute one configured simulation."""
        simulation = self._generator(config)
        daily = self._analyzer(simulation.events)
        forecast = (
            self._forecaster(daily, config.forecast) if config.forecast.enabled else None
        )
        paths = self._writer(simulation, daily, forecast, config)
        return RunSummary(
            ticket_count=simulation.events["TicketName"].nunique(),
            event_count=len(simulation.events),
            daily_row_count=len(daily),
            forecast_row_count=0 if forecast is None else len(forecast.predictions),
            artifact_paths=paths,
        )
