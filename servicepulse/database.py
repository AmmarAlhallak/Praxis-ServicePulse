"""PostgreSQL-Verbindung. Keine Excel-Rückfallquelle für Serviceberichte."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]


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
