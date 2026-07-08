import streamlit as st

from pawpal_system import Task, Pet, Owner, ScheduledItem, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")
available_minutes = st.number_input(
    "Time available today (minutes)", min_value=0, max_value=1440, value=120
)

# --- Persist the Owner in the session "vault" -------------------------------
# Streamlit reruns this whole file top-to-bottom on every interaction. We only
# want to build the Owner once; the `not in` guard keeps the same object alive
# across reruns so the pets and tasks we add don't vanish on the next click.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name, available_minutes=int(available_minutes))

owner = st.session_state.owner

# The stored Owner is static — widget edits don't reach back into it
# automatically — so sync its mutable fields from the inputs on each rerun.
owner.name = owner_name
owner.available_minutes = int(available_minutes)

st.divider()

# --- Adding a Pet -----------------------------------------------------------
st.subheader("Pets")
st.caption("Add one or more pets; each keeps its own list of care tasks.")

col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_p2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    owner.add_pet(Pet(name=pet_name, species=species))

if not owner.pets:
    st.info("No pets yet. Add one above to start planning.")
    st.stop()

# Pick which pet new tasks attach to. We key the selectbox by list index rather
# than name so two pets sharing a name stay distinct.
pet_index = st.selectbox(
    "Active pet (tasks below are added to this pet)",
    options=range(len(owner.pets)),
    format_func=lambda i: f"{owner.pets[i].name} ({owner.pets[i].species})",
)
pet = owner.pets[pet_index]

st.divider()

# --- Scheduling a Task ------------------------------------------------------
st.subheader("Tasks")
st.caption(f"Add care tasks for {pet.name}. These feed directly into your scheduler.")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    pet.add_task(Task(name=task_title, duration=int(duration), priority=priority))

tasks = pet.get_tasks()
if tasks:
    st.write(f"Current tasks for {pet.name}:")
    st.table(
        [
            {
                "title": t.name,
                "duration_minutes": t.duration,
                "priority": t.priority,
            }
            for t in tasks
        ]
    )
else:
    st.info(f"No tasks yet for {pet.name}. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Runs your Scheduler across every pet, within the owner's time budget.")

if st.button("Generate schedule"):
    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner)
        scheduler.build_plan()
        st.code(scheduler.explain(), language="text")
