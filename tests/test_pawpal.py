"""Tests for the PawPal+ logic layer (pawpal_system.py)."""

import os
import sys
from datetime import date, timedelta

import pytest

# Make the project root importable when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import DEFAULT_DAY_START, Owner, Pet, Scheduler, Task


# --- Simple tests -----------------------------------------------------------

def test_task_completion_changes_status():
    """Calling mark_done() changes the task's status to completed."""
    task = Task(name="Walk", duration=30)
    assert task.completed is False  # starts incomplete
    task.mark_done()
    assert task.completed is True   # status actually changed


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count by one."""
    pet = Pet(name="Rex", species="dog")
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(name="Walk", duration=30))
    assert len(pet.get_tasks()) == 1


# --- Task -------------------------------------------------------------------

def test_task_defaults():
    task = Task(name="Walk", duration=30)
    assert task.priority == "medium"
    assert task.category == "general"
    assert task.frequency == "daily"
    assert task.completed is False


def test_task_normalizes_priority():
    task = Task(name="Walk", duration=30, priority="  HIGH ")
    assert task.priority == "high"


def test_task_rejects_bad_priority():
    with pytest.raises(ValueError):
        Task(name="Walk", duration=30, priority="urgent")


def test_task_rejects_nonpositive_duration():
    with pytest.raises(ValueError):
        Task(name="Walk", duration=0)


def test_task_mark_done_and_undone():
    task = Task(name="Walk", duration=30)
    task.mark_done()
    assert task.completed is True
    task.mark_undone()
    assert task.completed is False


def test_task_due_date_defaults_to_today():
    task = Task(name="Walk", duration=30)
    assert task.due_date == date.today()


# --- Recurrence -------------------------------------------------------------

def test_daily_task_is_recurring_weekly_too():
    assert Task(name="Walk", duration=30, frequency="daily").is_recurring
    assert Task(name="Bath", duration=30, frequency="weekly").is_recurring


def test_monthly_and_oneoff_tasks_do_not_recur():
    assert not Task(name="Vet", duration=30, frequency="monthly").is_recurring
    assert not Task(name="Nails", duration=30, frequency="once").is_recurring


def test_daily_next_occurrence_is_tomorrow():
    task = Task(name="Walk", duration=30, frequency="daily")
    nxt = task.next_occurrence()
    assert nxt.due_date == date.today() + timedelta(days=1)
    assert nxt.completed is False
    # Same task details carry over, but it is a distinct object.
    assert nxt is not task
    assert (nxt.name, nxt.duration, nxt.priority, nxt.frequency) == (
        "Walk", 30, "medium", "daily"
    )


def test_weekly_next_occurrence_is_one_week_out():
    task = Task(name="Bath", duration=30, frequency="weekly")
    nxt = task.next_occurrence()
    assert nxt.due_date == date.today() + timedelta(weeks=1)


def test_next_occurrence_from_explicit_date_rolls_month_boundary():
    task = Task(name="Walk", duration=30, frequency="daily")
    nxt = task.next_occurrence(from_date=date(2024, 12, 31))
    assert nxt.due_date == date(2025, 1, 1)  # timedelta handles year rollover


def test_non_recurring_next_occurrence_is_none():
    task = Task(name="Vet", duration=30, frequency="monthly")
    assert task.next_occurrence() is None


def test_mark_task_complete_spawns_next_daily_occurrence():
    pet = Pet(name="Rex", species="dog")
    walk = Task(name="Walk", duration=30, frequency="daily")
    pet.add_task(walk)

    follow_up = pet.mark_task_complete(walk)

    assert walk.completed is True
    assert follow_up in pet.get_tasks()          # auto-added to the list
    assert follow_up.completed is False
    assert follow_up.due_date == date.today() + timedelta(days=1)
    assert len(pet.get_tasks()) == 2             # original + next occurrence


def test_mark_task_complete_does_not_respawn_non_recurring():
    pet = Pet(name="Rex", species="dog")
    vet = Task(name="Vet", duration=30, frequency="monthly")
    pet.add_task(vet)

    follow_up = pet.mark_task_complete(vet)

    assert vet.completed is True
    assert follow_up is None
    assert pet.get_tasks() == [vet]              # nothing new added


# --- Pet --------------------------------------------------------------------

def test_pet_add_and_get_tasks():
    pet = Pet(name="Rex", species="dog")
    task = Task(name="Walk", duration=30)
    pet.add_task(task)
    assert pet.get_tasks() == [task]


def test_pet_remove_task_by_identity():
    pet = Pet(name="Rex", species="dog")
    a = Task(name="Walk", duration=20)
    b = Task(name="Walk", duration=20)  # same fields, different object
    pet.add_task(a)
    pet.add_task(b)
    pet.remove_task(a)
    assert pet.get_tasks() == [b]


# --- Owner ------------------------------------------------------------------

def test_owner_get_all_tasks_flattens_across_pets():
    owner = Owner(name="Harvey", available_minutes=120)
    rex = Pet(name="Rex", species="dog")
    milo = Pet(name="Milo", species="cat")
    rex.add_task(Task(name="Walk", duration=30))
    milo.add_task(Task(name="Feed", duration=10))
    owner.add_pet(rex)
    owner.add_pet(milo)
    names = {t.name for t in owner.get_all_tasks()}
    assert names == {"Walk", "Feed"}


def _owner_with_two_pets():
    owner = Owner(name="Harvey", available_minutes=120)
    rex = Pet(name="Rex", species="dog")
    milo = Pet(name="Milo", species="cat")
    walk = Task(name="Walk", duration=30)
    walk.mark_done()
    rex.add_task(walk)
    rex.add_task(Task(name="Feed", duration=10))
    milo.add_task(Task(name="Groom", duration=15))
    owner.add_pet(rex)
    owner.add_pet(milo)
    return owner


def test_filter_tasks_no_args_matches_get_all_tasks():
    owner = _owner_with_two_pets()
    assert owner.filter_tasks() == owner.get_all_tasks()


def test_filter_tasks_by_completion_status():
    owner = _owner_with_two_pets()
    done = owner.filter_tasks(completed=True)
    todo = owner.filter_tasks(completed=False)
    assert {t.name for t in done} == {"Walk"}
    assert {t.name for t in todo} == {"Feed", "Groom"}


def test_filter_tasks_by_pet_name_is_case_insensitive():
    owner = _owner_with_two_pets()
    tasks = owner.filter_tasks(pet_name="  rex ")
    assert {t.name for t in tasks} == {"Walk", "Feed"}


def test_filter_tasks_combines_both_filters():
    owner = _owner_with_two_pets()
    tasks = owner.filter_tasks(completed=False, pet_name="Rex")
    assert {t.name for t in tasks} == {"Feed"}


# --- Scheduler --------------------------------------------------------------

def _owner_with_tasks():
    owner = Owner(name="Harvey", available_minutes=60)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task(name="Feed", duration=15, priority="high"))
    pet.add_task(Task(name="Walk", duration=30, priority="high"))
    pet.add_task(Task(name="Play", duration=20, priority="low"))
    owner.add_pet(pet)
    return owner


def test_scheduler_orders_by_priority_then_duration():
    scheduler = Scheduler(_owner_with_tasks())
    plan = scheduler.build_plan()
    names = [item.task.name for item in plan]
    # High priority first; within high, shortest first -> Feed before Walk.
    assert names[:2] == ["Feed", "Walk"]


def test_scheduler_respects_time_budget():
    # Budget 60 fits Feed(15)+Walk(30)=45; Play(20) would exceed -> skipped.
    scheduler = Scheduler(_owner_with_tasks())
    plan = scheduler.build_plan()
    assert scheduler.total_time() == 45
    assert "Play" not in [item.task.name for item in plan]


def test_scheduler_lays_tasks_back_to_back():
    scheduler = Scheduler(_owner_with_tasks())
    plan = scheduler.build_plan()
    assert plan[0].start_minute == DEFAULT_DAY_START
    for earlier, later in zip(plan, plan[1:]):
        assert later.start_minute == earlier.end_minute


def test_scheduler_skips_completed_tasks():
    owner = _owner_with_tasks()
    owner.pets[0].get_tasks()[0].mark_done()  # complete "Feed"
    scheduler = Scheduler(owner)
    plan = scheduler.build_plan()
    assert "Feed" not in [item.task.name for item in plan]


def test_scheduler_explain_mentions_skipped():
    scheduler = Scheduler(_owner_with_tasks())
    text = scheduler.explain()
    assert "Skipped" in text
    assert "Play" in text


def test_sort_by_time_orders_by_start_minute():
    scheduler = Scheduler(_owner_with_tasks())
    scheduler.build_plan()
    ordered = scheduler.sort_by_time()
    starts = [item.start_minute for item in ordered]
    assert starts == sorted(starts)


def test_sort_by_time_defaults_to_built_plan():
    scheduler = Scheduler(_owner_with_tasks())
    plan = scheduler.build_plan()
    # A freshly built plan is already laid out in start-time order.
    assert scheduler.sort_by_time() == plan


def test_sort_by_time_sorts_a_shuffled_plan():
    scheduler = Scheduler(_owner_with_tasks())
    plan = scheduler.build_plan()
    shuffled = list(reversed(plan))
    ordered = scheduler.sort_by_time(shuffled)
    assert ordered == plan  # restored to earliest-first order


# --- Conflict detection -----------------------------------------------------

def test_task_rejects_out_of_range_start_time():
    with pytest.raises(ValueError):
        Task(name="Walk", duration=30, start_time=24 * 60)


def _owner_with_pinned(*specs):
    """Build an owner whose (pet_name, task_name, start, duration) specs are pinned."""
    owner = Owner(name="Harvey", available_minutes=600)
    pets = {}
    for pet_name, task_name, start, duration in specs:
        pet = pets.get(pet_name)
        if pet is None:
            pet = Pet(name=pet_name, species="dog")
            pets[pet_name] = pet
            owner.add_pet(pet)
        pet.add_task(Task(name=task_name, duration=duration, start_time=start))
    return owner


def test_no_conflict_when_no_tasks_pinned():
    scheduler = Scheduler(_owner_with_tasks())  # nothing has a start_time
    assert scheduler.detect_conflicts() == []


def test_no_conflict_for_back_to_back_pinned_tasks():
    # Walk 09:00-09:30 then Feed 09:30-09:45 touch but do not overlap.
    owner = _owner_with_pinned(
        ("Rex", "Walk", 9 * 60, 30),
        ("Rex", "Feed", 9 * 60 + 30, 15),
    )
    assert Scheduler(owner).detect_conflicts() == []


def test_detects_conflict_between_two_pets():
    owner = _owner_with_pinned(
        ("Rex", "Vet visit", 9 * 60, 30),        # 09:00-09:30
        ("Milo", "Grooming", 9 * 60 + 15, 20),   # 09:15-09:35 -> overlaps
    )
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1
    assert "Vet visit" in warnings[0]
    assert "Grooming" in warnings[0]


def test_detects_conflict_within_same_pet():
    owner = _owner_with_pinned(
        ("Rex", "Walk", 9 * 60, 30),      # 09:00-09:30
        ("Rex", "Play", 9 * 60 + 10, 20),  # 09:10-09:30 -> overlaps
    )
    assert len(Scheduler(owner).detect_conflicts()) == 1


def test_completed_pinned_task_is_ignored():
    owner = _owner_with_pinned(
        ("Rex", "Walk", 9 * 60, 30),
        ("Milo", "Grooming", 9 * 60 + 15, 20),
    )
    owner.pets[0].get_tasks()[0].mark_done()  # complete the Walk
    assert Scheduler(owner).detect_conflicts() == []
