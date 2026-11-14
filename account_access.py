"""Password and single-use verification codes for fictional hackathon profiles."""
from contextlib import closing
from email.message import EmailMessage
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import smtplib
import sqlite3
import ssl
import time

DIRECTORY = Path(__file__).parent / ".local"
MAILBOX = DIRECTORY / "dev-mail"
CODE_LIFETIME = 600


def database():
    DIRECTORY.mkdir(exist_ok=True)
    conn = sqlite3.connect(DIRECTORY / "login.sqlite")
    conn.execute("CREATE TABLE IF NOT EXISTS accounts (email TEXT PRIMARY KEY, password_hash BLOB, salt BLOB)")
    conn.execute("""CREATE TABLE IF NOT EXISTS challenges
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, hash BLOB, salt BLOB, pending_password BLOB,
                  password_salt BLOB, expires INTEGER, attempts INTEGER)""")
    conn.execute("CREATE TABLE IF NOT EXISTS rate (email TEXT PRIMARY KEY, start INTEGER, tries INTEGER)")
    return conn


def digest(value, salt):
    return hashlib.scrypt(value.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def deliver(email, code, challenge):
    host = os.getenv("RECOVERY_SMTP_HOST")
    if not host:
        MAILBOX.mkdir(exist_ok=True)
        (MAILBOX / f"{challenge}.txt").write_text(f"{email}\nVerification code: {code}\n", encoding="utf8")
        return
    message = EmailMessage()
    message["From"] = os.environ["RECOVERY_MAIL_FROM"]
    message["To"] = email
    message["Subject"] = "Recovery Companion verification code"
    message.set_content(f"Your sign-in code is {code}. It expires in 10 minutes.")
    with smtplib.SMTP_SSL(host, int(os.getenv("RECOVERY_SMTP_PORT", "465")),
                          context=ssl.create_default_context(), timeout=12) as client:
        client.login(os.environ["RECOVERY_SMTP_USER"], os.environ["RECOVERY_SMTP_PASSWORD"])
        client.send_message(message)


def begin(email, password, signup):
    email = email.strip().casefold()
    if len(email) > 254 or not re.fullmatch(r"[^\s@<>:,;]+@[^\s@<>:,;]+\.[^\s@<>:,;]+", email):
        raise ValueError("Enter a valid email address.")
    if not password or len(password) > 256:
        raise ValueError("Enter a password up to 256 characters.")
    if signup and (len(password) < 6 or not re.search(r"[0-9]", password)
                   or not re.search(r"[^\w\s]|_", password)):
        raise ValueError("Use at least six characters, one number and one special character.")
    now = int(time.time())
    with closing(database()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM rate WHERE start <= ?", (now - 600,))
        conn.execute("INSERT INTO rate VALUES (?,?,1) ON CONFLICT(email) DO UPDATE SET tries=tries+1", (email, now))
        tries = conn.execute("SELECT tries FROM rate WHERE email=?", (email,)).fetchone()[0]
    if tries > 10:
        raise ValueError("Too many attempts. Try again in ten minutes.")
    with closing(database()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        found = conn.execute("SELECT password_hash, salt FROM accounts WHERE email=?", (email,)).fetchone()
        if signup and found:
            raise ValueError("Unable to create this account. Try signing in.")
        salt = found[1] if found else secrets.token_bytes(16)
        hashed = digest(password, salt)
        if not signup and (not found or not hmac.compare_digest(found[0], hashed)):
            raise ValueError("The email or password is incorrect.")
        challenge = secrets.token_hex(16)
        code = f"{secrets.randbelow(1000000):06d}"
        code_salt = secrets.token_bytes(16)
        conn.execute("DELETE FROM challenges WHERE email=? OR expires<=?", (email, now))
        conn.execute("INSERT INTO challenges VALUES (?,?,?,?,?,?,?,0)",
                     (challenge, email, digest(code, code_salt), code_salt,
                      hashed if signup else None, salt if signup else None, now + CODE_LIFETIME))
    try:
        deliver(email, code, challenge)
    except (OSError, KeyError, ValueError, smtplib.SMTPException):
        with closing(database()) as conn, conn:
            conn.execute("DELETE FROM challenges WHERE id=?", (challenge,))
        raise ValueError("Code delivery failed. Check the email settings and try again.") from None
    return challenge


def verify(challenge, code):
    with closing(database()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT email,hash,salt,pending_password,password_salt,expires,attempts FROM challenges WHERE id=?",
                           (challenge,)).fetchone()
        if not row or row[5] <= time.time() or row[6] >= 5:
            return None
        if not hmac.compare_digest(digest(code.strip(), row[2]), row[1]):
            conn.execute("UPDATE challenges SET attempts=attempts+1 WHERE id=?", (challenge,))
            return None
        conn.execute("DELETE FROM challenges WHERE id=?", (challenge,))
        if row[3] is not None:
            conn.execute("INSERT INTO accounts VALUES (?,?,?)", (row[0], row[3], row[4]))
    (MAILBOX / f"{challenge}.txt").unlink(missing_ok=True)
    return row[0]
