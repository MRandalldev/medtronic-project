# Recovery Companion: architecture

How the app works behind the screens. Every item is marked **[verified]** (read in the code and, where noted,
exercised by `check.py` or a browser test) or **[inferred]** (reasoned from the code but not run end to end).
No secrets appear in this document.

## 1. Big picture

```
Browser ──HTTP/WebSocket──▶ Streamlit app (app.py + pages/*.py)          [verified]
   │                            │
   │                            ├─ data.py ──────── patient record (session; SQLite or Postgres for accounts)
   │                            ├─ backend.py ───── check-in rules, care-team summary, Claude client
   │                            ├─ grounding.py ─── Reco: rules → knowledge base → retrieval → model
   │                            ├─ account_access.py  email + password + emailed code
   │                            ├─ provider_directory.py  CMS + NPI public APIs
   │                            └─ schedule_export.py  .ics calendar file
   │
   ├─ WebLLM (browser/component) ─ small model that runs on the patient's own device   [verified]
   └─ POST /health/readings ◀── iPhone Shortcut (Apple Health heart rate)                [verified in tests]
```

One Python process serves everything. Locally it is `streamlit run app.py`. On Vercel, `api/index.py` wraps the same
app in an ASGI server (`st.App`) and adds two routes. **[verified]**

## 2. Frontend

**Framework.** Streamlit 1.67 (Python). Every page is a Python script that Streamlit reruns from the top whenever the
user interacts. There is no separate React or JavaScript app. **[verified]**

**Structure.**

| Path | Role |
|---|---|
| `app.py` | Entry point: sign-in screen, demo entry, sidebar navigation (`st.navigation(position="hidden")` plus custom `st.page_link` groups), Reco launcher |
| `pages/4_Dashboard.py` | **Today**: one next step, today's doses, as-needed medicine counter, refills, next visit, caregiver update |
| `pages/3_Check_in.py` | Daily check-in questionnaire (quiz style) |
| `pages/1_Onboarding.py` | Profile questionnaire, one question per screen |
| `pages/6_Calendar.py` + `month_view.py` | Month calendar, dose ticking, calendar export |
| `pages/progress.py` | Recovery dashboard: milestones, adherence, trends |
| `pages/messages.py`, `pages/7_Care_team.py`, `pages/caregiver.py` | Two-way messages; care-team and caregiver demo views |
| `pages/2_Upload_papers.py` | Discharge papers to plan |
| `pages/watch.py`, `pages/connections.py` | Simulated watch/cuff; Apple Health shortcut pairing |
| `pages/directory.py` | Hospital and clinician lookup |
| `pages/settings.py` | Phones, reminder time, emergency countdown |
| `reco.py` | Reco chat: launcher, panel, thread, composer |
| `ui.py` | Shared pieces (call buttons, alert banner, patient card, theme loader) |
| `registration.py`, `login_screen.py` | Native sign-in form with the live password meter |

**Styling.** `ui.theme()` injects, in this order: `assets/recovery.css`, `assets/appearance.css`, `assets/design.css`,
and `assets/theme.css`. `theme.css` loads last and owns the design system: color, shadow, radius and motion tokens for
light and dark mode. Light and dark mode set `data-reco-theme` on `<html>` (`assets/appearance.js`, remembered in
`localStorage`). The same script marks the active sidebar link (`data-active`) and tags bordered containers as cards
(`data-reco-card`), because Streamlit 1.67 gives neither an attribute of its own. `.streamlit/config.toml` sets
Streamlit's own theme colors to match. **[verified]**

**State.** `st.session_state` holds the patient record (`patient`), the signed-in owner, Reco's pending request and
questionnaire drafts. Persistence is described in section 3. **[verified]**

**Questionnaires.**
- *Check-in.* The questionnaire has 13 sourced yes/no questions (tiles), two "compared to yesterday" questions (tile
  rows), a pain tap 0–10, minutes walked, and optional pulse, temperature, weight and blood pressure. Submitting saves
  the numbers as a reading, scores answers plus readings with `backend.score_checkin`, saves the check-in, and shows a
  red, yellow or green result first. The visual quiz styling is CSS only; widget keys and scoring did not change.
  **[verified by check.py]**
- *Profile.* The profile questionnaire has eight one-question screens. Each Continue copies that screen's answers into
  `profile_draft` (Streamlit drops the state of widgets that leave the screen). Back returns to the previous screen
  with answers kept. The last screen writes the whole profile in one `data.save_patient` call. **[verified by check.py]**

