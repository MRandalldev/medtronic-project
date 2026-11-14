# Recovery Companion (HackNCAT 10.0, Medtronic challenge)

Turns heart surgery discharge papers into daily guidance, check-ins and early warnings.

## Run it
    python -m venv .venv
    source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

Put the API key in `.streamlit/secrets.toml` (never commit it):
    ANTHROPIC_API_KEY = "sk-ant-..."

## Who edits what
- `app.py`, `pages/`, `ui.py`: screens (Jaiden / Jayden), design from Alicia
- `.streamlit/config.toml`: Alicia's colors and font
- `backend.py`, `data.py`: Mekhai. Keep function names and return shapes; run `python check.py` after changes
- `sources/thresholds.csv`, `sources/*.txt`: Jaiden. Every rule needs a source link

## Rules
Pull before you push. Only edit your own files. Nothing goes to main unless it runs locally.
