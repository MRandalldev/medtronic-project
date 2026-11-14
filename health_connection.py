"""Account-scoped, revocable write access for the Apple Health shortcut."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
import secrets

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from data import PROFILE_DB
from storage import open_database


def database():
    conn = open_database(PROFILE_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS health_grants (
        owner TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL, samples TEXT NOT NULL)""")
    conn.commit()
    return conn


def connect(owner):
    token = secrets.token_urlsafe(32)
    with closing(database()) as db, db:
        db.execute("""INSERT INTO health_grants VALUES (?, ?, '[]')
                   ON CONFLICT(owner) DO UPDATE SET digest=excluded.digest""",
                   (owner, sha256(token.encode()).hexdigest()))
    return token


def disconnect(owner):
    with closing(database()) as db, db:
        db.execute("DELETE FROM health_grants WHERE owner=?", (owner,))


def samples(owner):
    if not owner:
        return None
    with closing(database()) as db:
        row = db.execute("SELECT samples FROM health_grants WHERE owner=?", (owner,)).fetchone()
    return json.loads(row[0]) if row else None


def accept_sample(token, payload):
    try:
        stamp = datetime.fromisoformat(payload["time"])
        if not stamp.tzinfo or isinstance(payload["heart_rate"], bool):
            raise ValueError
        rate = float(payload["heart_rate"])
        if not isfinite(rate) or rate <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError):
        return 400, "Use an ISO 8601 sample time with time zone and a positive heart rate in bpm."
    digest = sha256(token.encode()).hexdigest()
    with closing(database()) as db, db:
        # Updating the same row locks concurrent submissions and serializes revocation.
        matched = db.execute("UPDATE health_grants SET digest=digest WHERE digest=?", (digest,))
        if not matched.rowcount:
            return 401, "Connection expired or disconnected."
        old = db.execute("SELECT samples FROM health_grants WHERE digest=?", (digest,)).fetchone()
        latest = {r["time"]: r for r in json.loads(old[0])}
        key = stamp.astimezone(timezone.utc).isoformat(timespec="microseconds")
        latest[key] = {"time": key, "heart_rate": rate}
        rows = [latest[k] for k in sorted(latest)[-100:]]
        db.execute("UPDATE health_grants SET samples=? WHERE digest=?", (json.dumps(rows), digest))
    return 200, "Reading received."


async def receive(request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or len(auth) != 50:
        return JSONResponse({"message": "A connection key is required."}, status_code=401)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 2048:
            return JSONResponse({"message": "Send one reading at a time."}, status_code=413)
        raw.extend(chunk)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        return JSONResponse({"message": "Expected a JSON object."}, status_code=400)
    code, message = await run_in_threadpool(accept_sample, auth[7:], payload)
    return JSONResponse({"message": message}, status_code=code)
