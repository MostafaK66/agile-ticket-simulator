"""Artifact writer tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from agile_ticket_simulator.artifacts import write_artifacts
from agile_ticket_simulator.config import AppConfig
from agile_ticket_simulator.errors import ArtifactError
from agile_ticket_simulator.forecasting import ForecastResult
from agile_ticket_simulator.generator import SimulationResult


def data() -> tuple[SimulationResult, pd.DataFrame, ForecastResult]:
    table = pd.DataFrame({"value": [1]})
    return SimulationResult(table, table), table, ForecastResult(table, table)


def test_writes_forecast_artifacts_and_manifest(app_config: AppConfig) -> None:
    simulation, daily, forecast = data()
    paths = write_artifacts(simulation, daily, forecast, app_config)
    assert len(paths) == 5
    assert all(path.is_file() for path in paths)
    manifest = json.loads(paths[-1].read_text())
    assert manifest["forecast_enabled"] is True
    assert manifest["ticket_count"] == 20


def test_writes_without_forecast(app_config: AppConfig) -> None:
    simulation, daily, _ = data()
    paths = write_artifacts(simulation, daily, None, app_config)
    assert len(paths) == 4
    manifest = json.loads(paths[-1].read_text())
    assert manifest["forecast_metrics"] == []


def test_wraps_filesystem_error(app_config: AppConfig, tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("file")
    config = replace(app_config, output=replace(app_config.output, directory=blocked))
    simulation, daily, forecast = data()
    with pytest.raises(ArtifactError, match="Cannot write"):
        write_artifacts(simulation, daily, forecast, config)
