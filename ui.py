"""
ui.py — shared look-and-feel pieces. (Owner: Jaiden/Jayden, design by Alicia)

Alicia's colors and font go in .streamlit/config.toml. Reusable pieces that
appear on several pages live here, so a design change happens in one place.
"""
from base64 import b64encode
from pathlib import Path

import streamlit as st

import backend
import data
from html import escape
from urllib.parse import quote

def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def _digits(number: str) -> str:
    return "".join(ch for ch in number if ch.isdigit() or ch == "+")


def _short(message: str) -> str:
    """'Chest pain or angina symptoms: call 911.' -> 'Chest pain or angina symptoms'"""
    return message.split(":")[0].strip().rstrip(".")


def _topic(message: str) -> str:
    """Like _short, with only the first letter lowered, so units such as °F keep their capitals mid-sentence."""
    text = _short(message)
    return text[:1].lower() + text[1:]


def demo_safe() -> bool:
    """In the demo (and before sign-in) call buttons never dial, so nobody calls 911 by accident while presenting."""
    return bool(st.session_state.get("demo")) or not (st.session_state.get("owner") or st.session_state.get("local_identity"))


def call_button(label: str, href: str, key: str, primary: bool = False, demo_note: str = "") -> None:
    """A one-tap call or text link. In demo mode it explains what would happen instead of dialing."""
    if demo_safe():
        st.button(label, key=key, type="primary" if primary else "secondary", width="stretch",
                  on_click=st.toast, args=(demo_note or ("Demo: on a phone this opens Messages with the text filled in. Nothing is sent."
                                       if href.startswith("sms:") else "Demo: on a phone this opens the dialer. Nothing is sent."),))
    else:
        css = "reco-call primary" if primary else "reco-call"
        st.html(f'<a class="{css}" href="{escape(href, quote=True)}">{escape(label)}</a>')


def call_actions(patient: dict, key: str, reason: str = "", emergency: bool = True) -> None:
    """Numbered one-tap actions: 911, the care team, then the caregiver."""
    care = data.care_phone(patient)
    caregiver = patient.get("caregiver", "").split("(")[0].strip()
    caregiver_phone = data.settings(patient).get("caregiver_phone", "")
    first = caregiver.split()[0] if caregiver else "your caregiver"
    if emergency:
        call_button("1  Call 911", "tel:911", f"{key}_911", primary=True,
                    demo_note="Demo: on a phone this opens the dialer with 911. Your phone asks you to confirm.")
    if care:
        call_button(f"{'2  ' if emergency else ''}Call your care team · {care}", "tel:" + _digits(care), f"{key}_care",
                    primary=not emergency)
    if caregiver_phone:
        text = f"I {'called 911' if emergency else 'need to call my care team'} after my heart surgery. {reason}".strip()
        call_button(f"{'3  ' if emergency else ''}Text {first}", f"sms:{_digits(caregiver_phone)}?&body={quote(text)}", f"{key}_sms")


countdown = st.components.v2.component(
    "emergency_countdown", html='<div class="cd"></div>',
    css=".cd{font:600 1rem system-ui;padding:.7rem 1rem;border-radius:.8rem;background:#fff3f0;color:#7a1f12;display:flex;gap:1rem;align-items:center;justify-content:space-between}.cd button{font:inherit;border:1px solid #7a1f12;background:transparent;color:inherit;border-radius:.6rem;padding:.3rem .8rem;cursor:pointer}",
    js="""export default function ({data, parentElement}) {
  const root = parentElement.querySelector('.cd');
  if (root.dataset.alert === data.id) return;
  root.dataset.alert = data.id;
  let left = data.seconds, timer;
  const text = document.createElement('span');
  const cancel = document.createElement('button');
  cancel.textContent = 'Cancel';
  cancel.onclick = () => { clearInterval(timer); text.textContent = 'Countdown cancelled. Call 911 yourself if you need to.'; cancel.remove(); };
  root.replaceChildren(text, cancel);
  const tick = () => {
    if (left <= 0) {
      clearInterval(timer); cancel.remove();
      if (data.demo) { text.textContent = 'Demo: on a phone, the dialer would open with 911 now. You still press Call.'; }
      else { text.textContent = 'Opening your phone to call 911…'; window.location.href = 'tel:911'; }
      return;
    }
    text.textContent = 'Opening your phone to call 911 in ' + left + '…';
    left -= 1;
  };
  tick(); timer = setInterval(tick, 1000);
}""")


def check_in_streak(patient: dict) -> int:
    days = {c.get("date") for c in patient.get("checkins", [])}
    streak, day = 0, data.now_local().date()
    while day.isoformat() in days:
        streak += 1
        day = day.fromordinal(day.toordinal() - 1)
    return streak


