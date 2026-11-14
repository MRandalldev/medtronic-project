import csv
import io
import requests
import streamlit as st
from urllib.parse import urlsplit

CMS = "https://data.cms.gov/provider-data"
NPI = "https://npiregistry.cms.hhs.gov/api/"

@st.cache_data(ttl=86400, show_spinner=False)
def hospitals():
    meta = requests.get(CMS + "/api/1/metastore/schemas/dataset/items/xubh-q36u", timeout=15)
    meta.raise_for_status()
    url = next(d["downloadURL"] for d in meta.json()["distribution"] if d.get("mediaType") == "text/csv")
    if urlsplit(url).hostname != "data.cms.gov" or urlsplit(url).scheme != "https":
        raise ValueError("Unrecognized hospital dataset host")
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
    return [(r["Facility Name"], r["City/Town"], r["State"], r["Facility ID"]) for r in rows]

def doctors(last, state):
    response = requests.get(NPI, params={"version":"2.1","enumeration_type":"NPI-1","last_name":last,"state":state,"limit":20}, timeout=12)
    response.raise_for_status()
    payload = response.json()
    if "Errors" in payload:
        raise ValueError("Registry could not process this search")
    return [(r["basic"]["first_name"] + " " + r["basic"]["last_name"], r["number"],
             next((t["desc"] for t in r["taxonomies"] if t["primary"]), "")) for r in payload.get("results", [])]


@st.cache_data(ttl=86400, show_spinner=False)
def affiliations(facility_id, surname=""):
    """Return the first 50 CMS-listed clinicians at a selected hospital."""
    field = "facility_affiliations_certification_number"
    params = {"limit": 50, "conditions[0][property]": field,
              "conditions[0][operator]": "=", "conditions[0][value]": facility_id}
    if surname:
        params.update({"conditions[1][property]": "provider_last_name",
                       "conditions[1][operator]": "=", "conditions[1][value]": surname.strip().upper()})
    response = requests.get(CMS + "/api/1/datastore/query/27ea-46a8/0", params=params, timeout=20)
    response.raise_for_status()
    return [(f"{r['provider_first_name']} {r['provider_last_name']}", r["npi"])
            for r in response.json()["results"] if r[field] == facility_id]
