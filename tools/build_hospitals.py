"""
Build sources/hospitals.json from the CMS Hospital General Information dataset.

Run once from the project folder (needs internet):   python tools/build_hospitals.py
Then commit sources/hospitals.json. The app then finds hospitals instantly, with no live download.
Source: https://data.cms.gov/provider-data/dataset/xubh-q36u
"""
import csv
import io
import json
from pathlib import Path

import requests

CMS = "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/xubh-q36u"
OUT = Path(__file__).resolve().parents[1] / "sources" / "hospitals.json"

meta = requests.get(CMS, timeout=30)
meta.raise_for_status()
url = next(d["downloadURL"] for d in meta.json()["distribution"] if d.get("mediaType") == "text/csv")
response = requests.get(url, timeout=60)
response.raise_for_status()
rows = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
hospitals = sorted({(r["Facility Name"].strip().title(), r["City/Town"].strip().title(), r["State"].strip(), r["Facility ID"].strip())
                    for r in rows if r.get("Facility Name") and r.get("State")}, key=lambda h: (h[2], h[0]))
OUT.write_text(json.dumps(hospitals, separators=(",", ":")), encoding="utf-8")
print(f"Wrote {len(hospitals)} hospitals to {OUT}")
