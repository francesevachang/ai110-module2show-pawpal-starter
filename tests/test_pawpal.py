"""Tests for the PawPal+ logic layer (pawpal_system.py)."""

import os
import sys

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
