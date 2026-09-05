"""Validated conversion of event records into complete daily project metrics."""

from __future__ import annotations

import pandas as pd

from agile_ticket_simulator.errors import DataValidationError
from agile_ticket_simulator.generator import ACTIVE_STATUSES

REQUIRED_COLUMNS = {
    "TicketName",
    "TicketStatus",
    "TicketProject",
    "TicketStatusDate",
    "TicketCreatedDate",
}
METRICS = ("CreatedTicketsCount", "DoneTicketsCount", "FlowTicketsCount")


def build_daily_metrics(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate status events by project/date and insert missing days as zero."""
    missing = sorted(REQUIRED_COLUMNS.difference(events.columns))
    if missing:
        raise DataValidationError(f"Event data is missing columns: {', '.join(missing)}")
    if events.empty:
        raise DataValidationError("Event data contains no records")
    frame = events.copy()
    for column in ("TicketCreatedDate", "TicketStatusDate"):
        try:
            frame[column] = pd.to_datetime(frame[column], errors="raise").dt.normalize()
        except (ValueError, TypeError) as error:
            message = f"Column '{column}' contains an invalid date"
            raise DataValidationError(message) from error
    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        raise DataValidationError("Required event fields cannot be empty")

    daily_frames: list[pd.DataFrame] = []
    for project, project_events in frame.groupby("TicketProject", sort=True):
        start = min(
            project_events["TicketCreatedDate"].min(),
            project_events["TicketStatusDate"].min(),
        )
        end = max(
            project_events["TicketCreatedDate"].max(),
            project_events["TicketStatusDate"].max(),
        )
        index = pd.date_range(start, end, freq="D", name="Date")
        created = _unique_tickets(project_events, "TicketCreatedDate")
        done = _unique_tickets(
            project_events[project_events["TicketStatus"] == "Done"], "TicketStatusDate"
        )
        flow = _unique_tickets(
            project_events[project_events["TicketStatus"].isin(ACTIVE_STATUSES)],
            "TicketStatusDate",
        )
        daily = pd.DataFrame(
            {
                "CreatedTicketsCount": created.reindex(index, fill_value=0),
                "DoneTicketsCount": done.reindex(index, fill_value=0),
                "FlowTicketsCount": flow.reindex(index, fill_value=0),
            },
            index=index,
        ).reset_index()
        daily.insert(1, "Project", str(project))
        daily_frames.append(daily)
    return pd.concat(daily_frames, ignore_index=True)


def _unique_tickets(events: pd.DataFrame, date_column: str) -> pd.Series:
    if events.empty:
        return pd.Series(dtype="int64")
    return events.groupby(date_column)["TicketName"].nunique().astype("int64")