def alert_banner(level: str, reasons: list, key: str = "checkin") -> None:
    """The result of a check-in, written for someone who may be frightened: one clear next step at a time."""
    patient = data.get_patient()
    reason_text = "; ".join(_topic(r["message"]) for r in reasons)
    with st.container(key=f"result_{level}_{key}", border=True):
        if level == "red":
            st.markdown("### Let’s get you help now")
            st.write("You did the right thing by checking in. Based on what you told us — "
                     f"**{reason_text}** — your discharge guidance says to call 911.")
            if data.settings(patient).get("countdown"):
                countdown(data={"id": f"{key}-{len(patient.get('alerts', []))}", "seconds": 10, "demo": demo_safe()},
                          key=f"countdown_{key}", height=56)
            call_actions(patient, f"red_{key}", reason_text, emergency=True)
            st.caption("While you wait: " + backend.EMERGENCY_STEPS[2])
        elif level == "yellow":
            st.markdown("### Call your care team today")
            st.write(f"Your check-in shows **{reason_text}**. It’s not an emergency, but your discharge guidance "
                     "says your team should hear about it today. Calling early gives them time to help.")
            call_actions(patient, f"yellow_{key}", reason_text, emergency=False)
        else:
            streak = check_in_streak(patient)
            st.markdown("### All clear today")
            nxt = data.next_dose(patient)
            st.write("Nothing in your check-in matched a warning sign. "
                     + (f"You’re on a **{streak}-day check-in streak**. " if streak > 1 else "")
                     + (f"Next dose: **{nxt[1]} at {data.clock_12(nxt[0])}**." if nxt else ""))
        if reasons:
            with st.expander("Why am I seeing this?"):
                for r in reasons:
                    st.markdown(f"- {r['message']}  \n  Source: [{r['source'].split('/')[2] if r['source'].startswith('http') else r['source']}]({r['source']})")
        if level in ("red", "yellow"):
            st.caption("Saved to your recovery record and shown in the care team view."
                       + (" Demo: no call or text is sent." if demo_safe() else ""))


def checkin_recap(patient: dict) -> None:
    """Today's own numbers next to the previous check-in, so the patient can see their recovery move."""
    with_numbers = [c for c in patient.get("checkins", []) if c.get("numbers")]
    if not with_numbers:
        return
    now, before = with_numbers[-1]["numbers"], (with_numbers[-2]["numbers"] if len(with_numbers) > 1 else {})
    fields = [("pain", "Pain", "{}/10", "inverse"), ("walk_min", "Walked", "{} min", "normal"), ("heart_rate", "Pulse", "{} bpm", "off"),
              ("temp_f", "Temperature", "{}°F", "off"), ("weight_lb", "Weight", "{} lb", "off")]
    shown = [f for f in fields if now.get(f[0]) is not None]
    if "bp_sys" in now and "bp_dia" in now:
        shown.append(("bp", "Blood pressure", f"{now['bp_sys']}/{now['bp_dia']}", "off"))
    with st.container(border=True, key="checkin_recap"):
        st.markdown("**What you recorded today**")
        cols = st.columns(min(len(shown), 3) or 1)
        for i, (key, label, fmt, color) in enumerate(shown):
            delta = round(now[key] - before[key], 1) if key != "bp" and before.get(key) is not None else None
            cols[i % len(cols)].metric(label, fmt.format(now[key]) if key != "bp" else fmt, delta=delta if delta else None, delta_color=color,
                                       help="The small number is the change since your last check-in." if delta else None)
        st.caption("Your care team sees these numbers and how they change. Pain and walking are tracked as trends; "
                   "pulse, temperature, weight and blood pressure are also checked against the sourced warning rules.")
    if now.get("pain"):
        prn_card(patient, "recap")


def prn_card(patient: dict, key: str) -> None:
    """As-needed medicine with a running count against the limit written in the patient's own papers."""
    for i, med in enumerate(data.prn_meds(patient)):
        status = data.prn_status(patient, med)
        with st.container(border=True, key=f"prn_{key}_{i}"):
            st.markdown(f"**{med['name']}** · as needed")
            st.caption(med["dose"] + ".")
            limit = med["max_24h"]
            if limit:
                st.progress(min(status["taken_24h"] / limit, 1.0), text=f"{status['taken_24h']} of {limit} taken in the last 24 hours")
            else:
                st.write(f"{status['taken_24h']} taken in the last 24 hours. Your papers give no daily limit; ask your care team.")
            blocked = limit is not None and status["left"] <= 0
            if blocked:
                st.warning("You have reached the limit in your papers. If your pain is not under control, call your care team.")
            elif status["next_ok"]:
                st.info(f"Your papers say every {med['gap_hours']} hours. The next dose is OK after "
                        f"{status['next_ok'].strftime('%I:%M %p').lstrip('0')}.")
            if not blocked and not status["next_ok"]:   # no buttons while a dose would break the limit or the gap
                one, two = st.columns(2)
                if one.button("I took 1", key=f"prn1_{key}_{i}", width="stretch"):
                    data.log_prn(med["name"], 1)
                    st.rerun()
                if (limit is None or status["left"] >= 2) and two.button("I took 2", key=f"prn2_{key}_{i}", width="stretch"):
                    data.log_prn(med["name"], 2)
                    st.rerun()


