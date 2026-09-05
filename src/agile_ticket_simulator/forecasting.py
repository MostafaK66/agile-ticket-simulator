"""Leakage-safe one-step rolling ridge forecasts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from agile_ticket_simulator.analytics import METRICS
from agile_ticket_simulator.config import ForecastConfig
from agile_ticket_simulator.errors import ForecastError

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Tidy validation predictions and metric-level errors."""

    predictions: pd.DataFrame
    metrics: pd.DataFrame


def forecast_daily_metrics(daily: pd.DataFrame, config: ForecastConfig) -> ForecastResult:
    """Walk forward through each project and metric using actual past observations."""
    required = {"Date", "Project", *METRICS}
    missing = sorted(required.difference(daily.columns))
    if missing:
        raise ForecastError(f"Daily metrics are missing columns: {', '.join(missing)}")
    all_predictions: list[pd.DataFrame] = []
    all_metrics: list[dict[str, object]] = []
    for project, project_frame in daily.groupby("Project", sort=True):
        ordered = project_frame.sort_values("Date")
        for metric in METRICS:
            values = ordered[metric].to_numpy(dtype=np.float64)
            dates = pd.to_datetime(ordered["Date"]).to_numpy()
            features, targets, target_dates = make_supervised(values, dates, config.lags)
            split = int(len(targets) * (1.0 - config.validation_fraction))
            if split < 2 or split >= len(targets):
                raise ForecastError(
                    f"Project '{project}' metric '{metric}' does not have enough "
                    "observations for the configured chronological split"
                )
            predicted = _walk_forward(
                features, targets, split=split, penalty=config.ridge_penalty
            )
            actual = targets[split:]
            mae = float(np.mean(np.abs(actual - predicted)))
            all_predictions.append(
                pd.DataFrame(
                    {
                        "Date": pd.to_datetime(target_dates[split:]),
                        "Project": str(project),
                        "Metric": metric,
                        "Actual": actual,
                        "Predicted": predicted,
                        "Residual": actual - predicted,
                    }
                )
            )
            all_metrics.append({"Project": str(project), "Metric": metric, "MAE": mae})
    if not all_predictions:
        raise ForecastError("Daily metrics contain no project observations")
    return ForecastResult(
        predictions=pd.concat(all_predictions, ignore_index=True),
        metrics=pd.DataFrame(all_metrics),
    )


def make_supervised(
    values: npt.ArrayLike, dates: npt.ArrayLike, lags: int
) -> tuple[FloatArray, FloatArray, npt.NDArray[np.datetime64]]:
    """Create copied lag windows without unsafe stride manipulation."""
    series = np.asarray(values, dtype=np.float64)
    date_values = np.asarray(dates, dtype="datetime64[ns]")
    if series.ndim != 1 or len(series) != len(date_values):
        message = "Values and dates must be equally sized one-dimensional arrays"
        raise ForecastError(message)
    if lags < 1:
        raise ForecastError("Forecast lags must be positive")
    if not np.isfinite(series).all():
        raise ForecastError("Forecast values contain a non-finite value")
    if len(series) <= lags:
        raise ForecastError(f"Need more than {lags} observations to create lag windows")
    features = np.stack(
        [series[index - lags : index] for index in range(lags, len(series))]
    )
    return features, series[lags:].copy(), date_values[lags:].copy()


def _walk_forward(
    features: FloatArray,
    targets: FloatArray,
    *,
    split: int,
    penalty: float,
) -> FloatArray:
    predictions: list[float] = []
    for index in range(split, len(targets)):
        coefficients = _fit_ridge(features[:index], targets[:index], penalty)
        augmented = np.concatenate(([1.0], features[index]))
        prediction = max(0.0, float(augmented @ coefficients))
        predictions.append(float(round(prediction)))
    return np.asarray(predictions, dtype=np.float64)


def _fit_ridge(features: FloatArray, targets: FloatArray, penalty: float) -> FloatArray:
    design = np.column_stack((np.ones(len(features)), features))
    regularizer = np.eye(design.shape[1]) * penalty
    regularizer[0, 0] = 0.0
    return np.asarray(
        np.linalg.pinv(design.T @ design + regularizer) @ design.T @ targets
    )
