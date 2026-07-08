"""PawPal+ logic layer.

Backend classes for the PawPal+ pet care planning assistant. This module holds
all the domain logic (Owner, Pet, Task) and the scheduling logic (Scheduler),
kept separate from the Streamlit UI in app.py.

This is the class skeleton (names, attributes, and empty method stubs) based on
diagrams/uml.mmd. Logic will be filled in later.
"""

from dataclasses import dataclass, field


@dataclass
class Task:
    """A single pet care task, e.g. a morning walk or feeding."""

    name: str
    duration: int  # minutes
    priority: str = "medium"  # "high" | "medium" | "low"
    category: str = "general"  # e.g. "walk", "feeding", "meds", "grooming"

    def __repr__(self) -> str:
        ...


@dataclass
class Pet:
    """A pet that has a list of care tasks."""

    name: str
    species: str
    breed: str = ""
    tasks: list = field(default_factory=list)

    def add_task(self, task: "Task") -> None:
        """Add a care task for this pet."""
        ...

    def remove_task(self, task: "Task") -> None:
        """Remove a care task if it is present."""
        ...

    def get_tasks(self) -> list:
        """Return this pet's list of tasks."""
        ...


@dataclass
class Owner:
    """A pet owner with a daily time budget and one or more pets."""

    name: str
    available_minutes: int = 0
    pets: list = field(default_factory=list)

    def add_pet(self, pet: "Pet") -> None:
        """Add a pet to this owner."""
        ...


class Scheduler:
    """Builds a daily plan for a pet within a time budget."""

    def __init__(self, pet: "Pet", available_minutes: int):
        self.pet = pet
        self.available_minutes = available_minutes

    def sort_tasks(self) -> list:
        """Return this pet's tasks ordered by priority, then shortest first."""
        ...

    def build_plan(self) -> list:
        """Choose tasks that fit within the available minutes."""
        ...

    def total_time(self, plan: list) -> int:
        """Return the total number of minutes used by a plan."""
        ...

    def explain(self) -> str:
        """Return a human-readable explanation of the generated plan."""
        ...
