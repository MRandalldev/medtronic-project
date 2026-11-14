"""rail.py: the right-hand column. On most pages: a profile header, reminders, quick links and achievements
(laid out like a game profile page). On the Calendar: the selected day's schedule."""
from datetime import date, timedelta
from html import escape

import streamlit as st

import data
import ui
from schedule_export import schedule


def _badges(p: dict) -> list:
    """(label, unlocked, how to earn) — computed only from the patient's own record."""
    checkins = p.get("checkins", [])
    streak = ui.check_in_streak(p)
    walked = max((c.get("numbers", {}).get("walk_min") or 0 for c in checkins), default=0)
    doses = data.adherence(p)
    yesterday = (data.now_local().date() - timedelta(days=1)).isoformat()
    log = p.get("med_log", {}).get(yesterday, {})
    all_yesterday = bool(data.scheduled_doses(p)) and all(log.get(f"{n} {t}") for n, t in data.scheduled_doses(p))
    return [("First check-in", bool(checkins), "Do your first daily check-in"),
            ("3-day streak", streak >= 3, "Check in 3 days in a row"),
            ("7-day streak", streak >= 7, "Check in 7 days in a row"),
            ("Every dose", all_yesterday, "Mark every dose taken for a whole day"),
            ("On your feet", walked >= 20, "Walk 20 minutes in a day"),
            ("Papers in", bool(p.get("documents")), "Add your discharge papers"),
            ("Team player", any(m.get("from") == "Patient" for m in p.get("messages", [])), "Send your care team a message"),
            ("Steady week", doses["due"] >= 7 and doses["taken"] / doses["due"] >= 0.9, "Take 90% of doses for a week")]


def profile_card(p: dict) -> None:
    name = p.get("name") or "Your recovery"
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "R"
    day = data.days_since_surgery(p)
    badges = _badges(p)
    earned = sum(b[1] for b in badges)
    streak = ui.check_in_streak(p)
    st.html(f'''<div class="rail-profile"><div class="banner"></div>
      <div class="who"><div class="avatar">{escape(initials)}</div><div><div class="name">{escape(name)}</div>
      <div class="sub">{f"Recovery day {day}" if day is not None else "Add your surgery date"}</div></div></div>
      <div class="stats"><div><b>{streak}</b><span>day streak</span></div><div><b>{earned}/{len(badges)}</b><span>badges</span></div>
      <div><b>{len(p.get("checkins", []))}</b><span>check-ins</span></div></div></div>''')


def reminders(p: dict) -> None:
    items = []
    if not data.checked_in_today(p):
        items.append(("due", "Daily check-in", "Not done yet today", "pages/3_Check_in.py"))
    late = data.overdue_doses(p)
    if late:
        items.append(("due", f"{late[0][0]}", f"Due at {data.clock_12(late[0][1])}" + (f" · {len(late) - 1} more waiting" if len(late) > 1 else ""),
                      "pages/4_Dashboard.py"))
    else:
        nxt = data.next_dose(p)
        if nxt:
            items.append(("info", nxt[1], f"Next dose at {data.clock_12(nxt[0])}", "pages/4_Dashboard.py"))
    for r in data.refill_reminders(p, within=7):
        items.append(("due", f"Refill {r['name']}", f"By {data.human_date(r['date'])}", "pages/4_Dashboard.py"))
    visit = data.next_visit(p)
    if visit:
        items.append(("info", visit[1]["with"], data.human_date(visit[1]["date"]), "pages/6_Calendar.py"))
    new = data.unread(p, "Care team")
    if new:
        items.append(("info", f"{new} new message{'s' if new != 1 else ''}", "From your care team", "pages/messages.py"))
    with st.container(key="rail_reminders"):
        st.html('<p class="rail-title">Reminders</p>')
        if not items:
            st.html('<p class="rail-empty">You\'re all caught up.</p>')
        for n, (kind, title, sub, page) in enumerate(items[:5]):
            with st.container(key=f"rail_item_{kind}_{n}"):
                st.page_link(page, label=f"**{title}**  \n{sub}")


def quick_links(p: dict) -> None:
    with st.container(key="rail_quick"):
        st.html('<p class="rail-title">Quick access</p>')
        links = [("pages/3_Check_in.py", "Check in", ":material/fact_check:"), ("pages/5_Assistant.py", "Ask Reco", ":material/chat:"),
                 ("pages/messages.py", "Message team", ":material/forum:"), ("pages/progress.py", "My progress", ":material/monitoring:")]
        for page, label, icon in links:
            st.page_link(page, label=label, icon=icon)
        care = data.care_phone(p)
        if care:
            ui.call_button(f"Call care team · {care}", "tel:" + ui._digits(care), "rail_call_care")


def achievements(p: dict) -> None:
    badges = _badges(p)
    tiles = "".join(f'<div class="badge{" on" if on else ""}" title="{escape(how)}"><i>{"★" if on else "☆"}</i><span>{escape(label)}</span></div>'
                    for label, on, how in badges)
    with st.container(key="rail_badges"):
        st.html(f'<p class="rail-title">Achievements</p><div class="badges">{tiles}</div>')


def day_panel(p: dict) -> None:
    """The Calendar's selected day, on the right: doses to tick, visits and refills."""
    day = st.session_state.get("calendar_day") or data.now_local().date()
    plan = p.get("plan", {})
    with st.container(key=f"rail_day_{day.isoformat()}"):
        st.html(f'<p class="rail-title">{day.strftime("%A")}</p><p class="rail-day">{day.strftime("%B")} {day.day}</p>')
        future = day > data.now_local().date()
        any_event = False
        for med in plan.get("medications", []):
            for clock in [t for t in med.get("times", []) if len(t) == 5 and t[2] == ":"]:   # "as needed" is not a dose time
                any_event = True
                label = f"{med['name']} {clock}"
                saved = p.get("med_log", {}).get(day.isoformat(), {}).get(label, False)
                taken = st.checkbox(f"{data.clock_12(clock)} · {med['name']}", value=saved, disabled=future, key=f"dose_{day}_{label}")
                if taken != saved:
                    data.log_dose(day.isoformat(), label, taken)
                    st.rerun()
        for start, title, detail in schedule(plan, day, 1):
            if type(start) is date:
                any_event = True
                st.html(f'<div class="rail-event"><b>{escape(title)}</b>{"<br>" + escape(detail) if detail else ""}</div>')
        if not any_event:
            st.html('<p class="rail-empty">Nothing scheduled this day.</p>')
        if future:
            st.caption("Doses can be marked from the day they're due.")


def render(p: dict, page: str) -> None:
    with st.container(key="rail"):
        if page == "Calendar":
            day_panel(p)
            return
        profile_card(p)
        reminders(p)
        quick_links(p)
        achievements(p)
