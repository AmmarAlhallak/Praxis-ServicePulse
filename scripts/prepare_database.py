"""Lokale PostgreSQL-Instanz mit vorhandenen Windows-Binärdateien starten."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from servicepulse.database import ROOT

PRIVATE = ROOT / "data/private"
STATE = PRIVATE / "postgres.json"
CLUSTER = ROOT / "data/postgresql"


def find_postgres_bin() -> Path:
    """Findet vorhandene PostgreSQL-Programme, auch auf dem isolierten CI-Rechner."""
    configured = os.environ.get("SERVICEPULSE_PG_BIN") or os.environ.get("PGBIN")
    if configured and (Path(configured) / "pg_ctl.exe").exists():
        return Path(configured)
    candidates = sorted(
        Path("C:/Program Files/PostgreSQL").glob("*/bin/pg_ctl.exe"),
        key=lambda p: tuple(int(x) for x in p.parent.parent.name.split(".")),
        reverse=True,
    )
    if candidates:
        return candidates[0].parent
    command = shutil.which("pg_ctl")
    if command:
        return Path(command).parent
    raise RuntimeError("PostgreSQL-Binärdateien fehlen. Hinweise: docs/postgresql_windows.md")


def run(executable: str | Path, *args: object, env: dict[str, str] | None = None) -> None:
    """Führt ein PostgreSQL-Werkzeug ohne Ausgabe möglicher Zugangsdaten aus."""
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(
            [str(executable), *map(str, args)],
            stdout=output,
            stderr=output,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    if result.returncode:
        # Programme können Verbindungsparameter ausgeben: keine Geheimnisse weiterreichen.
        raise RuntimeError(
            f"{Path(executable).name} fehlgeschlagen. Lokales PostgreSQL-Protokoll prüfen."
        )


def local_settings() -> dict[str, Any]:
    """Liest lokale Einstellungen; erzeugt sie nur für die Erstvorbereitung."""
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        STATE.write_text(
            json.dumps(
                {
                    "bin": str(find_postgres_bin()),
                    "port": 55432,
                    "admin_password": secrets.token_urlsafe(32),
                    "app_password": secrets.token_urlsafe(32),
                }
            ),
            encoding="utf-8",
        )
        if os.name == "nt":
            # Nur das aktuelle Windows-Konto erhält Zugriff auf lokale Geheimnisse.
            user = subprocess.check_output(["whoami"], text=True).strip()
            run("icacls.exe", PRIVATE, "/inheritance:r", "/grant:r", f"{user}:(OI)(CI)F")
    return json.loads(STATE.read_text(encoding="utf-8"))


def connection_url(
    settings: dict[str, Any], admin: bool = False, database: str = "servicepulse"
) -> URL:
    """Erstellt eine SQLAlchemy-Verbindung für die gewählte lokale Rolle und Datenbank."""
    return URL.create(
        "postgresql+psycopg",
        username="servicepulse_owner" if admin else "servicepulse_app",
        password=settings["admin_password" if admin else "app_password"],
        host="127.0.0.1",
        port=settings["port"],
        database=database,
    )


def ensure_server(settings: dict[str, Any], initialize: bool = False) -> None:
    """Startet nur den eigenen Server; verändert keine Tabellen oder Rollen."""
    binpath = Path(settings["bin"])
    if not (CLUSTER / "PG_VERSION").exists():
        if not initialize:
            raise RuntimeError("PostgreSQL noch nicht vorbereitet. prepare_database.py ausführen.")
        password_file = PRIVATE / "init-password.tmp"
        password_file.write_text(settings["admin_password"], encoding="utf-8")
        try:
            run(
                binpath / "initdb.exe",
                "-D",
                CLUSTER,
                "-U",
                "servicepulse_owner",
                "--encoding=UTF8",
                "--locale=C",
                "--auth=scram-sha-256",
                "--pwfile",
                password_file,
            )
        finally:
            password_file.unlink(missing_ok=True)
        with (CLUSTER / "postgresql.conf").open("a", encoding="utf-8") as handle:
            handle.write(
                "\nlisten_addresses = '127.0.0.1'\nport = "
                + str(settings["port"])
                + "\npassword_encryption = 'scram-sha-256'\n"
            )
    status = subprocess.run(
        [str(binpath / "pg_ctl.exe"), "-D", str(CLUSTER), "status"], capture_output=True
    )
    if status.returncode:
        run(
            binpath / "pg_ctl.exe", "-D", CLUSTER, "-l", ROOT / "data/postgresql.log", "-w", "start"
        )


def start_local() -> dict[str, Any]:
    """Erstvorbereitung: startet die Instanz und legt fehlende Datenbank/Rollen an."""
    settings = local_settings()
    ensure_server(settings, initialize=True)
    with psycopg.connect(
        host="127.0.0.1",
        port=settings["port"],
        dbname="postgres",
        user="servicepulse_owner",
        password=settings["admin_password"],
        autocommit=True,
    ) as con:
        if not con.execute("SELECT 1 FROM pg_database WHERE datname='servicepulse'").fetchone():
            con.execute("CREATE DATABASE servicepulse OWNER servicepulse_owner")
        if not con.execute("SELECT 1 FROM pg_roles WHERE rolname='servicepulse_app'").fetchone():
            con.execute(
                sql.SQL("CREATE ROLE servicepulse_app LOGIN PASSWORD {}").format(
                    sql.Literal(settings["app_password"])
                )
            )
        con.execute("REVOKE ALL ON DATABASE servicepulse FROM PUBLIC")
        con.execute("GRANT CONNECT ON DATABASE servicepulse TO servicepulse_app")
    return settings


def migrate(db: Engine) -> None:
    """Wendet ausstehende Alembic-Versionen auf der ausdrücklich übergebenen Verbindung an."""
    cfg = Config(str(ROOT / "alembic.ini"))
    with db.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(73210646)"))
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def backup(
    settings: dict[str, Any], database: str = "servicepulse", directory: Path | None = None
) -> Path:
    """Sichert die gewählte Datenbank und liefert den Dump-Pfad; Tests nutzen eigene Ziele."""
    directory = directory or ROOT / "data/backups/postgresql"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"servicepulse_{datetime.now():%Y%m%d_%H%M%S_%f}.dump"
    env = {**os.environ, "PGPASSWORD": settings["admin_password"]}
    run(
        Path(settings["bin"]) / "pg_dump.exe",
        "-h",
        "127.0.0.1",
        "-p",
        settings["port"],
        "-U",
        "servicepulse_owner",
        "-d",
        database,
        "-Fc",
        "-f",
        target,
        env=env,
    )
    return target


def prepare() -> None:
    """Explizite Erstvorbereitung mit Migration, Import, Rechten und Sicherung."""
    settings = start_local()
    owner = create_engine(connection_url(settings, True), hide_parameters=True)
    try:
        prepare_contents(settings, owner)
    finally:
        owner.dispose()


def prepare_contents(settings: dict[str, Any], owner: Engine) -> None:
    """Bereitet Schema, Daten, Rollenrechte und lokale App-Konfiguration vor."""
    migrate(owner)
    with owner.begin() as con:
        con.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
        con.execute(text("GRANT USAGE ON SCHEMA public TO servicepulse_app"))
        con.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE ON devices,categories,sources,service_reports,service_actions,measurement_files TO servicepulse_app"
            )
        )
        con.execute(text("GRANT SELECT, INSERT ON audit_log TO servicepulse_app"))
        con.execute(text("GRANT SELECT ON alembic_version TO servicepulse_app"))
        con.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO servicepulse_app")
        )
    from servicepulse.repository import import_research, sync_measurements

    added = import_research(ROOT, owner)
    files = sync_measurements(ROOT, owner)
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(
            "SERVICEPULSE_DATABASE_URL="
            + connection_url(settings).render_as_string(hide_password=False)
            + "\n",
            encoding="utf-8",
        )
        if os.name == "nt":
            user = subprocess.check_output(["whoami"], text=True).strip()
            run("icacls.exe", env_path, "/inheritance:r", "/grant:r", f"{user}:F")
    print(f"PostgreSQL bereit. Neu übernommen: {added} Serviceeinträge, {files} Messdateien.")
    backup(settings)


def start_existing() -> None:
    """Normalstart: Server und Schemas prüfen; kein Import, Grant oder Backup."""
    if not (STATE.exists() and (CLUSTER / "PG_VERSION").exists() and (ROOT / ".env").exists()):
        prepare()
        return
    ensure_server(local_settings())
    from servicepulse.database import engine

    expected = set(ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads())
    with engine().connect() as connection:
        actual = set(MigrationContext.configure(connection).get_current_heads())
        if actual != expected:
            raise RuntimeError(
                "Datenbankschema benötigt eine Migration. prepare_database.py --migrate ausführen."
            )
    print("PostgreSQL bereit. Normalstart ohne Import oder Backup.")


def main() -> int:
    """Trennt Normalstart von bewussten Wartungsaktionen."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    for flag in ["start-only", "migrate", "sync", "backup"]:
        actions.add_argument("--" + flag, action="store_true")
    args = parser.parse_args()
    try:
        if args.start_only:
            start_existing()
        elif args.backup:
            settings = local_settings()
            ensure_server(settings)
            backup(settings)
            print("PostgreSQL-Sicherung erstellt.")
        elif args.migrate or args.sync:
            settings = start_local()
            owner = create_engine(connection_url(settings, True), hide_parameters=True)
            try:
                if args.migrate:
                    migrate(owner)
                    print("Migrationen angewendet.")
                else:
                    from servicepulse.repository import import_research, sync_measurements

                    print(
                        f"Synchronisiert: {import_research(ROOT, owner)} Serviceeinträge, {sync_measurements(ROOT, owner)} Messdateien neu."
                    )
            finally:
                owner.dispose()
        else:
            prepare()
    except Exception as exc:
        print(
            "Datenbankstart fehlgeschlagen: "
            + (
                str(exc)
                if isinstance(exc, RuntimeError)
                else type(exc).__name__ + ". Hinweise in docs/postgresql_windows.md."
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
