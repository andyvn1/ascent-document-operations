"""Plan-as-code schema for the GitHub Issue backlog.

Stable IDs exist because titles change (a task gets renamed, a project
gets renamed) but the identity of "the thing being tracked" must not —
that identity is what the GitHub Issue marker (`ascent-task-id: TASK-001`)
and the dependency graph below both key off of. See AI.md §4.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_STABLE_ID_PATTERN = re.compile(r"^[A-Z]+(-[A-Za-z0-9]+|[0-9]+)$")


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(StrEnum):
    NOT_STARTED = "not_started"
    IN_REVIEW = "in_review"
    DONE = "done"


def _validate_stable_id(value: str) -> str:
    if not _STABLE_ID_PATTERN.match(value):
        raise ValueError(f"id {value!r} must look like PREFIX-suffix, e.g. TASK-001 or M1")
    return value


class Project(BaseModel):
    id: str
    name: str

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        return _validate_stable_id(value)


class Milestone(BaseModel):
    id: str
    title: str
    week: int = Field(ge=1, le=6)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        return _validate_stable_id(value)


class Epic(BaseModel):
    """Epics are scoped to a project: the same epic name (e.g. "Data
    Layer") can legitimately exist under two different projects, so
    identity is (id) but uniqueness/lookup for task references is by
    (project, name), not name alone.
    """

    id: str
    name: str
    project: str

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        return _validate_stable_id(value)


class Task(BaseModel):
    id: str
    title: str
    description: str
    project: str
    epic: str
    milestone: str
    day: int = Field(ge=1)
    week: int = Field(ge=1, le=6)
    priority: Priority
    status: Status
    estimate_hours: float = Field(gt=0)
    labels: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        return _validate_stable_id(value)


class MissingDependencyError(ValueError):
    def __init__(self, task_id: str, missing_dependency_id: str) -> None:
        self.task_id = task_id
        self.missing_dependency_id = missing_dependency_id
        super().__init__(f"task {task_id} depends on unknown task {missing_dependency_id}")


class CircularDependencyError(ValueError):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"circular dependency: {' -> '.join(cycle)}")


class TaskPlan(BaseModel):
    projects: list[Project]
    milestones: list[Milestone]
    epics: list[Epic]
    tasks: list[Task]

    @model_validator(mode="after")
    def _validate(self) -> Self:
        self._check_unique_ids()
        self._check_references()
        self._check_dependencies()
        return self

    def _check_unique_ids(self) -> None:
        groups: list[tuple[str, list[Project] | list[Milestone] | list[Epic] | list[Task]]] = [
            ("project", self.projects),
            ("milestone", self.milestones),
            ("epic", self.epics),
            ("task", self.tasks),
        ]
        for label, items in groups:
            seen: set[str] = set()
            for item in items:
                if item.id in seen:
                    raise ValueError(f"duplicate {label} id: {item.id}")
                seen.add(item.id)

    def _check_references(self) -> None:
        project_names = {p.name for p in self.projects}
        milestone_titles = {m.title for m in self.milestones}
        epic_keys = {(e.project, e.name) for e in self.epics}

        for epic in self.epics:
            if epic.project not in project_names:
                raise ValueError(f"epic {epic.id} references unknown project {epic.project!r}")

        for task in self.tasks:
            if task.project not in project_names:
                raise ValueError(f"task {task.id} references unknown project {task.project!r}")
            if task.milestone not in milestone_titles:
                raise ValueError(
                    f"task {task.id} references unknown milestone {task.milestone!r}"
                )
            if (task.project, task.epic) not in epic_keys:
                raise ValueError(
                    f"task {task.id} references unknown epic {task.epic!r} "
                    f"under project {task.project!r}"
                )

    def _check_dependencies(self) -> None:
        task_ids = {t.id for t in self.tasks}
        dependencies_by_id = {t.id: t.dependencies for t in self.tasks}

        for task in self.tasks:
            for dependency_id in task.dependencies:
                if dependency_id not in task_ids:
                    raise MissingDependencyError(task.id, dependency_id)

        in_progress: set[str] = set()
        completed: set[str] = set()

        def visit(task_id: str, path: list[str]) -> None:
            if task_id in in_progress:
                raise CircularDependencyError([*path, task_id])
            if task_id in completed:
                return
            in_progress.add(task_id)
            for dependency_id in dependencies_by_id.get(task_id, []):
                visit(dependency_id, [*path, task_id])
            in_progress.remove(task_id)
            completed.add(task_id)

        for task_id in task_ids:
            if task_id not in completed:
                visit(task_id, [])


def _read_yaml(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_task_plan(
    *,
    projects_path: str | Path,
    milestones_path: str | Path,
    epics_path: str | Path,
    tasks_path: str | Path,
) -> TaskPlan:
    return TaskPlan(
        projects=_read_yaml(projects_path)["projects"],
        milestones=_read_yaml(milestones_path)["milestones"],
        epics=_read_yaml(epics_path)["epics"],
        tasks=_read_yaml(tasks_path)["tasks"],
    )