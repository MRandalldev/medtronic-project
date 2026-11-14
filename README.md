# Recovery Companion

A Python and Streamlit workspace for the HackNCAT Medtronic challenge. Use fictional patients and discharge papers. The demo starts with Marcus Reed. Signing up creates a separate profile with your chosen name.

## Open in VS Code on Windows

Open the existing medtronic-project folder with File → Open Folder. Use Terminal → New Terminal (PowerShell). From a fresh clone, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Select Python: Select Interpreter in the command palette and choose the .venv interpreter. Use the same interpreter on every command. Open http://localhost:8501. If the team already has the repository, use Source Control → Fetch and check out feature/recovery-workspace.

## Deploy the full app on Vercel

Use the repository root (`./`) and deploy the commit containing `vercel.json` and `api/index.py`. The config routes the website and Streamlit WebSocket to the same Python ASGI application. Use the Other framework preset, clear old build/output overrides and enable Fluid Compute. The browser/component directory is an iframe used inside chat. Pointing the website there shows “Preparing Reco…” by itself.

The fictional demo runs without account credentials. For hosted local-email accounts, set DATABASE_URL to a shared PostgreSQL connection string and configure the SMTP settings below. Sessions may reconnect when a Vercel function expires. For a local deployment smoke test, run the project interpreter with `-m uvicorn api.index:app`, then open the printed address and enter the demo. [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python) · [WebSocket support](https://vercel.com/kb/guide/do-vercel-serverless-functions-support-websocket-connections)

## Accounts

Choose Sign up, enter an email, enter and confirm a password, add your name, then select Create account. New passwords need at least six characters, a number and a special character. The meter updates as you type. With the default local configuration, the app shows the filename in .local/dev-mail containing the code. Open that file in VS Code. Returning users sign in with their password and another code. Codes expire after ten minutes. A new Streamlit session requires another local sign-in.

For delivery to an inbox, set RECOVERY_SMTP_HOST, RECOVERY_SMTP_USER, RECOVERY_SMTP_PASSWORD and RECOVERY_MAIL_FROM in the server environment and restart Streamlit. The SMTP provider must support implicit TLS, default port 465 (override with RECOVERY_SMTP_PORT). Keep demo mailbox mode on the development machine. The local SQLite databases under .local hold authentication and fictional profile data. A persistent disk is needed for hosted accounts.

Alternatively configure a hosted OpenID Connect identity provider. Register a regular web app, allow the exact callback http://localhost:8501/oauth2callback, copy .streamlit/secrets.example.toml to .streamlit/secrets.toml and fill in the registered client, issuer discovery URL and random cookie secret. Enable password registration and the desired verification policy with the provider. Restart Streamlit. In this mode the provider handles sign-in. [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)

## Run the personal assistant

Open **Ask Reco** in the lower right corner of any page. Before sign-in, Reco can explain the app using public guidance. In the patient workspace, retrieval includes the current profile, schedule, documents and the reference library. A local model selects and orders relevant facts into a single cited answer. Urgent phrases trigger fixed guidance first.

Ollama is the first model on the Python host. If unavailable, WebLLM runs on compatible browsers and downloads model files on first use. If both are unavailable, Reco can show the saved source. A patient can also request that source immediately during the download. To rebuild the browser bundle use npm ci --prefix browser and npm run build --prefix browser. RECOVERY_MODEL overrides the default Ollama model. [Ollama](https://docs.ollama.com/windows) · [WebLLM](https://webllm.mlc.ai/)

```powershell
winget install -e --id Ollama.Ollama
ollama pull qwen2.5:0.5b
ollama list
```

## Calendar and Apple Health

Calendar shows the plan for the selected day. Export 1, 7 or 30 days of doses, visits and refills to an ICS file. Medication times use local wall time. Apple Calendar and Google Calendar can import the file. An optional display alarm is included on timed doses. To create Apple Reminders tasks, use the separate downloadable Script Editor import on a Mac with iCloud Reminders enabled. Verify device alerts and remove outdated entries after a plan change.

Health connections imports a fictional Apple Health XML or ZIP snapshot, retaining only the latest 100 heart-rate readings. Remove the snapshot from the same page. Live HealthKit authorization requires a native Apple app.

## Hospitals, clinicians and education

1. On Find my care team, search CMS by city or hospital name and save a facility. The app reads the latest Hospital General Information CSV from the CMS catalog and keeps the six-character facility ID. [Hospital data](https://data.cms.gov/provider-data/dataset/xubh-q36u)
2. List clinicians at the saved hospital. The app filters the CMS facility-affiliation dataset by that ID and displays up to 50 matching names and NPIs. An exact surname narrows results. Coverage follows the published CMS dataset. [Affiliations](https://data.cms.gov/provider-data/dataset/27ea-46a8)
3. The separate NPI Registry lookup searches individual clinicians by surname and state. Saving a clinician adds their name to the profile. These public directories supply identifiers. Clinical records and messages would require a distinct authorized hospital integration. [NPI Registry API](https://npiregistry.cms.hhs.gov/api-page)
4. For recovery education, Jaiden can use PubMed or Google Scholar to discover research, read the original publication, and have the team review its applicability. Add a short attributed summary, topic tags and its direct URL to sources/recovery.json. The initial three educational passages summarize one MedlinePlus bypass-discharge page. Directory records supply identity information only. [MedlinePlus](https://medlineplus.gov/ency/patientinstructions/000102.htm) · [PubMed search](https://pubmed.ncbi.nlm.nih.gov/help/)

## Team handoff

- Mekhai owns backend.py, data.py and assistant retrieval. Next implement extraction into an editable draft with source references before saving medications and follow-ups.
- Jaiden owns source review and sourced check-in rules. Current thresholds are demo placeholders. Jaiden and Jayden own integration and deployment.
- Jayden owns app.py and pages. Next connect reviewed medication and visit data to the Today page.
- Alicia owns design and the demo story. Test the sign-up → profile → upload → question → daily check-in journey with a fictional patient.

The care-team view and wearable readings are simulated. Caregiver sharing, live EHR connections, timed notifications and real escalation delivery are future work.
