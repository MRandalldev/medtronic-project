# Recovery Companion

A Python and Streamlit workspace for the HackNCAT Medtronic challenge. Use fictional patients and discharge papers. The demo starts with Marcus Reed. Signing up creates an empty profile.

## Open in VS Code on Windows

Open the existing medtronic-project folder with File → Open Folder. Use Terminal → New Terminal (PowerShell). From a fresh clone, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Select Python: Select Interpreter in the command palette and choose the .venv interpreter. Use the same interpreter on every command. Open http://localhost:8501. If the team already has the repository, use Source Control → Fetch and check out feature/recovery-workspace.

## Accounts

Choose Sign up, enter a fictional email and a password of at least ten characters, then select Send verification code. With the default local configuration, the app shows the filename in .local/dev-mail containing the code. Open that file in VS Code. Returning users sign in with their password and another code. Codes expire after ten minutes. A new Streamlit session requires another local sign-in.

For delivery to an inbox, set RECOVERY_SMTP_HOST, RECOVERY_SMTP_USER, RECOVERY_SMTP_PASSWORD and RECOVERY_MAIL_FROM in the server environment and restart Streamlit. The SMTP provider must support implicit TLS, default port 465 (override with RECOVERY_SMTP_PORT). Keep demo mailbox mode on the development machine. The local SQLite databases under .local hold authentication and fictional profile data. A persistent disk is needed for hosted accounts.

Alternatively configure a hosted OpenID Connect identity provider. Register a regular web app, allow the exact callback http://localhost:8501/oauth2callback, copy .streamlit/secrets.example.toml to .streamlit/secrets.toml and fill in the registered client, issuer discovery URL and random cookie secret. Enable password registration and the desired verification policy with the provider. Restart Streamlit. In this mode the provider handles sign-in. [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)

## Run the personal assistant

- **Source lookup** works immediately. Save a preference, enter your doctor and hospital or upload a fictional UTF-8 text document. Ask a specific question, such as “Who is my doctor?” or “When is my follow-up appointment?”.
- **Ollama** runs on the same computer as the Python server. Install it on each development host and run the commands below. The app calls its loopback chat API. RECOVERY_MODEL overrides the default model tag. [Ollama on Windows](https://docs.ollama.com/windows)
- **WebLLM** runs the passage selection in a compatible browser. Select WebLLM, submit a question and click the download button. First use needs internet and WebGPU. The included bundle runs without installing Node. To rebuild after editing browser/src.js, run npm ci --prefix browser and npm run build --prefix browser. Model weights download on demand. [WebLLM](https://webllm.mlc.ai/)

```powershell
winget install -e --id Ollama.Ollama
ollama pull qwen2.5:0.5b
ollama list
```

Python retrieves up to four matching passages from the current profile, documents, saved follow-ups and the public library. The selected engine picks a passage ID. Python displays the matching text and its source. Every verified account has separate SQLite-backed context, preferences and chat history. Demo data lasts for one browser session. Saving a preference changes future lookups immediately. Model weights are shared. The browser option still uses the Python server for sign-in, storage and retrieval.

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
