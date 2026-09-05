"""Forecasting tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agile_ticket_simulator.config import ForecastConfig
from agile_ticket_simulator.errors import ForecastError
from agile_ticket_simulator.forecasting import forecast_daily_metrics, make_supervised


def daily_frame(days: int = 20) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    values = np.arange(days) % 5
    return pd.DataFrame(
        {
            "Date": dates,
            "Project": "P",
            "CreatedTicketsCount": values,
            "DoneTicketsCount": values + 1,
            "FlowTicketsCount": values + 2,
        }
    )


def test_makes_copied_lag_windows() -> None:
    values = np.arange(6.0)
    dates = pd.date_range("2024-01-01", periods=6).to_numpy()
    features, targets, target_dates = make_supervised(values, dates, 3)
    assert features.tolist() == [[0.0, 1.0, 2.0], [1.0, 2.0, 3.0], [2.0, 3.0, 4.0]]
    assert targets.tolist() == [3.0, 4.0, 5.0]
    values[0] = 99.0
    assert features[0, 0] == 0.0
    assert target_dates[0] == dates[3]


@pytest.mark.parametrize(
    ("values", "dates", "lags"),
    [
        ([[1.0]], ["2024-01-01"], 1),
        ([1.0], ["2024-01-01", "2024-01-02"], 1),
        ([1.0], ["2024-01-01"], 0),
        ([float("nan"), 1.0], ["2024-01-01", "2024-01-02"], 1),
        ([1.0], ["2024-01-01"], 1),
    ],
)
def test_rejects_invalid_supervised_inputs(
    values: object, dates: object, lags: int
) -> None:
    with pytest.raises(ForecastError):
        make_supervised(values, dates, lags)


def test_forecasts_all_metrics_deterministically() -> None:
    config = ForecastConfig(True, 3, 0.25, 1.0)
    first = forecast_daily_metrics(daily_frame(), config)
    second = forecast_daily_metrics(daily_frame(), config)
    pd.testing.assert_frame_equal(first.predictions, second.predictions)
    assert len(first.metrics) == 3
    assert set(first.predictions["Metric"]) == {
        "CreatedTicketsCount",
        "DoneTicketsCount",
        "FlowTicketsCount",
    }
    assert (first.predictions["Predicted"] >= 0).all()


def test_rejects_bad_daily_frames() -> None:
    config = ForecastConfig(True, 3, 0.25, 1.0)
    with pytest.raises(ForecastError, match="missing columns"):
        forecast_daily_metrics(pd.DataFrame(), config)
    with pytest.raises(ForecastError, match="enough observations"):
        forecast_daily_metrics(daily_frame(5), config)


def test_rejects_empty_project_observations() -> None:
    empty = daily_frame().iloc[:0]
    with pytest.raises(ForecastError, match="no project"):
        forecast_daily_metrics(empty, ForecastConfig(True, 2, 0.2, 0.0))
