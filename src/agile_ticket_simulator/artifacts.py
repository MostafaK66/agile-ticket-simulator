"""Filesystem boundary for generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from agile_ticket_simulator.config import AppConfig
from agile_ticket_simulator.errors import ArtifactError
from agile_ticket_simulator.forecasting import ForecastResult
from agile_ticket_simulator.generator import SimulationResult


def write_artifacts(
    simulation: SimulationResult,
    daily: pd.DataFrame,
    forecast: ForecastResult | None,
    config: AppConfig,
) -> tuple[Path, ...]:
    """Write generated tables and a run manifest."""
    output = config.output
    paths = [
        output.directory / output.events_file,
        output.directory / output.increments_file,
        output.directory / output.daily_metrics_file,
    ]
    if forecast is not None:
        paths.append(output.directory / output.forecasts_file)
    manifest_path = output.directory / output.manifest_file
    try:
        output.directory.mkdir(parents=True, exist_ok=True)
        simulation.events.to_csv(paths[0], index=False)
        simulation.increments.to_csv(paths[1], index=False)
        daily.to_csv(paths[2], index=False)
        if forecast is not None:
            forecast.predictions.to_csv(paths[3], index=False)
        manifest = {
            "event_count": len(simulation.events),
            "forecast_enabled": forecast is not None,
            "forecast_metrics": (
                forecast.metrics.to_dict(orient="records") if forecast is not None else []
            ),
            "increment_count": len(simulation.increments),
            "seed": config.simulation.seed,
            "ticket_count": config.simulation.ticket_count,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactError(f"Cannot write simulation artifacts: {error}") from error
    paths.append(manifest_path)
    return tuple(paths)
