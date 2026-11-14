from datetime import date, datetime

import streamlit as st

import data
from watch_reminders import reminders_script
from month_view import month_view
from schedule_export import calendar_file, schedule

st.title("Recovery calendar")
meds = None
p = data.get_patient()
plan = p.get("plan", {})
day = month_view(plan)
st.caption("Pick a day. Its doses, visits and refills open on the right.")
with st.expander("Take your schedule with you: reminders on your phone or Apple Watch"):
    days = st.selectbox("Export starting on the selected day", [1, 7, 30], index=1,
                        format_func=lambda n: f"{n} day" if n == 1 else f"{n} days")
    remind = st.checkbox("Add a daily check-in reminder", True)
    check_time = data.settings(p)["checkin_time"]
    alerts = st.checkbox("Include alerts for medicines, check-ins, visits and refills", True)
    entries = list(schedule(plan, day, days, check_time if remind else None))
    st.caption(f"Medicines and the check-in ({data.clock_12(check_time)}, change it in Settings) alert at their time. "
               "Visits alert at 9:00 AM that day. Refills alert three days before and on the day.")
    st.download_button("Download for Apple or Google Calendar", calendar_file(entries, st.session_state.get("owner", "demo"), alerts),
                       f"reco-{day}.ics", "text/calendar", disabled=not entries)
    st.caption("Times use local clock time. Review the imported schedule when your plan changes.")
    if True:  # how to import
        st.markdown("**How to import and get Apple Watch alerts**")
        st.write("Apple Calendar on Mac · Open the downloaded file and choose an iCloud calendar synced to your iPhone.")
        st.write("Google Calendar on a computer · Open Settings → Import & export → Import. Select the file and destination calendar.")
        st.write("Apple Watch · On your iPhone, open Watch → My Watch → Calendar and enable notifications for that calendar. Check the alert on an imported event.")
        st.markdown("[Apple Watch calendar settings](https://support.apple.com/guide/watch/apd1b51754cc/watchos) · [Google Calendar import](https://support.google.com/calendar/answer/37118)")

    if True:  # Apple Reminders
        st.markdown("**Add medication tasks to Apple Reminders**")
        st.write("On a Mac using iCloud Reminders, download this script, open it in Script Editor, review it and press Run. Allow access to Reminders. The Reco list syncs to your Apple Watch through iCloud.")
        st.caption("Creates timed tasks for doses in the selected date range. Choose Calendar alerts or Reminders to avoid duplicate notifications.")
        st.download_button("Download Reminders import for Mac", reminders_script(entries, st.session_state.get("owner", "demo")),
                           "Reco Reminders.applescript", "text/plain", disabled=not any(isinstance(row[0], datetime) for row in entries))
