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
    reason_text = "; ".join(_short(r["message"]) for r in reasons)
    with st.container(key=f"result_{level}_{key}", border=True):
        if level == "red":
            st.markdown("### Let’s get you help now")
            st.write("You did the right thing by checking in. Based on what you told us — "
                     f"**{reason_text.lower()}** — your discharge guidance says to call 911.")
            if data.settings(patient).get("countdown"):
                countdown(data={"id": f"{key}-{len(patient.get('alerts', []))}", "seconds": 10, "demo": demo_safe()},
                          key=f"countdown_{key}", height=56)
            call_actions(patient, f"red_{key}", reason_text, emergency=True)
            st.caption("While you wait: " + backend.EMERGENCY_STEPS[2])
        elif level == "yellow":
            st.markdown("### Call your care team today")
            st.write(f"You mentioned **{reason_text.lower()}**. It’s not an emergency, but your discharge guidance "
                     "says your team should hear about it today. Calling early gives them time to help.")
            call_actions(patient, f"yellow_{key}", reason_text, emergency=False)
        else:
            streak = check_in_streak(patient)
            st.markdown("### All clear today")
            nxt = data.next_dose(patient)
            st.write("Nothing in your check-in matched a warning sign. "
                     + (f"You’re on a **{streak}-day check-in streak**. " if streak > 1 else "")
                     + (f"Next dose: **{nxt[1]} at {nxt[0]}**." if nxt else ""))
        if reasons:
            with st.expander("Why am I seeing this?"):
                for r in reasons:
                    st.markdown(f"- {r['message']}  \n  Source: [{r['source'].split('/')[2] if r['source'].startswith('http') else r['source']}]({r['source']})")
        if level in ("red", "yellow"):
            st.caption("Saved to your recovery record and shown in the care team view."
                       + (" Demo: no call or text is sent." if demo_safe() else ""))


def demo_badge() -> None:
    st.caption("Fictional recovery workspace")

ASSETS = Path(__file__).parent / "assets"


@st.cache_data
def artwork(filename):
    mime = "png" if filename.endswith(".png") else "jpeg"
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
            styles.replace("EARTH_ART", artwork("earthrise.jpg")) + design + "</style>")


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
        pills.append(f'<span class="pill info">Next: {escape(nxt[1].split(" ")[0])} {escape(nxt[0])}</span>')
    st.html(f'''<div class="reco-patient"><div class="avatar">{escape(initials)}</div>
      <div class="name">{escape(name)}</div><div class="day">{f"Day {day} after surgery" if day is not None else "Add your surgery date"}</div>
      <div class="status">{"".join(pills)}</div></div>''')
