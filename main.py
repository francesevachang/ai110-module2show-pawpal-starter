"""PawPal+ demo script.

Builds a small pet-care household and prints today's schedule to the terminal.
Run with:  python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # An owner with a daily care-time budget (in minutes).
    owner = Owner(name="Harvey", available_minutes=180)

    # At least two pets.
    rex = Pet(name="Rex", species="dog", breed="Labrador")
    milo = Pet(name="Milo", species="cat", breed="Tabby")
    owner.add_pet(rex)
    owner.add_pet(milo)

    # At least three tasks. The scheduler lays these out back-to-back starting
    # at the day start, so each ends up at a different time of day.
    rex.add_task(Task(name="Morning walk", duration=30, priority="high", category="walk"))
    rex.add_task(Task(name="Breakfast", duration=15, priority="high", category="feeding"))
    milo.add_task(Task(name="Litter cleanup", duration=10, priority="medium", category="grooming"))
    milo.add_task(Task(name="Play time", duration=20, priority="low", category="play"))

    # Build the day's plan within the owner's time budget.
    scheduler = Scheduler(owner)
    scheduler.build_plan()

    # Print "Today's Schedule".
    print("Today's Schedule")
    print("=" * 40)
    print(scheduler.explain())


if __name__ == "__main__":
    main()
