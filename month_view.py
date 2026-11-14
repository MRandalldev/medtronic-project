from calendar import Calendar, monthrange
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from schedule_export import schedule

ASSETS = Path(__file__).parent / "assets"
month_grid = st.components.v2.component(
    "recovery_month",
    html='<div class="month" role="group" aria-label="Recovery dates"></div>',
    css=(ASSETS / "month.css").read_text(encoding="utf8"),
    js=(ASSETS / "month.js").read_text(encoding="utf8"),
)


def move_month(selected, offset):
    year, index = divmod(selected.year * 12 + selected.month - 1 + offset, 12)
    return date(year, index + 1, min(selected.day, monthrange(year, index + 1)[1]))


def month_view(plan):
    selected = st.session_state.get("calendar_day", date.today())
    left, center, right = st.columns([1, 2, 1], vertical_alignment="center")
    if left.button("← Previous", key="previous_month"):
        selected = move_month(selected, -1)
    if right.button("Next →", key="next_month"):
        selected = move_month(selected, 1)
    center.subheader(selected.strftime("%B %Y"))
    first = selected.replace(day=1)
    counts = {}
    for when, title, _ in schedule(plan, first, monthrange(first.year, first.month)[1]):
        day = when.date() if isinstance(when, datetime) else when
        counts.setdefault(day, []).append(title)
    days = []
    for day in Calendar(firstweekday=6).itermonthdates(first.year, first.month):
        days.append({"iso": day.isoformat(), "number": day.day, "inMonth": day.month == first.month,
                     "today": day == date.today(), "events": counts.get(day, [])})
    key = first.isoformat()
    def choose():
        state = st.session_state.get("grid_" + key, {})
        picked = state.get("picked")
        if picked:
            st.session_state.calendar_day = date.fromisoformat(picked)
    st.session_state.calendar_day = selected
    month_grid(data={"days": days, "selected": selected.isoformat()}, key="grid_" + key, on_picked_change=choose)
    return selected
