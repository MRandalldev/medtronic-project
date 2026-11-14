from datetime import date, datetime, time, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from icalendar import Alarm, Calendar, Event


def schedule(plan, start, days):
    """Yield events in the patient's local wall time, preserving date-only visits."""
    end = start + timedelta(days=days)
    for offset in range(days):
        day = start + timedelta(days=offset)
        for med in plan.get("medications", []):
            for value in med.get("times", []):
                try:
                    clock = time.fromisoformat(value)
                except (TypeError, ValueError):
                    continue
                yield datetime.combine(day, clock), med["name"], med.get("dose", "")
    for visit in plan.get("follow_ups", []):
        try:
            day = date.fromisoformat(visit["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if start <= day < end:
            yield day, "Visit with " + visit["with"], visit.get("purpose", "")
    for med in plan.get("medications", []):
        try:
            day = date.fromisoformat(med.get("refill_date", ""))
        except (TypeError, ValueError):
            continue
        if start <= day < end:
            yield day, "Refill · " + med["name"], ""


def calendar_file(entries, owner, alerts):
    calendar = Calendar()
    calendar.add("prodid", "-//Reco//Recovery calendar//EN")
    calendar.add("version", "2.0")
    now = datetime.now(timezone.utc)
    for start, title, detail in dict.fromkeys(entries):
        event = Event()
        uid = uuid5(NAMESPACE_URL, repr((owner, start.isoformat(), title, detail)))
        event.add("uid", f"{uid}@reco.local")
        event.add("dtstamp", now)
        event.add("dtstart", start)
        if not isinstance(start, datetime):
            event.add("dtend", start + timedelta(days=1))
        event.add("summary", title)
        event.add("description", detail)
        if alerts and isinstance(start, datetime):
            alert = Alarm()
            alert.add("action", "DISPLAY")
            alert.add("trigger", timedelta(0))
            alert.add("description", title)
            event.add_component(alert)
        calendar.add_component(event)
    return calendar.to_ical()
