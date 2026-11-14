from calendar import Calendar, monthrange
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from data import now_local
from schedule_export import schedule

ASSETS = Path(__file__).parent / "assets"
month_grid = st.components.v2.component(
    "recovery_month", html='<div class="calendar"></div>',
    css=(ASSETS / "month.css").read_text(encoding="utf8"),
    js=(ASSETS / "month.js").read_text(encoding="utf8"),
)


def move_month(selected, offset):
    year, index = divmod(selected.year * 12 + selected.month - 1 + offset, 12)
    return date(year, index + 1, min(selected.day, monthrange(year, index + 1)[1]))


def month_view(plan):
    selected = st.session_state.setdefault("calendar_day", now_local().date())
    first = selected.replace(day=1)
    events = {}
    for when, title, detail in schedule(plan, first, monthrange(first.year, first.month)[1]):
        timed = isinstance(when, datetime)
        day = when.date() if timed else when
        kind = "dose" if timed else "refill" if title.startswith("Refill ·") else "visit"
        events.setdefault(day, []).append({"title": title, "kind": kind, "detail": detail,
                                          "time": when.strftime("%I:%M %p").lstrip("0") if timed else "All day",
                                          "order": when.strftime("%H:%M") if timed else ""})
    days = [{"iso": d.isoformat(), "number": d.day, "inMonth": d.month == first.month,
             "events": sorted(events.get(d, []), key=lambda e: (e["kind"] == "dose", e["order"]))}
            for d in Calendar(firstweekday=6).itermonthdates(first.year, first.month)]

    def choose():
        picked = st.session_state.recovery_dates.get("picked")
        if picked:
            st.session_state.calendar_day = date.fromisoformat(picked)

    month_grid(data={"days": days, "selected": selected.isoformat(), "today": now_local().date().isoformat(),
                     "month": selected.strftime("%B"), "year": selected.year,
                     "previous": move_month(selected, -1).isoformat(), "next": move_month(selected, 1).isoformat(),
                     "dayLabel": selected.strftime("%A, %B %d")}, key="recovery_dates", on_picked_change=choose)
    return selected
