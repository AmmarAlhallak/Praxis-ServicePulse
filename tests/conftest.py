"""Isolierte native PostgreSQL-Instanz; CI benötigt keine lokale Konfiguration."""

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine

from scripts.prepare_database import connection_url, find_postgres_bin, migrate
from servicepulse import repository as repo

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def postgres_instance(tmp_path_factory):
    """Eigene temporäre PostgreSQL-Instanz, auch Neustarts betreffen keinen Nutzserver."""
    import secrets
    import socket

    from scripts.prepare_database import run

    folder = tmp_path_factory.mktemp("servicepulse_pg")
    cluster = folder / "cluster"
    settings = {"bin": str(find_postgres_bin())}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        settings["port"] = sock.getsockname()[1]
    settings.update(
        admin_password=secrets.token_urlsafe(32), app_password=secrets.token_urlsafe(32)
    )
    password = folder / "init.tmp"
    password.write_text(settings["admin_password"], encoding="utf-8")
    try:
        run(
            Path(settings["bin"]) / "initdb.exe",
            "-D",
            cluster,
            "-U",
            "servicepulse_owner",
            "--encoding=UTF8",
            "--locale=C",
            "--auth=scram-sha-256",
            "--pwfile",
            password,
        )
    finally:
        password.unlink(missing_ok=True)
    with (cluster / "postgresql.conf").open("a", encoding="utf-8") as handle:
        handle.write(f"\nlisten_addresses='127.0.0.1'\nport={settings['port']}\n")
    run(
        Path(settings["bin"]) / "pg_ctl.exe",
        "-D",
        cluster,
        "-l",
        folder / "server.log",
        "-w",
        "start",
    )
    try:
        with psycopg.connect(
            host="127.0.0.1",
            port=settings["port"],
            dbname="postgres",
            user="servicepulse_owner",
            password=settings["admin_password"],
            autocommit=True,
        ) as c:
            c.execute(
                sql.SQL("CREATE ROLE servicepulse_app LOGIN PASSWORD {}").format(
                    sql.Literal(settings["app_password"])
                )
            )
        yield settings, cluster
    finally:
        run(Path(settings["bin"]) / "pg_ctl.exe", "-D", cluster, "-m", "fast", "-w", "stop")


@pytest.fixture(scope="session")
def ci_application_database(postgres_instance):
    """Eigener Excel-Demobestand für CI-Oberflächentests, getrennt von Schreibtests."""
    settings, _ = postgres_instance
    name = "servicepulse_ci_" + uuid.uuid4().hex
    args = dict(
        host="127.0.0.1",
        port=settings["port"],
        dbname="postgres",
        user="servicepulse_owner",
        password=settings["admin_password"],
        autocommit=True,
    )
    with psycopg.connect(**args) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    db = create_engine(
        connection_url(settings, True, database=name), hide_parameters=True, pool_pre_ping=True
    )
    try:
        migrate(db)
        repo.import_research(ROOT, db)
        yield db
    finally:
        db.dispose()
        with psycopg.connect(**args) as c:
            c.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture(autouse=True)
def route_ci_to_test_database(request, monkeypatch):
    if os.environ.get("SERVICEPULSE_CI") != "1":
        return
    db = request.getfixturevalue("ci_application_database")
    # Eine Einstellung ist verbindlich: keine implizite Verbindung zum Nutzbestand.
    assert db.url.database.startswith("servicepulse_ci_")
    monkeypatch.setattr(repo, "engine", lambda: db)
    monkeypatch.setenv("SERVICEPULSE_DATABASE_URL", db.url.render_as_string(hide_password=False))
