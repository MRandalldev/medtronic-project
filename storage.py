"""SQLite for a single development host, shared Postgres for hosted accounts."""
import os
import sqlite3


class PostgresDatabase:
    def __init__(self, url):
        import psycopg
        self.connection = psycopg.connect(url, connect_timeout=8)

    def execute(self, statement, params=()):
        if statement == "BEGIN IMMEDIATE":
            # The SQLite account transactions serialize mutually exclusive code issuance and verification.
            return self.connection.execute("SELECT pg_advisory_xact_lock(73411901)")
        sql = statement.replace("?", "%s").replace(" BLOB", " BYTEA")
        sql = sql.replace("SET tries=tries+1", "SET tries=rate.tries+1")
        return self.connection.execute(sql, params)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        if kind is None:
            self.connection.commit()
        else:
            self.connection.rollback()


def open_database(path):
    url = os.getenv("DATABASE_URL")
    if url:
        return PostgresDatabase(url)
    if os.getenv("VERCEL"):
        raise RuntimeError("Set DATABASE_URL to persist accounts across Vercel instances.")
    path.parent.mkdir(exist_ok=True)
    return sqlite3.connect(path)
