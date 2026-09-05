"""Generator tests."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from agile_ticket_simulator.config import AppConfig, ProjectConfig
from agile_ticket_simulator.generator import EVENT_COLUMNS, STATUSES, TicketGenerator


def test_generation_is_deterministic_and_complete(app_config: AppConfig) -> None:
    first = TicketGenerator().generate(app_config)
    second = TicketGenerator().generate(app_config)
    pd.testing.assert_frame_equal(first.events, second.events)
    assert first.events["TicketName"].nunique() == 20
    assert tuple(first.events.columns) == EVENT_COLUMNS
    types = first.events.drop_duplicates("TicketName")["TicketType"].value_counts()
    assert types.to_dict() == {"Story": 12, "Bug": 8}
    increments = first.increments["ProgramIncrement"].tolist()
    assert increments == sorted(
        increments, key=lambda value: tuple(map(int, value.split(".")))
    )


def test_zero_progress_still_emits_initial_status(app_config: AppConfig) -> None:
    project = ProjectConfig("Project_A", 0.0, 10, ("Team_A",), (1,), (1,))
    config = replace(
        app_config,
        projects=(project,),
        team_members=(("Team_A", 5),),
    )
    result = TicketGenerator().generate(config)
    assert len(result.events) == config.simulation.ticket_count
    assert set(result.events["TicketStatus"]) == {STATUSES[0]}


def test_story_points_respect_capacity(app_config: AppConfig) -> None:
    result = TicketGenerator().generate(app_config)
    capacities = {project.name: project.capacity for project in app_config.projects}
    unique = result.events.drop_duplicates(["PI", "TicketProject", "TicketName"])
    totals = unique.groupby(["PI", "TicketProject"])["TicketStoryPoint"].sum()
    for (_, project), total in totals.items():
        assert total <= capacities[project]
    assert (result.events["TicketStoryPoint"] >= 0).all()


def test_enriched_values_are_valid(app_config: AppConfig) -> None:
    events = TicketGenerator().generate(app_config).events
    assert set(events["TicketType"]) <= {"Bug", "Story"}
    assert set(events["TicketScope"]) <= {"Planned", "Committed", "Delivered"}
    assert events["TeamMembers"].min() > 0
    assert events["TicketFeatureName"].str.startswith("ADA_Feature_").all()