**Reco on the frontend.** A fixed button sits in the bottom-right corner (`.st-key-reco_dock`). Clicking it opens a
Streamlit dialog that the theme restyles as a chat panel anchored to the same corner. The panel grows out of the
corner with `clip-path`, `scale` and `opacity` over 420 ms on an iOS-like curve, and only fades for reduced-motion
users. The thread is a fixed-height container with `autoscroll=True`, so it scrolls on its own and follows new
messages. It shows the last 40 turns. The composer stays pinned below. A typing indicator shows while the in-browser
model is working. **[verified in Chrome, desktop and 390 px phone]** Limit: Streamlit removes the dialog instantly on
close, so there is no closing animation.

## 3. Backend

**Patient record.** One JSON object per patient (shape documented at the top of `data.py`): profile, plan
(medications, follow-ups, warning signs), vitals, check-ins, medication log, as-needed log, alerts (with
acknowledgement), messages (with read state), documents and Reco history. **[verified]**
- *Demo and guest:* kept in the session only, seeded from `data/sample_patient.json`.
- *Signed-in accounts:* saved as JSON in a `profiles` table with an optimistic `revision` check, so two tabs cannot
  overwrite each other. **[verified]**
- *Database:* `storage.open_database` uses Postgres when `DATABASE_URL` is set. Otherwise it uses SQLite files in
  `.local/` (`accounts.sqlite`, `login.sqlite`). On Vercel, SQLite is refused, because instances don't share a disk.
  **[verified]**

**Authentication.**
- *Email accounts* (`account_access.py`): sign-up needs a password that passes `password_policy.py` (NIST SP 800-63B-4:
  at least 8 characters, a blocklist, no composition rules). Passwords are hashed with scrypt. Every sign-in also
  needs a six-digit code by email, so it has two factors. Attempts are rate-limited. Without SMTP settings, the code is
  written to a local file for development. **[verified]**
- *OIDC:* when `[auth]` is set in Streamlit secrets, `st.login()` is offered. **[inferred: no provider configured in this repo]**
- *Authorization:* each account's record is keyed by a hash of (issuer, subject). The care-team and caregiver views are
  demo views inside the same session, with no clinician accounts. **[verified]**

**Business logic.**
- *Warning rules:* `sources/thresholds.csv` holds 20 rules, each with its source link. `backend.score_checkin` and
  `chat_rules.check` apply the same rules to check-in answers, typed numbers, device readings and chat. AI never
  decides urgency. **[verified]**
- *Medicines:* scheduled doses, adherence, overdue doses, refill reminders and as-needed limits read from the
  patient's own papers live in `data.py`. **[verified]**
- *Plan from papers:* `plan_reader.py` extracts medicines, visits and warning signs with patterns, plus Claude when a
  key is set. **[verified for the demo papers]**

## 4. APIs and integrations

| Integration | Where | Sends | Receives | Status |
|---|---|---|---|---|
| **Anthropic Claude** (`claude-sonnet-5-5`) | `backend.call_ai`, used by `grounding.claude_select` and the paper reader | System prompt, question, the retrieved passages and recent turns | JSON: reply plus the IDs of the passages used | Only when `ANTHROPIC_API_KEY` is set **[verified code path; not called in tests]** |
| **Ollama** (local) | `grounding.select` → `POST http://127.0.0.1:11434/api/chat` | Same prompt, JSON schema | Same JSON | Local machine only; skipped on Vercel **[verified code]** |
| **WebLLM** (in the browser) | `browser_engine.py` + `browser/component` (served at `/reco-engine`) | Same prompt | Same JSON | Downloads Qwen2.5-0.5B to the device; warmed in the background **[verified earlier in Chrome]** |
| **CMS Provider Data** | `provider_directory.hospitals / affiliations` → `https://data.cms.gov/provider-data` | Dataset query | Hospitals; clinician affiliations | Public, no key **[verified earlier; blocked in this sandbox]** |
| **NPI Registry** | `provider_directory.doctors` → `https://npiregistry.cms.hhs.gov/api/` | Surname and state | Clinicians | Public, no key **[verified earlier]** |
| **SMTP** | `account_access.deliver` | Verification code | — | When `RECOVERY_SMTP_*` are set **[inferred: not run with a real server]** |
| **Apple Health (iPhone Shortcut)** | `POST /health/readings` (`health_connection.receive`) | `Authorization: Bearer <pairing key>`, JSON `{time, heart_rate}`, max 2 KB | 200, 400, 401 or 413 with a message | **[verified by tests; not on a physical iPhone]** |
| **Calendar export** | `schedule_export.py` | — | `.ics` with alerts for doses, check-ins, visits and refills | **[verified by check.py; not imported on a real phone]** |

