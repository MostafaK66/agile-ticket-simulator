"""CLI tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pytest import CaptureFixture, MonkeyPatch

from agile_ticket_simulator import cli
from agile_ticket_simulator.errors import ConfigurationError


def test_cli_success(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    summary = SimpleNamespace(
        ticket_count=10,
        event_count=42,
        forecast_row_count=6,
        artifact_paths=(Path("events.csv"),),
    )
    monkeypatch.setattr(cli.AppConfig, "from_toml", lambda _: object())
    service = SimpleNamespace(run=lambda _: summary)
    monkeypatch.setattr(cli, "SimulationService", lambda: service)
    assert cli.main(["--config", "example.toml"]) == 0
    output = capsys.readouterr().out
    assert "10 tickets, 42 events" in output
    assert "artifact: events.csv" in output


def test_cli_error(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    def fail(_: Path) -> object:
        raise ConfigurationError("bad config")

    monkeypatch.setattr(cli.AppConfig, "from_toml", fail)
    assert cli.main([]) == 2
    assert "error: bad config" in capsys.readouterr().err


def test_parser_default() -> None:
    assert cli.build_parser().parse_args([]).config == Path("config.toml")
