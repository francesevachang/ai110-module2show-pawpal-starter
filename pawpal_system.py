"""PawPal+ logic layer.

Backend classes for the PawPal+ pet care planning assistant. This module holds
all the domain logic (Owner, Pet, Task) and the scheduling logic (Scheduler),
kept separate from the Streamlit UI in app.py.

"""

from dataclasses import dataclass, field

# Lower rank == higher priority. Sorting uses this so "high" beats "medium"
# beats "low"
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Default start of the care day, in minutes since midnight (07:00).
DEFAULT_DAY_START = 7 * 60


def _format_clock(minute_of_day: int) -> str:
    """Turn minutes-since-midnight into a HH:MM label, e.g. 450 -> '07:30'."""
    minute_of_day %= 24 * 60
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


@dataclass
class Task:
    """A single pet care task, e.g. a morning walk or feeding."""

    name: str
    duration: int  # minutes
    priority: str = "medium"  # "high" | "medium" | "low"
    category: str = "general"  # e.g. "walk", "feeding", "meds", "grooming"
    frequency: str = "daily"  # e.g. "daily", "weekly", "monthly"
    completed: bool = False  # whether the task has been done

    def __post_init__(self) -> None:
        # Normalize and validate up front so a typo can't silently sort a task
        # to the bottom of the plan later on.
        self.priority = str(self.priority).strip().lower()
        if self.priority not in PRIORITY_RANK:
            raise ValueError(
                f"priority must be one of {sorted(PRIORITY_RANK)}, got {self.priority!r}"
            )
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration!r}")

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_undone(self) -> None:
        """Mark this task as not yet completed."""
        self.completed = False

    def __repr__(self) -> str:
        status = "done" if self.completed else "todo"
        return (
            f"Task({self.name!r}, {self.duration}min, {self.priority}, "
            f"{self.category}, {self.frequency}, {status})"
        )


@dataclass
class Pet:
    """A pet that has a list of care tasks."""

    name: str
    species: str
    breed: str = ""
    tasks: list = field(default_factory=list)

    def add_task(self, task: "Task") -> None:
        """Add a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, task: "Task") -> None:
        """Remove a care task if it is present.

        Matches by identity, not value, so two tasks that happen to have the
        same fields (e.g. two 20-minute medium walks) are treated as distinct
        and we never remove the wrong one.
        """
        for i, existing in enumerate(self.tasks):
            if existing is task:
                del self.tasks[i]
                return

    def get_tasks(self) -> list:
        """Return this pet's list of tasks."""
        return self.tasks


@dataclass
class Owner:
    """A pet owner with a daily time budget and one or more pets."""

    name: str
    available_minutes: int = 0
    pets: list = field(default_factory=list)

    def add_pet(self, pet: "Pet") -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list:
        """Return every task across all of this owner's pets, flattened."""
        return [task for pet in self.pets for task in pet.get_tasks()]


@dataclass
class ScheduledItem:
    """One task placed on the day's timeline, with the pet it belongs to."""

    pet: Pet
    task: Task
    start_minute: int  # minutes since midnight

    @property
    def end_minute(self) -> int:
        return self.start_minute + self.task.duration


class Scheduler:
    """Builds a daily plan across all of an owner's pets within one time budget."""

    def __init__(self, owner: "Owner", day_start_minute: int = DEFAULT_DAY_START):
        self.owner = owner
        self.day_start_minute = day_start_minute
        self.plan: list = []  # cached result of the last build_plan() call

    @property
    def available_minutes(self) -> int:
        """The owner's daily budget, read live so Owner stays the source of truth."""
        return self.owner.available_minutes

    def _all_tasks(self) -> list:
        """Flatten every pet's not-yet-completed tasks into (pet, task) pairs.

        Completed tasks are skipped so the budget is spent only on work that
        still needs doing.
        """
        return [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.get_tasks()
            if not task.completed
        ]

    def sort_tasks(self) -> list:
        """Return (pet, task) pairs ordered by priority, then shortest first.

        Shortest-first as the tie-breaker means that, at equal priority, we can
        fit more tasks into the same budget.
        """
        return sorted(
            self._all_tasks(),
            key=lambda pair: (PRIORITY_RANK[pair[1].priority], pair[1].duration),
        )

    def build_plan(self) -> list:
        """Choose tasks that fit within the available minutes and time them.

        Greedy heuristic: walk the tasks in priority/duration order and take each
        one that still fits in the remaining budget, laying them back-to-back
        starting at day_start_minute. This is fast and predictable but not
        guaranteed optimal (see explain()).
        """
        remaining = self.available_minutes
        clock = self.day_start_minute
        plan: list = []
        for pet, task in self.sort_tasks():
            if task.duration <= remaining:
                plan.append(ScheduledItem(pet, task, clock))
                clock += task.duration
                remaining -= task.duration
        self.plan = plan
        return plan

    def total_time(self, plan: list = None) -> int:
        """Return the total minutes used by a plan (defaults to the built plan)."""
        plan = self.plan if plan is None else plan
        return sum(item.task.duration for item in plan)

    def explain(self) -> str:
        """Return a human-readable explanation of the generated plan."""
        if not self.plan:
            self.build_plan()

        lines = [
            f"Plan for {self.owner.name} "
            f"({self.total_time()} of {self.available_minutes} min used):"
        ]
        for item in self.plan:
            lines.append(
                f"  {_format_clock(item.start_minute)}-{_format_clock(item.end_minute)}  "
                f"{item.task.name} ({item.pet.name}, {item.task.priority} priority, "
                f"{item.task.duration} min)"
            )

        scheduled = {id(item.task) for item in self.plan}
        skipped = [
            (pet, task)
            for pet, task in self._all_tasks()
            if id(task) not in scheduled
        ]
        if skipped:
            lines.append("Skipped (did not fit the time budget):")
            for pet, task in skipped:
                lines.append(
                    f"  {task.name} ({pet.name}, {task.priority} priority, "
                    f"{task.duration} min)"
                )

        lines.append(
            "Tasks are chosen highest-priority first, shortest-first to break ties; "
            "this fills the budget greedily rather than searching for the optimal mix."
        )
        return "\n".join(lines)
