"""Thin command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agile_ticket_simulator.config import AppConfig
from agile_ticket_simulator.errors import AgileSimulatorError
from agile_ticket_simulator.service import SimulationService


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic Agile ticket events and forecasts"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="TOML configuration path (default: config.toml)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the simulator and translate expected errors into concise messages."""
    arguments = build_parser().parse_args(argv)
    try:
        summary = SimulationService().run(AppConfig.from_toml(arguments.config))
    except AgileSimulatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        f"completed: {summary.ticket_count} tickets, {summary.event_count} events, "
        f"{summary.forecast_row_count} forecasts"
    )
    for path in summary.artifact_paths:
        print(f"artifact: {path}")
    return 0
