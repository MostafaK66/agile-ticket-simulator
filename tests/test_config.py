"""Configuration tests."""

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
from agile_ticket_simulator.errors import ConfigurationError


def test_loads_example_configuration() -> None:
    config = AppConfig.from_toml(Path("config.example.toml"))
    assert config.simulation.ticket_count == 1000
    assert len(config.projects) == 3
    assert config.output.directory.is_absolute()


@pytest.mark.parametrize("content", ["", "[simulation\n", "[simulation]\nticket_count=1"])
def test_rejects_missing_or_malformed_toml(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(content)
    with pytest.raises(ConfigurationError):
        AppConfig.from_toml(path)


def test_missing_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Cannot read configuration"):
        AppConfig.from_toml(tmp_path / "missing.toml")


@pytest.mark.parametrize(
    "arguments",
    [
        (0, 1, date(2024, 1, 1), date(2024, 1, 2), 1, 1),
        (1, -1, date(2024, 1, 1), date(2024, 1, 2), 1, 1),
        (1, 1, date(2024, 1, 2), date(2024, 1, 1), 1, 1),
        (1, 1, date(2024, 1, 1), date(2024, 1, 2), 0, 1),
        (1, 1, date(2024, 1, 1), date(2024, 1, 2), 1, 0),
    ],
)
def test_simulation_validation(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ConfigurationError):
        SimulationConfig(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "arguments",
    [(True, 0, 0.2, 1.0), (True, 1, 1.0, 1.0), (True, 1, 0.2, -1.0)],
)
def test_forecast_validation(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ConfigurationError):
        ForecastConfig(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "arguments",
    [
        ("", 0.5, 1, ("T",), (1,), (1,)),
        ("P", 1.1, 1, ("T",), (1,), (1,)),
        ("P", 0.5, -1, ("T",), (1,), (1,)),
        ("P", 0.5, 1, (), (1,), (1,)),
        ("P", 0.5, 1, ("T",), (), (1,)),
    ],
)
def test_project_validation(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ConfigurationError):
        ProjectConfig(*arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "index,value", [(0, "folder/e.csv"), (0, "e.json"), (4, "run.csv")]
)
def test_output_validation(index: int, value: str) -> None:
    names = ["e.csv", "i.csv", "d.csv", "f.csv", "run.json"]
    names[index] = value
    with pytest.raises(ConfigurationError):
        OutputConfig(Path("out"), *names)


def test_root_requires_projects_and_complete_teams(app_config: AppConfig) -> None:
    with pytest.raises(ConfigurationError, match="Project names"):
        AppConfig(
            app_config.simulation,
            app_config.forecast,
            app_config.output,
            (),
            app_config.team_members,
        )
    with pytest.raises(ConfigurationError, match="Missing team"):
        AppConfig(
            app_config.simulation,
            app_config.forecast,
            app_config.output,
            app_config.projects,
            (("Team_A", 5),),
        )


def test_root_rejects_invalid_member_counts(app_config: AppConfig) -> None:
    with pytest.raises(ConfigurationError, match="positive"):
        AppConfig(
            app_config.simulation,
            app_config.forecast,
            app_config.output,
            app_config.projects,
            (("Team_A", 5), ("Team_B", 0)),
        )
