"""Shared deterministic fixtures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from agile_ticket_simulator.config import (
    AppConfig,
    ForecastConfig,
    OutputConfig,
    ProjectConfig,
    SimulationConfig,
)


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    projects = (
        ProjectConfig("Project_A", 1.0, 8, ("Team_A",), (1, 2), (2, 3)),
        ProjectConfig("Project_B", 0.5, 5, ("Team_B",), (1,), (2,)),
    )
    return AppConfig(
        simulation=SimulationConfig(20, 123, date(2024, 1, 1), date(2024, 2, 15), 14, 5),
        forecast=ForecastConfig(True, 3, 0.25, 1.0),
        output=OutputConfig(
            tmp_path / "outputs",
            "events.csv",
            "increments.csv",
            "daily.csv",
            "forecasts.csv",
            "run.json",
        ),
        projects=projects,
        team_members=(("Team_A", 5), ("Team_B", 3)),
    )