def thread(patient: dict, viewer: str) -> None:
    """The message thread between the patient and the care team, shown from one side ("Patient" or "Care team")."""
    messages = patient.get("messages", [])
    if not messages:
        st.caption("No messages yet.")
    first = (patient.get("name") or "Patient").split(" ")[0]
    for m in messages:
        mine = m.get("from") == viewer
        who = "You" if mine else ("Care team" if m.get("from") == "Care team" else first)
        with st.chat_message("user" if m.get("from") != "Care team" else "assistant",
                             avatar=":material/person:" if m.get("from") != "Care team" else ":material/medical_services:"):
            st.markdown(f"**{who}** · {data.human_time(m.get('time', ''))}"
                        + (" · *new*" if not mine and m.get("read") is False else ""))
            st.write(m.get("text", ""))
    with st.form(f"send_{viewer.replace(' ', '_').lower()}", clear_on_submit=True, border=False):
        text = st.text_area("Write a message", key=f"draft_{viewer}", height=80, max_chars=1000, label_visibility="collapsed",
                            placeholder="Type your message" if viewer == "Patient" else "Reply to the patient")
        if st.form_submit_button("Send message", type="primary") and text.strip():
            data.add_message(viewer, text.strip())
            st.rerun()


def next_action_card(patient: dict) -> None:
    """The single most important thing to do now, at the top of Today."""
    action = data.next_action(patient)
    with st.container(border=True, key=f"next_{action['kind']}"):
        st.html('<p class="next-label">Your next step</p>')
        st.markdown(f"### {action['title']}")
        st.write(action["body"])
        st.page_link(action["page"], label=action["link"] + " →")


def demo_badge() -> None:
    st.caption("Fictional recovery workspace")

ASSETS = Path(__file__).parent / "assets"


@st.cache_data
def artwork(filename):
    mime = "png" if filename.endswith(".png") else "svg+xml" if filename.endswith(".svg") else "jpeg"
    return f"data:image/{mime};base64," + b64encode((ASSETS / filename).read_bytes()).decode("ascii")


appearance = st.components.v2.component("appearance_switch", html='<button type="button"></button>',
    css="button{float:right;background:var(--reco-card,transparent);color:var(--reco-ink,inherit);border:1px solid var(--reco-border,#79918b);border-radius:2rem;padding:.4rem .8rem;cursor:pointer;font:600 .85rem system-ui}",
    js=(ASSETS / "appearance.js").read_text(encoding="utf8"))


def theme():
    css = (ASSETS / "recovery.css").read_text(encoding="utf8")
    styles = (ASSETS / "appearance.css").read_text(encoding="utf8")
    design = (ASSETS / "design.css").read_text(encoding="utf8")
    # Fonts load through <link> tags: an @import only works at the very top of a stylesheet, and this one
    # sits after other rules, so browsers ignored it and fell back to system fonts.
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400'
             '&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap">')
    st.html(fonts + "<style>" + css.replace("RECO_ART", artwork("reco-face.png")) +
            styles.replace("EARTH_ART", artwork("heartrise.svg")) + design + "</style>")


def patient_card(patient: dict) -> None:
    """Sidebar summary: who, which recovery day, and the one thing to do next."""
    name = patient.get("name") or "Your recovery"
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "R"
    day = data.days_since_surgery(patient)
    today = data.now_local().date().isoformat()
    checked = any(c.get("date") == today for c in patient.get("checkins", []))
    nxt = data.next_dose(patient)
    pills = ['<span class="pill ok">✓ Checked in today</span>' if checked else '<span class="pill due">● Check-in due</span>']
    if nxt:
        pills.append(f'<span class="pill info">Next: {escape(nxt[1].split(" ")[0])} {escape(data.clock_12(nxt[0]))}</span>')
    st.html(f'''<div class="reco-patient"><div class="avatar">{escape(initials)}</div>
      <div class="name">{escape(name)}</div><div class="day">{f"Day {day} after surgery" if day is not None else "Add your surgery date"}</div>
      <div class="status">{"".join(pills)}</div></div>''')
