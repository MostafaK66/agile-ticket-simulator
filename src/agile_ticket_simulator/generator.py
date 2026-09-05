"""Deterministic Agile ticket-event simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from agile_ticket_simulator.config import AppConfig, ProjectConfig
from agile_ticket_simulator.errors import SimulationError

STATUSES = ("Refined", "To Do", "In Progress", "In Review", "Done")
ACTIVE_STATUSES = frozenset(STATUSES[:-1])
PRIORITIES = ("Blocker", "Major", "Minor", "Not Blocking")
STORY_POINTS = (1, 2, 3, 5)
EVENT_COLUMNS = (
    "PI",
    "TicketName",
    "TicketStatus",
    "TicketProject",
    "TicketTeam",
    "TicketStatusDate",
    "TicketCreatedDate",
    "TicketFeatureName",
    "TicketType",
    "TicketPriority",
    "TicketScope",
    "TeamMembers",
    "TicketStoryPoint",
)


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Generated event records and ordered program increments."""

    events: pd.DataFrame
    increments: pd.DataFrame


class TicketGenerator:
    """Generate repeatable ticket lifecycles from validated configuration."""

    def generate(self, config: AppConfig) -> SimulationResult:
        """Generate all configured tickets and enrich their status events."""
        # Predictability is the product requirement; this is not security-sensitive.
        rng = random.Random(config.simulation.seed)  # noqa: S311
        member_counts = dict(config.team_members)
        bug_count = int(config.simulation.ticket_count * 0.4)
        ticket_types = ["Bug"] * bug_count + ["Story"] * (
            config.simulation.ticket_count - bug_count
        )
        rng.shuffle(ticket_types)
        events: list[dict[str, object]] = []
        for ticket_number in range(1, config.simulation.ticket_count + 1):
            project = rng.choice(config.projects)
            team = rng.choice(project.teams)
            first_status_date = _random_date(
                config.simulation.start_date, config.simulation.end_date, rng
            )
            created_date = first_status_date - timedelta(
                days=rng.choice((1, 3, 5, 7, 9, 11))
            )
            ticket_name = f"ADA_Ticket_{ticket_number}"
            common: dict[str, object] = {
                "TicketName": ticket_name,
                "TicketProject": project.name,
                "TicketTeam": team,
                "TicketCreatedDate": created_date,
                "TicketFeatureName": (
                    f"ADA_Feature_{rng.randint(1, config.simulation.feature_count)}"
                ),
                "TicketType": ticket_types[ticket_number - 1],
                "TicketPriority": rng.choice(PRIORITIES),
                "TeamMembers": member_counts[team],
            }
            status_date = first_status_date
            for index, status in enumerate(STATUSES):
                if index > 0 and rng.random() >= project.progress_rate:
                    break
                events.append(
                    {
                        **common,
                        "TicketStatus": status,
                        "TicketStatusDate": status_date,
                        "TicketScope": _scope(status),
                    }
                )
                status_date += timedelta(days=_status_delay(project, status, rng))
        if not events:
            raise SimulationError("Simulation produced no ticket events")
        frame = pd.DataFrame(events)
        frame["PI"] = frame["TicketStatusDate"].map(
            lambda value: _program_increment(
                value, config.simulation.start_date, config.simulation.pi_length_days
            )
        )
        frame["TicketStoryPoint"] = _assign_story_points(frame, config.projects, rng)
        frame = frame.loc[:, list(EVENT_COLUMNS)].sort_values(
            ["TicketStatusDate", "TicketName", "TicketStatus"], ignore_index=True
        )
        increment_names = sorted(frame["PI"].unique(), key=_pi_sort_key)
        increments = pd.DataFrame({"ProgramIncrement": increment_names})
        return SimulationResult(events=frame, increments=increments)


def _random_date(start: date, end: date, rng: random.Random) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _status_delay(project: ProjectConfig, status: str, rng: random.Random) -> int:
    choices = project.review_delays if status == "In Review" else project.default_delays
    return rng.choice(choices)


def _scope(status: str) -> str:
    if status == "Done":
        return "Delivered"
    if status in {"In Progress", "In Review"}:
        return "Committed"
    return "Planned"


def _program_increment(value: date, start: date, length: int) -> str:
    number = (value - start).days // length + 1
    major, minor_zero_based = divmod(number - 1, 10)
    return f"{major + 1}.{minor_zero_based + 1}"


def _pi_sort_key(value: str) -> tuple[int, int]:
    major, minor = value.split(".", maxsplit=1)
    return int(major), int(minor)


def _assign_story_points(
    events: pd.DataFrame,
    projects: tuple[ProjectConfig, ...],
    rng: random.Random,
) -> pd.Series:
    capacities = {project.name: project.capacity for project in projects}
    assignments: dict[tuple[str, str, str], int] = {}
    for (increment, project), group in events.groupby(["PI", "TicketProject"], sort=True):
        remaining = capacities[str(project)]
        tickets = sorted(group["TicketName"].unique())
        for ticket in tickets:
            possible = [point for point in STORY_POINTS if point <= remaining]
            point = rng.choice(possible) if possible else 0
            assignments[(str(increment), str(project), str(ticket))] = point
            remaining -= point
    values = (
        assignments[(str(row.PI), str(row.TicketProject), str(row.TicketName))]
        for row in events.itertuples()
    )
    return pd.Series(values, index=events.index, dtype="int64")
