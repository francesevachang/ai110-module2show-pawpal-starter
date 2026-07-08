"""PawPal+ demo script.

Builds a small pet-care household and prints today's schedule to the terminal.
Run with:  python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler, _format_clock


def main() -> None:
    # An owner with a daily care-time budget (in minutes).
    owner = Owner(name="Harvey", available_minutes=180)

    # At least two pets.
    rex = Pet(name="Rex", species="dog", breed="Labrador")
    milo = Pet(name="Milo", species="cat", breed="Tabby")
    owner.add_pet(rex)
    owner.add_pet(milo)

    # Add tasks deliberately OUT OF ORDER (mixed priorities, not by time) so the
    # scheduler's sorting has real work to do rather than getting them pre-sorted.
    rex.add_task(Task(name="Play time", duration=20, priority="low", category="play"))
    milo.add_task(Task(name="Litter cleanup", duration=10, priority="medium", category="grooming"))
    rex.add_task(Task(name="Morning walk", duration=30, priority="high", category="walk"))
    milo.add_task(Task(name="Evening feed", duration=15, priority="medium", category="feeding"))
    rex.add_task(Task(name="Breakfast", duration=15, priority="high", category="feeding"))

    # Mark one task done so the completion filter has something to show.
    rex.get_tasks()[0].mark_done()  # "Play time" is already handled

    # Build the day's plan within the owner's time budget.
    scheduler = Scheduler(owner)
    scheduler.build_plan()

    # Print "Today's Schedule".
    print("Today's Schedule")
    print("=" * 40)
    print(scheduler.explain())

    # --- New sorting method: plan items ordered by scheduled start time --------
    print("\nBy scheduled time (sort_by_time)")
    print("=" * 40)
    for item in scheduler.sort_by_time():
        print(
            f"  {_format_clock(item.start_minute)}-{_format_clock(item.end_minute)}  "
            f"{item.task.name} ({item.pet.name})"
        )

    # --- New filtering method: filter tasks by status or pet name --------------
    print("\nFiltering tasks (filter_tasks)")
    print("=" * 40)

    done = owner.filter_tasks(completed=True)
    print("Completed:", [t.name for t in done])

    todo = owner.filter_tasks(completed=False)
    print("Still to do:", [t.name for t in todo])

    rex_tasks = owner.filter_tasks(pet_name="Rex")
    print("Rex's tasks:", [t.name for t in rex_tasks])

    rex_todo = owner.filter_tasks(completed=False, pet_name="Rex")
    print("Rex's remaining tasks:", [t.name for t in rex_todo])

    # --- Recurring tasks: completing one schedules the next occurrence --------
    print("\nRecurring tasks (mark_task_complete)")
    print("=" * 40)

    walk = next(t for t in rex.get_tasks() if t.name == "Morning walk")
    print(f"Before: Rex has {len(rex.get_tasks())} tasks; '{walk.name}' due {walk.due_date}.")

    next_walk = rex.mark_task_complete(walk)  # daily task -> auto-schedules tomorrow
    print(
        f"Completed '{walk.name}'. Auto-created next occurrence due {next_walk.due_date} "
        f"(today + 1 day)."
    )
    print(f"After: Rex has {len(rex.get_tasks())} tasks.")

    # --- Conflict detection: two tasks pinned to the same time ----------------
    print("\nConflict detection (detect_conflicts)")
    print("=" * 40)

    # Pin two tasks to overlapping times: Rex's vet visit at 09:00 for 30 min
    # and Milo's grooming at 09:15 for 20 min. One owner can't do both at once.
    rex.add_task(Task(name="Vet visit", duration=30, priority="high", start_time=9 * 60))
    milo.add_task(Task(name="Grooming", duration=20, priority="medium", start_time=9 * 60 + 15))

    warnings = scheduler.detect_conflicts()
    if warnings:
        print(f"Found {len(warnings)} conflict(s):")
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("No time conflicts detected.")


if __name__ == "__main__":
    main()
