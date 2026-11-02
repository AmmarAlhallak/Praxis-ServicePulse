"""PostgreSQL-Verbindung. Keine Excel-Rückfallquelle für Serviceberichte."""

import os
import re
import subprocess
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]


def backup_database(db: Engine) -> Path:
    """Sichert exakt die übergebene PostgreSQL-Datenbank; Fehler verhindern die Änderung."""
    from scripts.prepare_database import find_postgres_bin, run

    url = db.url
    if db.dialect.name != "postgresql" or not all([url.host, url.database, url.username]):
        raise RuntimeError("Keine eindeutige PostgreSQL-Verbindung für die Sicherung vorhanden.")
    directory = ROOT / "data/backups/postgresql"
    directory.mkdir(parents=True, exist_ok=True)
    database_name = re.sub(r"[^A-Za-z0-9_-]", "_", str(url.database))
    target = (
        directory / f"{database_name}_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex[:8]}.dump"
    )
    env = {**os.environ}
    env.pop("PGPASSWORD", None)
    if url.password is not None:
        env["PGPASSWORD"] = str(url.password)
    binary = find_postgres_bin()
    try:
        run(
            binary / "pg_dump.exe",
            "-h",
            url.host,
            "-p",
            url.port or 5432,
            "-U",
            url.username,
            "-d",
            url.database,
            "-Fc",
            "-f",
            target,
            env=env,
        )
        check = subprocess.run(
            [str(binary / "pg_restore.exe"), "--list", str(target)], capture_output=True
        )
        if check.returncode or not target.exists() or target.stat().st_size == 0:
            raise RuntimeError("Die Datenbanksicherung konnte nicht verifiziert werden.")
    except Exception as exc:
        raise RuntimeError("Sicherung fehlgeschlagen. Der Bericht wurde nicht verändert.") from exc
    return target


@lru_cache
def engine() -> Engine:
    """Liefert den wiederverwendeten Verbindungspool aus der lokalen Konfiguration."""
    load_dotenv(ROOT / ".env")
    url = os.environ.get("SERVICEPULSE_DATABASE_URL")
    if not url:
        raise RuntimeError("Datenbank noch nicht eingerichtet. Bitte start.cmd ausführen.")
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("ServicePulse benötigt eine PostgreSQL-Verbindung.")
    return create_engine(
        url, pool_pre_ping=True, connect_args={"connect_timeout": 5}, hide_parameters=True
    )