**How Reco answers** (`grounding.immediate_reply`, then `reco.chat`), first match wins:
1. Crisis wording: 988 guidance.
2. Urgent symptoms: fixed emergency steps and call buttons (never model text).
3. The 20 sourced rules, using the same code as the check-in.
4. Questions about the patient's own record: next visit, today's medicines, when to call.
5. A knowledge base of 54 sourced topics (`reco_kb.py`, TF-IDF matching with a confidence threshold).
6. Otherwise, retrieval over the patient's papers and record plus approved references, then a model picks passages
   and writes the conversational part: Claude if a key is set, else Ollama locally, else WebLLM in the browser.
   Medical facts are quoted from the passages, not generated.
7. If nothing is confident: "not sure", with tappable suggestion chips.

A red or yellow answer is saved as an alert in the record. It does not notify anyone outside the app. **[verified]**

## 5. Data flow

- **Check-in:** widgets → `pages/3_Check_in.py` → `data.record_numbers` (vitals) → `backend.score_checkin` (rules) →
  `data.add_checkin` and, when red or yellow, `data.add_alert` → `data.save_patient` (session, then the database for
  accounts). Today, the dashboard, the care-team view and the caregiver view read from the same record on their next
  run.
- **Profile:** screen answers → `profile_draft` → one `data.save_patient` on the last screen.
- **Reco:** composer → `reco.chat` → `grounding.immediate_reply` or retrieval → model (server or browser) →
  `record_turn` saves to `assistant_history` (and an alert if flagged). With the browser model, the request is stored
  as `reco_pending`. The WebLLM component returns the answer through a component trigger on the next run.
- **Background work:** none on the server. In the browser, WebLLM warms itself on an idle callback after the page
  loads. **[verified]**

## 6. Configuration

| Variable or file | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` (env or `.streamlit/secrets.toml`) | Enables Claude for Reco and paper reading |
| `RECOVERY_MODEL` | Ollama model name (default `qwen2.5:0.5b`) |
| `DATABASE_URL` | Postgres for accounts. Required on Vercel for sign-up and sign-in. |
| `RECOVERY_SMTP_HOST`, `RECOVERY_SMTP_PORT` (default 465), `RECOVERY_SMTP_USER`, `RECOVERY_SMTP_PASSWORD`, `RECOVERY_MAIL_FROM` | Verification email |
| `VERCEL` | Set by Vercel; switches off Ollama and the SQLite fallback |
| `[auth]` in secrets | Optional OIDC sign-in |
| `.streamlit/config.toml` | Streamlit theme colors |
| `vercel.json`, `api/index.py` | Deployment: all paths go to the ASGI app; `/health/readings` and `/reco-engine` are added |
| `requirements.txt` | streamlit, anthropic, pandas, requests, Authlib, icalendar, defusedxml, psycopg |

## 7. Risks and bottlenecks

**Security**
- The care-team and caregiver views are not access-controlled clinician tools. They are demo views of the same
  session. Don't present them as secure clinical messaging, and this is not HIPAA-grade.
- Profiles are stored as plain JSON in the database (no encryption at the application layer). **[verified]**
- The Apple Health pairing key is shown once and stored only as a SHA-256 hash. Revoking it deletes the readings.
  **[verified]**
- Calls to CMS and NPI are restricted to their HTTPS hosts. **[verified]**

**Performance**
- Every interaction reruns the page script. Large pages (the calendar, the dashboard) are the slowest. **[inferred]**
- The first WebLLM download on a new device takes about a minute. Rules, the knowledge base and record answers work
  during the download. **[verified earlier on the live site]**
- On Vercel, every request is a serverless invocation with a 300 s limit. The Streamlit WebSocket depends on the
  platform keeping a connection open. **[inferred]**

## 8. What testing covers

`python check.py` covers the rules file, the backend contract, Reco's crisis and red paths, the knowledge base,
dates, the password policy, the sponsor checklist (check-in numbers, reminders, two-way care team, dashboard, caregiver
update), the profile questionnaire, and a click-through of every page with two profiles. Browser checks
(Playwright/Chrome, not in the repo) covered layout, contrast in light and dark mode, the phone layout, Reco's panel
position, thread scrolling and the open animation.
