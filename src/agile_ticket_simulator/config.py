"""Immutable, validated TOML configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any, TypeVar, cast

from agile_ticket_simulator.errors import ConfigurationError

T = TypeVar("T")


def _section(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Missing or invalid [{name}] section")
    return cast(dict[str, Any], value)


def _value(section: dict[str, Any], name: str, expected: type[T]) -> T:
    value = section.get(name)
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise ConfigurationError(f"'{name}' must be a {expected.__name__}")
    return value


def _positive(value: int, name: str, *, allow_zero: bool = False) -> int:
    if value < (0 if allow_zero else 1):
        kind = "non-negative" if allow_zero else "positive"
        raise ConfigurationError(f"'{name}' must be {kind}")
    return value


def _parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ConfigurationError(f"'{name}' must be an ISO date (YYYY-MM-DD)") from error


def _integer_tuple(section: dict[str, Any], name: str) -> tuple[int, ...]:
    values = section.get(name)
    if not isinstance(values, list) or not values:
        raise ConfigurationError(f"'{name}' must be a non-empty integer array")
    invalid = any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in values
    )
    if invalid:
        raise ConfigurationError(f"'{name}' values must be positive integers")
    return tuple(values)


def _filename(value: str, name: str, suffix: str) -> str:
    path = Path(value)
    if path.name != value or path.suffix != suffix:
        raise ConfigurationError(f"'{name}' must be a plain {suffix} filename")
    return value


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Simulation behavior for one project."""

    name: str
    progress_rate: float
    capacity: int
    teams: tuple[str, ...]
    default_delays: tuple[int, ...]
    review_delays: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ConfigurationError("Project names cannot be empty")
        if not isfinite(self.progress_rate) or not 0.0 <= self.progress_rate <= 1.0:
            raise ConfigurationError("Project progress rates must be between 0 and 1")
        _positive(self.capacity, "capacity", allow_zero=True)
        if not self.teams or any(not team.strip() for team in self.teams):
            raise ConfigurationError("Each project must define non-empty team names")
        if len(set(self.teams)) != len(self.teams):
            raise ConfigurationError("Team names within a project must be unique")
        if not self.default_delays or not self.review_delays:
            raise ConfigurationError("Each project must define status delays")
        if any(delay < 1 for delay in (*self.default_delays, *self.review_delays)):
            raise ConfigurationError("Status delays must be positive")


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Root simulation controls."""

    ticket_count: int
    seed: int
    start_date: date
    end_date: date
    pi_length_days: int
    feature_count: int

    def __post_init__(self) -> None:
        _positive(self.ticket_count, "ticket_count")
        _positive(self.seed, "seed", allow_zero=True)
        _positive(self.pi_length_days, "pi_length_days")
        _positive(self.feature_count, "feature_count")
        if self.end_date < self.start_date:
            raise ConfigurationError("'end_date' cannot be before 'start_date'")


@dataclass(frozen=True, slots=True)
class ForecastConfig:
    """Chronological rolling-forecast settings."""

    enabled: bool
    lags: int
    validation_fraction: float
    ridge_penalty: float

    def __post_init__(self) -> None:
        _positive(self.lags, "lags")
        if (
            not isfinite(self.validation_fraction)
            or not 0.0 < self.validation_fraction < 1.0
        ):
            raise ConfigurationError("'validation_fraction' must be between 0 and 1")
        if not isfinite(self.ridge_penalty) or self.ridge_penalty < 0:
            raise ConfigurationError("'ridge_penalty' must be non-negative")


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Output directory and artifact names."""

    directory: Path
    events_file: str
    increments_file: str
    daily_metrics_file: str
    forecasts_file: str
    manifest_file: str

    def __post_init__(self) -> None:
        for name, value, suffix in (
            ("events_file", self.events_file, ".csv"),
            ("increments_file", self.increments_file, ".csv"),
            ("daily_metrics_file", self.daily_metrics_file, ".csv"),
            ("forecasts_file", self.forecasts_file, ".csv"),
            ("manifest_file", self.manifest_file, ".json"),
        ):
            _filename(value, name, suffix)


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated application configuration."""

    simulation: SimulationConfig
    forecast: ForecastConfig
    output: OutputConfig
    projects: tuple[ProjectConfig, ...]
    team_members: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        names = [project.name for project in self.projects]
        if not names or len(names) != len(set(names)):
            raise ConfigurationError("Project names must be present and unique")
        member_map = dict(self.team_members)
        if len(member_map) != len(self.team_members):
            raise ConfigurationError("Team names must be unique")
        configured_teams = {team for project in self.projects for team in project.teams}
        missing = sorted(configured_teams.difference(member_map))
        if missing:
            raise ConfigurationError(f"Missing team member counts: {', '.join(missing)}")
        if any(count < 1 for count in member_map.values()):
            raise ConfigurationError("Team member counts must be positive")

    @classmethod
    def from_toml(cls, path: Path) -> AppConfig:
        """Load TOML and resolve output paths relative to the configuration."""
        try:
            with path.open("rb") as stream:
                document = tomllib.load(stream)
        except OSError as error:
            message = f"Cannot read configuration '{path}': {error}"
            raise ConfigurationError(message) from error
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(f"Invalid TOML in '{path}': {error}") from error
        simulation = _section(document, "simulation")
        forecast = _section(document, "forecast")
        output = _section(document, "output")
        projects = _section(document, "projects")
        team_members = _section(document, "team_members")
        parsed_projects = tuple(
            _project(name, cast(dict[str, Any], values))
            for name, values in projects.items()
            if isinstance(values, dict)
        )
        if len(parsed_projects) != len(projects):
            raise ConfigurationError("Every [projects] entry must be a table")
        parsed_members: list[tuple[str, int]] = []
        for name, count in team_members.items():
            if not isinstance(count, int) or isinstance(count, bool):
                raise ConfigurationError("Team member counts must be integers")
            parsed_members.append((name, count))
        base = path.resolve().parent
        return cls(
            simulation=SimulationConfig(
                ticket_count=_value(simulation, "ticket_count", int),
                seed=_value(simulation, "seed", int),
                start_date=_parse_date(
                    _value(simulation, "start_date", str), "start_date"
                ),
                end_date=_parse_date(_value(simulation, "end_date", str), "end_date"),
                pi_length_days=_value(simulation, "pi_length_days", int),
                feature_count=_value(simulation, "feature_count", int),
            ),
            forecast=ForecastConfig(
                enabled=_value(forecast, "enabled", bool),
                lags=_value(forecast, "lags", int),
                validation_fraction=float(_value(forecast, "validation_fraction", float)),
                ridge_penalty=float(_value(forecast, "ridge_penalty", float)),
            ),
            output=OutputConfig(
                directory=base / _value(output, "directory", str),
                events_file=_value(output, "events_file", str),
                increments_file=_value(output, "increments_file", str),
                daily_metrics_file=_value(output, "daily_metrics_file", str),
                forecasts_file=_value(output, "forecasts_file", str),
                manifest_file=_value(output, "manifest_file", str),
            ),
            projects=parsed_projects,
            team_members=tuple(parsed_members),
        )


def _project(name: str, section: dict[str, Any]) -> ProjectConfig:
    teams = section.get("teams")
    if not isinstance(teams, list) or any(not isinstance(team, str) for team in teams):
        raise ConfigurationError(f"Project '{name}' teams must be a string array")
    return ProjectConfig(
        name=name,
        progress_rate=float(_value(section, "progress_rate", float)),
        capacity=_value(section, "capacity", int),
        teams=tuple(teams),
        default_delays=_integer_tuple(section, "default_delays"),
        review_delays=_integer_tuple(section, "review_delays"),
    )
