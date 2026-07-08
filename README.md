# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

All scheduling logic lives in [pawpal_system.py](pawpal_system.py), split across the
`Task`, `Owner`, and `Scheduler` classes. The table summarizes each feature and the
method that implements it; details follow below.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | [`Scheduler.sort_tasks()`](pawpal_system.py#L248), [`Scheduler.sort_by_time()`](pawpal_system.py#L283) | Priority-then-duration for planning; start-time order for display |
| Filtering | [`Owner.filter_tasks()`](pawpal_system.py#L184), [`Scheduler._all_tasks()`](pawpal_system.py#L235) | By pet name and/or completion status; scheduler skips completed tasks |
| Conflict detection | [`Scheduler.detect_conflicts()`](pawpal_system.py#L292) | Warns on pinned tasks whose time slots overlap |
| Recurring tasks | [`Task.next_occurrence()`](pawpal_system.py#L80), [`Pet.mark_task_complete()`](pawpal_system.py#L150) | Daily/weekly tasks roll forward on completion |

### Sorting behavior

Two distinct orderings serve two different needs:

- **Planning order — [`Scheduler.sort_tasks()`](pawpal_system.py#L248).** Returns
  `(pet, task)` pairs sorted by priority first (`high` → `medium` → `low`, via the
  `PRIORITY_RANK` map) and then by shortest duration as the tie-breaker. Shortest-first
  at equal priority lets us fit more tasks into the same time budget. This is the order
  [`build_plan()`](pawpal_system.py#L259) walks when greedily filling the day.
- **Display order — [`Scheduler.sort_by_time()`](pawpal_system.py#L283).** Once a plan
  is built, this returns its `ScheduledItem`s sorted by `start_minute` (earliest first)
  so the timeline reads chronologically.

### Filtering behavior

- **By pet and/or completion — [`Owner.filter_tasks(completed=None, pet_name=None)`](pawpal_system.py#L184).**
  Both filters are optional and combine with AND. `pet_name` is matched
  case-insensitively (ignoring surrounding whitespace); `completed` keeps only tasks
  whose status matches. Passing neither is equivalent to
  [`Owner.get_all_tasks()`](pawpal_system.py#L180).
- **Skipping completed work — [`Scheduler._all_tasks()`](pawpal_system.py#L235).** The
  scheduler only ever considers not-yet-completed tasks, so the time budget is spent on
  work that still needs doing. Tasks that don't fit the budget are reported separately
  by [`explain()`](pawpal_system.py#L337).

### Conflict detection logic

[`Scheduler.detect_conflicts()`](pawpal_system.py#L292) returns a list of human-readable
warning strings (empty when there are no conflicts, and it never raises). Only tasks
with an explicit `start_time` are checked — the greedy `build_plan()` already lays
unpinned tasks back-to-back so they never overlap, so conflicts only arise when the user
pins two tasks to clashing times. It compares every pair of pinned, incomplete tasks
**across all pets** (one owner can only care for one pet at a time) using the standard
interval-overlap test: two tasks clash when each starts before the other ends
(`start_a < end_b and start_b < end_a`). Warnings are emitted in chronological order.

### Recurring task logic

- **[`Task.next_occurrence(from_date=None)`](pawpal_system.py#L80).** Returns a fresh,
  incomplete copy of the task with its `due_date` advanced by one interval. Only `daily`
  and `weekly` frequencies recur (see the `RECURRENCE_DELTA` map and the
  [`Task.is_recurring`](pawpal_system.py#L71) property); `monthly` and one-off tasks
  return `None`. The next due date is computed from *today* by default (not the old due
  date), so a task completed late still lands one interval from now rather than in the
  past. `timedelta` handles calendar math, so completing a daily task on Dec 31 correctly
  yields Jan 1.
- **[`Pet.mark_task_complete()`](pawpal_system.py#L150).** Marks a task done and, if it
  recurs, appends its next occurrence to the pet's task list — so finishing a daily walk
  automatically queues tomorrow's.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
