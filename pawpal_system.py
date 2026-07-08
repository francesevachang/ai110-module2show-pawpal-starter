"""PawPal+ logic layer.

Backend classes for the PawPal+ pet care planning assistant. This module holds
all the domain logic (Owner, Pet, Task) and the scheduling logic (Scheduler),
kept separate from the Streamlit UI in app.py.

"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations

# Lower rank == higher priority. Sorting uses this so "high" beats "medium"
# beats "low"
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# How far ahead the next occurrence of a recurring task falls. Only these
# frequencies recur automatically; "monthly" and one-off tasks do not.
RECURRENCE_DELTA = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}

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
    due_date: date = field(default_factory=date.today)  # when this task is due
    start_time: int = None  # optional fixed start, minutes since midnight

    def __post_init__(self) -> None:
        """Normalize and validate the priority, duration and start_time fields."""
        # Normalize and validate up front so a typo can't silently sort a task
        # to the bottom of the plan later on.
        self.priority = str(self.priority).strip().lower()
        if self.priority not in PRIORITY_RANK:
            raise ValueError(
                f"priority must be one of {sorted(PRIORITY_RANK)}, got {self.priority!r}"
            )
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration!r}")
        if self.start_time is not None and not (0 <= self.start_time < 24 * 60):
            raise ValueError(
                f"start_time must be within a day (0-1439 min), got {self.start_time!r}"
            )

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_undone(self) -> None:
        """Mark this task as not yet completed."""
        self.completed = False

    @property
    def is_recurring(self) -> bool:
        """True if this task repeats on a schedule we roll forward automatically.

        Only the frequencies in RECURRENCE_DELTA ("daily", "weekly") recur;
        "monthly" and one-off tasks return False.
        """
        return self.frequency in RECURRENCE_DELTA

    def next_occurrence(self, from_date: date = None) -> "Task":
        """Return a fresh, incomplete copy of this task due next time around.

        The new task keeps every field except that ``completed`` resets to False
        and ``due_date`` advances by this frequency's timedelta (one day for
        "daily", one week for "weekly"). ``timedelta`` handles the calendar math
        for us — adding ``timedelta(days=1)`` to any date rolls month and year
        boundaries correctly, so completing a daily task on Dec 31 yields Jan 1.

        Args:
            from_date: the date to advance from; defaults to today. Basing the
                next due date on today (rather than the old due date) means a
                task completed late still lands one interval from now, not in
                the past.

        Returns:
            The next Task, or None if this task's frequency does not recur.
        """
        if not self.is_recurring:
            return None
        base = date.today() if from_date is None else from_date
        return Task(
            name=self.name,
            duration=self.duration,
            priority=self.priority,
            category=self.category,
            frequency=self.frequency,
            completed=False,
            due_date=base + RECURRENCE_DELTA[self.frequency],
        )

    def __repr__(self) -> str:
        """Return a compact string showing the task's fields and status."""
        status = "done" if self.completed else "todo"
        return (
            f"Task({self.name!r}, {self.duration}min, {self.priority}, "
            f"{self.category}, {self.frequency}, due {self.due_date.isoformat()}, "
            f"{status})"
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

    def mark_task_complete(self, task: "Task") -> "Task":
        """Mark a task done and, if it recurs, schedule its next occurrence.

        For "daily" and "weekly" tasks this appends a fresh, incomplete copy to
        the pet's task list with its due date rolled forward (see
        Task.next_occurrence). Non-recurring tasks ("monthly", one-offs) are
        simply marked done.

        Returns:
            The newly created follow-up Task, or None if the task does not recur.
        """
        task.mark_done()
        follow_up = task.next_occurrence()
        if follow_up is not None:
            self.add_task(follow_up)
        return follow_up


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

    def filter_tasks(self, completed: bool = None, pet_name: str = None) -> list:
        """Return tasks across all pets, filtered by completion and/or pet name.

        Both filters are optional and combine (AND) when given together; passing
        neither returns the same tasks as get_all_tasks().

        Args:
            completed: if not None, keep only tasks whose .completed matches.
            pet_name: if not None, keep only tasks of the pet with this name
                (matched case-insensitively, ignoring surrounding whitespace).
        """
        wanted_pet = None if pet_name is None else pet_name.strip().lower()
        result = []
        for pet in self.pets:
            if wanted_pet is not None and pet.name.strip().lower() != wanted_pet:
                continue
            for task in pet.get_tasks():
                if completed is not None and task.completed != completed:
                    continue
                result.append(task)
        return result


@dataclass
class ScheduledItem:
    """One task placed on the day's timeline, with the pet it belongs to."""

    pet: Pet
    task: Task
    start_minute: int  # minutes since midnight

    @property
    def end_minute(self) -> int:
        """Return when this item ends, in minutes since midnight."""
        return self.start_minute + self.task.duration


class Scheduler:
    """Builds a daily plan across all of an owner's pets within one time budget."""

    def __init__(self, owner: "Owner", day_start_minute: int = DEFAULT_DAY_START):
        """Set up the scheduler for an owner and the time the care day starts."""
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

    def sort_by_time(self, plan: list = None) -> list:
        """Return a plan's items ordered by scheduled start time, earliest first.

        Sorts the ScheduledItem objects by their start_minute (when each task is
        placed on the day). Defaults to the built plan, matching total_time().
        """
        plan = self.plan if plan is None else plan
        return sorted(plan, key=lambda item: item.start_minute)

    def detect_conflicts(self) -> list:
        """Return warning messages for tasks pinned to overlapping times.

        Lightweight strategy: only tasks given an explicit ``start_time`` are
        checked. The greedy build_plan already lays unpinned tasks back-to-back
        so they never overlap; conflicts only arise when the user fixes two
        tasks to clashing times. We compare every pair of pinned tasks *across
        all pets* — one owner can only care for one pet at a time — and return
        one warning string per overlapping pair.

        Two tasks overlap when one starts before the other ends. Completed
        tasks are ignored since they no longer need a slot.

        Returns:
            A list of warning strings, empty when there are no conflicts. This
            method never raises, so callers can surface warnings without
            wrapping it in error handling.
        """
        pinned = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.get_tasks()
            if task.start_time is not None and not task.completed
        ]
        # Sort by start time so each conflict is reported earlier-task-first and
        # the warnings themselves come out in chronological order — easier to
        # scan than an arbitrary order. (The list is tiny, so we don't rely on
        # the sort for speed.)
        pinned.sort(key=lambda pair: pair[1].start_time)

        warnings: list = []
        for (pet_a, task_a), (pet_b, task_b) in combinations(pinned, 2):
            start_a, end_a = task_a.start_time, task_a.start_time + task_a.duration
            start_b, end_b = task_b.start_time, task_b.start_time + task_b.duration
            # Two intervals overlap when each starts before the other ends.
            if start_a < end_b and start_b < end_a:
                warnings.append(
                    f"⚠️ Time conflict: "
                    f"'{task_a.name}' ({pet_a.name}, "
                    f"{_format_clock(start_a)}-{_format_clock(end_a)}) overlaps "
                    f"'{task_b.name}' ({pet_b.name}, "
                    f"{_format_clock(start_b)}-{_format_clock(end_b)})."
                )
        return warnings

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
