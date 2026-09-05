"""Service tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from agile_ticket_simulator.config import AppConfig
from agile_ticket_simulator.forecasting import ForecastResult
from agile_ticket_simulator.generator import SimulationResult
from agile_ticket_simulator.service import SimulationService


def simulation() -> SimulationResult:
    events = pd.DataFrame({"TicketName": ["A", "B"]})
    return SimulationResult(events, pd.DataFrame({"PI": ["1.1"]}))


def test_orchestrates_enabled_forecast(app_config: AppConfig) -> None:
    daily = pd.DataFrame({"day": [1, 2]})
    forecast = ForecastResult(pd.DataFrame({"prediction": [1]}), pd.DataFrame())
    seen: list[object] = []

    def writer(*args: object) -> tuple[Path, ...]:
        seen.extend(args)
        return (Path("artifact.csv"),)

    service = SimulationService(
        generator=lambda _: simulation(),
        analyzer=lambda _: daily,
        forecaster=lambda *_: forecast,
        writer=writer,
    )
    summary = service.run(app_config)
    assert summary.ticket_count == 2
    assert summary.event_count == 2
    assert summary.daily_row_count == 2
    assert summary.forecast_row_count == 1
    assert summary.artifact_paths == (Path("artifact.csv"),)
    assert any(value is forecast for value in seen)


def test_skips_disabled_forecast(app_config: AppConfig) -> None:
    config = replace(app_config, forecast=replace(app_config.forecast, enabled=False))
    captured: list[object] = []

    def fail(*_: object) -> ForecastResult:
        raise AssertionError("forecaster should not run")

    def writer(*args: object) -> tuple[Path, ...]:
        captured.extend(args)
        return ()

    summary = SimulationService(
        generator=lambda _: simulation(),
        analyzer=lambda _: pd.DataFrame({"day": [1]}),
        forecaster=fail,
        writer=writer,
    ).run(config)
    assert summary.forecast_row_count == 0
    assert any(value is None for value in captured)
