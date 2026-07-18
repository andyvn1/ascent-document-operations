"""Unit tests for project_automation.schema.

Uses small synthetic plans built in-memory rather than the real (locally
gitignored) config/tasks.yaml, so these tests are reproducible for anyone
cloning the repo, per AI.md NFR5 (mock/isolate external and environment
dependencies in unit tests).
"""

from __future__ import annotations

from typing import TypedDict

import pytest
from pydantic import ValidationError

from project_automation.schema import (
    CircularDependencyError,
    Epic,
    Milestone,
    MissingDependencyError,
    Priority,
    Project,
    Status,
    Task,
    TaskPlan,
)


def _make_task(**overrides: object) -> Task:
    defaults: dict[str, object] = {
        "id": "TASK-001",
        "title": "Example task",
        "description": "An example task.",
        "project": "Business Validation",
        "epic": "Product Definition",
        "milestone": "M1: Business and MVP Definition",
        "day": 1,
        "week": 1,
        "priority": Priority.HIGH,
        "status": Status.NOT_STARTED,
        "estimate_hours": 4,
    }
    defaults.update(overrides)
    return Task(**defaults)  # type: ignore[arg-type]


class _BasePlanKwargs(TypedDict):
    projects: list[Project]
    milestones: list[Milestone]
    epics: list[Epic]


def _base_plan_kwargs() -> _BasePlanKwargs:
    return {
        "projects": [Project(id="PROJ-001", name="Business Validation")],
        "milestones": [
            Milestone(id="M1", title="M1: Business and MVP Definition", week=1)
        ],
        "epics": [
            Epic(id="EPIC-001", name="Product Definition", project="Business Validation")
        ],
    }


def test_valid_plan_passes() -> None:
    plan = TaskPlan(tasks=[_make_task()], **_base_plan_kwargs())
    assert plan.tasks[0].id == "TASK-001"


def test_duplicate_task_id_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate task id"):
        TaskPlan(
            tasks=[_make_task(id="TASK-001"), _make_task(id="TASK-001")],
            **_base_plan_kwargs(),
        )


def test_missing_dependency_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskPlan(
            tasks=[_make_task(id="TASK-001", dependencies=["TASK-999"])],
            **_base_plan_kwargs(),
        )
    assert isinstance(exc_info.value.errors()[0]["ctx"]["error"], MissingDependencyError)


def test_circular_dependency_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskPlan(
            tasks=[
                _make_task(id="TASK-001", dependencies=["TASK-002"]),
                _make_task(id="TASK-002", dependencies=["TASK-001"]),
            ],
            **_base_plan_kwargs(),
        )
    assert isinstance(exc_info.value.errors()[0]["ctx"]["error"], CircularDependencyError)


def test_self_dependency_is_circular() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskPlan(
            tasks=[_make_task(id="TASK-001", dependencies=["TASK-001"])],
            **_base_plan_kwargs(),
        )
    assert isinstance(exc_info.value.errors()[0]["ctx"]["error"], CircularDependencyError)


def test_unknown_project_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown project"):
        TaskPlan(
            tasks=[_make_task(project="Nonexistent Project")],
            **_base_plan_kwargs(),
        )


def test_unknown_milestone_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown milestone"):
        TaskPlan(
            tasks=[_make_task(milestone="M9: Does Not Exist")],
            **_base_plan_kwargs(),
        )


def test_epic_is_scoped_by_project() -> None:
    """The same epic name under a different project should not satisfy
    a task's reference — this is the "Data Layer" wrinkle found in the
    real tasks.yaml (same epic name, two different projects).
    """
    plan_kwargs = _base_plan_kwargs()
    plan_kwargs["projects"] = [
        Project(id="PROJ-001", name="Business Validation"),
        Project(id="PROJ-002", name="Backend Foundation"),
    ]
    plan_kwargs["epics"] = [
        Epic(id="EPIC-001", name="Data Layer", project="Backend Foundation"),
    ]
    with pytest.raises(ValidationError, match="unknown epic"):
        TaskPlan(
            tasks=[_make_task(project="Business Validation", epic="Data Layer")],
            **plan_kwargs,
        )


def test_duplicate_epic_id_across_projects_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate epic id"):
        TaskPlan(
            tasks=[],
            projects=[
                Project(id="PROJ-001", name="Backend Foundation"),
                Project(id="PROJ-002", name="File and Document Intake"),
            ],
            milestones=_base_plan_kwargs()["milestones"],
            epics=[
                Epic(id="EPIC-001", name="Data Layer", project="Backend Foundation"),
                Epic(id="EPIC-001", name="Data Layer", project="File and Document Intake"),
            ],
        )


def test_same_epic_name_different_projects_is_allowed() -> None:
    plan = TaskPlan(
        tasks=[
            _make_task(id="TASK-001", project="Backend Foundation", epic="Data Layer"),
            _make_task(id="TASK-002", project="File and Document Intake", epic="Data Layer"),
        ],
        projects=[
            Project(id="PROJ-001", name="Backend Foundation"),
            Project(id="PROJ-002", name="File and Document Intake"),
        ],
        milestones=_base_plan_kwargs()["milestones"],
        epics=[
            Epic(id="EPIC-001", name="Data Layer", project="Backend Foundation"),
            Epic(id="EPIC-002", name="Data Layer", project="File and Document Intake"),
        ],
    )
    assert len(plan.epics) == 2