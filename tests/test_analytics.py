"""Daily analytics tests."""

from __future__ import annotations

import pandas as pd
import pytest

from agile_ticket_simulator.analytics import build_daily_metrics
from agile_ticket_simulator.config import AppConfig
from agile_ticket_simulator.errors import DataValidationError
from agile_ticket_simulator.generator import TicketGenerator


def test_builds_complete_daily_project_metrics(app_config: AppConfig) -> None:
    events = TicketGenerator().generate(app_config).events
    daily = build_daily_metrics(events)
    assert not daily.empty
    assert list(daily.columns) == [
        "Date",
        "Project",
        "CreatedTicketsCount",
        "DoneTicketsCount",
        "FlowTicketsCount",
    ]
    for _, group in daily.groupby("Project"):
        differences = group["Date"].diff().dropna()
        assert (differences == pd.Timedelta(days=1)).all()


def test_uses_status_date_for_done_events() -> None:
    events = pd.DataFrame(
        {
            "TicketName": ["A", "A"],
            "TicketStatus": ["Refined", "Done"],
            "TicketProject": ["P", "P"],
            "TicketCreatedDate": ["2024-01-01", "2024-01-01"],
            "TicketStatusDate": ["2024-01-02", "2024-01-04"],
        }
    )
    daily = build_daily_metrics(events).set_index("Date")
    assert daily.loc["2024-01-01", "CreatedTicketsCount"] == 1
    assert daily.loc["2024-01-04", "DoneTicketsCount"] == 1
    assert daily.loc["2024-01-03", "DoneTicketsCount"] == 0


@pytest.mark.parametrize(
    ("events", "message"),
    [
        (pd.DataFrame(), "missing columns"),
        (
            pd.DataFrame(
                columns=[
                    "TicketName",
                    "TicketStatus",
                    "TicketProject",
                    "TicketStatusDate",
                    "TicketCreatedDate",
                ]
            ),
            "no records",
        ),
    ],
)
def test_rejects_invalid_event_frames(events: pd.DataFrame, message: str) -> None:
    with pytest.raises(DataValidationError, match=message):
        build_daily_metrics(events)


def test_rejects_bad_dates_and_null_fields() -> None:
    base = pd.DataFrame(
        {
            "TicketName": ["A"],
            "TicketStatus": ["Done"],
            "TicketProject": ["P"],
            "TicketStatusDate": ["bad"],
            "TicketCreatedDate": ["2024-01-01"],
        }
    )
    with pytest.raises(DataValidationError, match="invalid date"):
        build_daily_metrics(base)
    base["TicketStatusDate"] = "2024-01-02"
    base["TicketName"] = None
    with pytest.raises(DataValidationError, match="cannot be empty"):
        build_daily_metrics(base)
