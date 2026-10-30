"""Echtes PostgreSQL, getrennte kurzlebige Testdatenbank. Keine Testberichte im Nutzbestand."""

import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from scripts.prepare_database import connection_url, migrate
from servicepulse import repository as repo
from servicepulse.faults import metrics, read_faults

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def test_cluster(postgres_instance):
    return postgres_instance


@pytest.fixture(scope="module")
def isolated_database(test_cluster):
    settings, _ = test_cluster
    name = "servicepulse_test_" + uuid.uuid4().hex
    args = dict(
        host="127.0.0.1",
        port=settings["port"],
        dbname="postgres",
        user="servicepulse_owner",
        password=settings["admin_password"],
        autocommit=True,
    )
    with psycopg.connect(**args) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    db = create_engine(connection_url(settings, True, database=name), hide_parameters=True)
    try:
        migrate(db)
        yield db
    finally:
        db.dispose()
        with psycopg.connect(**args) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def database(isolated_database):
    db = isolated_database
    # Ausschließlich die oben erzeugte Testdatenbank. Originaldatenbank nie leeren.
    assert db.url.database.startswith("servicepulse_test_")
    with db.begin() as con:
        con.execute(
            text(
                "TRUNCATE audit_log,service_actions,service_reports,measurement_files,sources,categories,devices RESTART IDENTITY CASCADE"
            )
        )
    repo.import_research(ROOT, db)
    return db


def data(**changes):
    return dict(
        device_id="806279",
        service_date=date(2026, 10, 30),
        category="Unbekannt",
        description="Künstlicher Bericht ausschließlich in der Testdatenbank",
        component="",
        action="Testmaßnahme",
        status="offen",
        notes="",
        source="Automatisierter Test",
        actor="pytest",
        reason="Testanlage",
        **changes,
    )


def test_import_idempotent_and_original_values(database):
    assert repo.import_research(ROOT, database) == 0
    original = read_faults(ROOT / "fault_summary_R1.xlsx")
    actual = repo.reports_frame(database, originals=True)
    pd.testing.assert_frame_equal(original, actual[original.columns], check_dtype=False)
    assert list(metrics(repo.reports_frame(database)).values())[:4] == [46, 24, 11, 5]
    with Session(database) as session:
        from servicepulse.models import Audit

        assert len(session.scalars(select(Audit)).all()) == 46


def test_create_edit_durable_and_audited(database):
    values = data()
    rid = repo.save_report(values, request_key="same-submission", db=database)
    assert repo.save_report(values, request_key="same-submission", db=database) == rid
    database.dispose()  # Neue Verbindung, keine Prozess-/Session-Speicherung.
    assert len(repo.reports_frame(database)) == 47
    values.update(
        description="Geänderte Testbeschreibung",
        action="Zweite Testmaßnahme",
        status="abgeschlossen",
        reason="Testkorrektur",
    )
    repo.save_report(values, rid, 1, db=database)
    updated = repo.reports_frame(database).query("report_id==@rid").iloc[0]
    assert updated.action == "Zweite Testmaßnahme" and updated.report_version == 2
    log = repo.history(rid, database)
    assert (
        len(log) == 2
        and log[-1]["Vorher"]["action"] == "Testmaßnahme"
        and log[-1]["Nachher"]["action"] == "Zweite Testmaßnahme"
    )
    with pytest.raises(ValueError, match="inzwischen geändert"):
        repo.save_report(values, rid, 1, db=database)


def test_historical_edits_keep_originals_and_no_delete(database):
    original = repo.reports_frame(database, True)
    current = repo.reports_frame(database).iloc[0]
    values = data()
    values.update(
        device_id=current.device_id,
        category=current.category,
        description="Arbeitsfassung im Test",
        source=current.source_file,
    )
    repo.save_report(values, int(current.report_id), 1, db=database)
    pd.testing.assert_frame_equal(original, repo.reports_frame(database, True))
    with pytest.raises(DBAPIError):
        with database.begin() as con:
            con.execute(
                text("DELETE FROM service_reports WHERE id=:id"), {"id": int(current.report_id)}
            )
    with pytest.raises(DBAPIError):
        with database.begin() as con:
            con.execute(
                text("UPDATE service_reports SET original='{}'::jsonb WHERE id=:id"),
                {"id": int(current.report_id)},
            )


def test_new_device_missing_fields_and_validation(database):
    repo.add_device("999991", "Testgerät ohne Sensoren", db=database)
    values = data()
    values.update(device_id="999991", service_date=None, description="", action="")
    rid = repo.save_report(values, db=database)
    row = repo.reports_frame(database).query("report_id==@rid").iloc[0]
    assert row.report_id == rid
    assert pd.isna(row.event_date) and row.origin == "manual" and row.category == "Unbekannt"
    assert repo.files_frame(database).empty
    with pytest.raises(ValueError, match="bereits registriert"):
        repo.add_device("999991", db=database)
    with pytest.raises(ValueError):
        repo.add_device("../bad", db=database)
    values["source"] = ""
    with pytest.raises(ValueError, match="Herkunft"):
        repo.save_report(values, db=database)
    assert len(repo.reports_frame(database)) == 47


def test_management_form_updates_statistics_and_history(database, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(repo, "engine", lambda: database)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception and app.metric[0].value == "46"
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    app.button(key="open_new_report_806279").click().run()
    assert not app.exception
    description = next(w for w in app.text_area if w.label == "Beschreibung der Störung")
    source = next(w for w in app.text_input if w.label == "Quelle / Herkunft")
    description.set_value("Automatischer Formulartest, kein Forschungsbefund")
    source.set_value("Isolierte PostgreSQL-Testdatenbank")
    next(b for b in app.button if b.label == "Servicebericht speichern").click().run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "47"
    assert any("dauerhaft gespeichert" in v.value for v in app.success)
    assert len(repo.reports_frame(database)) == 47
    app.radio(key="report_mode").set_value("Bestehenden Bericht bearbeiten").run()
    assert not app.exception
    latest = int(repo.reports_frame(database).report_id.max())
    app.selectbox(key="edit_report_806279").set_value(latest).run()
    next(
        w for w in app.text_area if w.label == "Reparatur oder Wartungsmaßnahme (optional)"
    ).set_value("Teständerung aus Formular")
    next(w for w in app.text_input if w.label == "Grund der Änderung").set_value(
        "Formularbearbeitung prüfen"
    )
    next(b for b in app.button if b.label == "Änderungen speichern").click().run()
    assert not app.exception and not app.error
    assert repo.history(latest, database)[-1]["Nachher"]["action"] == "Teständerung aus Formular"


def test_parquet_import_validates_null_times_and_duplicate_bytes(tmp_path, database):
    import io

    from servicepulse.imports import import_parquet

    frame = pd.DataFrame({"Datetime": pd.to_datetime(["2022-01-01", None]), "RTD": [-80.0, -79.0]})
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    with pytest.raises(ValueError, match="fehlende Zeitstempel"):
        import_parquet(buffer.getvalue(), "999991_temp.parquet", tmp_path)
    frame = frame.dropna()
    frame.to_parquet(tmp_path / "999991_temp.parquet", index=False)
    repo.register_file(tmp_path / "999991_temp.parquet", "Test", database)
    with pytest.raises(ValueError, match="Identische Messdatei"):
        import_parquet(
            (tmp_path / "999991_temp.parquet").read_bytes(),
            "999992_temp.parquet",
            tmp_path,
            registry=repo.files_frame(database),
            source="Test",
        )
    assert not (tmp_path / "999992_temp.parquet").exists()


def test_owned_postgresql_restart_keeps_new_report(database, test_cluster):
    from scripts.prepare_database import run

    settings, cluster = test_cluster
    rid = repo.save_report(data(), db=database)
    database.dispose()
    try:
        run(Path(settings["bin"]) / "pg_ctl.exe", "-D", cluster, "-m", "fast", "-w", "stop")
    finally:
        run(
            Path(settings["bin"]) / "pg_ctl.exe",
            "-D",
            cluster,
            "-l",
            cluster.parent / "server.log",
            "-w",
            "start",
        )
    persisted = repo.reports_frame(database)
    row = persisted.loc[persisted.report_id.eq(rid)].iloc[0]
    assert row.fault_text == "Künstlicher Bericht ausschließlich in der Testdatenbank"
    assert len(repo.history(rid, database)) == 1


def test_application_role_can_save_but_cannot_delete_or_rewrite_audit(database, test_cluster):
    settings, _ = test_cluster
    with database.begin() as con:
        con.execute(text("GRANT USAGE ON SCHEMA public TO servicepulse_app"))
        con.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE ON devices,categories,sources,service_reports,service_actions,measurement_files TO servicepulse_app"
            )
        )
        con.execute(text("GRANT SELECT, INSERT ON audit_log TO servicepulse_app"))
        con.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO servicepulse_app")
        )
    app = create_engine(
        connection_url(settings, database=database.url.database), hide_parameters=True
    )
    try:
        rid = repo.save_report(data(), db=app)
        assert len(repo.history(rid, app)) == 1
        with pytest.raises(DBAPIError):
            with app.begin() as con:
                con.execute(text("DELETE FROM service_reports WHERE id=:id"), {"id": rid})
        with pytest.raises(DBAPIError):
            with app.begin() as con:
                con.execute(
                    text("UPDATE audit_log SET reason='tampered' WHERE report_id=:id"), {"id": rid}
                )
    finally:
        app.dispose()


def test_dump_restore_retains_report_and_audit(database, tmp_path, test_cluster):
    import os

    from scripts.prepare_database import run

    settings, _ = test_cluster
    rid = repo.save_report(data(), db=database)
    from scripts.prepare_database import backup

    target = backup(settings, database=database.url.database, directory=tmp_path)
    assert target.exists()
    env = {**os.environ, "PGPASSWORD": settings["admin_password"]}
    name = "servicepulse_restore_test_" + uuid.uuid4().hex
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
    restored = create_engine(connection_url(settings, True, database=name), hide_parameters=True)
    try:
        run(
            Path(settings["bin"]) / "pg_restore.exe",
            "-h",
            "127.0.0.1",
            "-p",
            settings["port"],
            "-U",
            "servicepulse_owner",
            "-d",
            name,
            "--exit-on-error",
            target,
            env=env,
        )
        assert len(repo.reports_frame(restored)) == 47
        assert len(repo.history(rid, restored)) == 1
        assert len(repo.reports_frame(restored, True)) == 46
    finally:
        restored.dispose()
        with psycopg.connect(**args) as c:
            c.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.mark.local_data
def test_real_temperature_gap_warm_values_and_corrected_events():
    from servicepulse.case_review import review_temperature
    from servicepulse.measurements import event_window, offsets

    path = ROOT / "data/raw/Revco/806279_temp.parquet"
    if not path.exists():
        pytest.skip("Reale Parquet-Datei fehlt")
    gaps, daily, warm, states = review_temperature(path, "2022-06-21", "2022-07-06")
    assert gaps.iloc[0].seconds == 432715
    assert gaps.iloc[0].previous == pd.Timestamp("2022-06-22 10:36:20")
    assert warm.rows == 145 and warm.maximum == pytest.approx(21.8)
    assert daily.repeated_timestamps.sum() == 0
    clock = offsets(ROOT / "research/reference/data/raw_data/other_data/time_offsets.csv")["806279"]
    assert clock == pd.Timedelta(minutes=9, seconds=20)
    events = event_window(
        ROOT / "data/raw/Revco/806279_events.parquet", "2022-06-21", "2022-07-06", clock
    )
    assert events.loc[events.Event.eq("Shutdown"), "Datetime"].iloc[0] == pd.Timestamp(
        "2022-06-22 10:36:52"
    )
    assert events.loc[events.Event.eq("Display Power On"), "Datetime"].iloc[0] == pd.Timestamp(
        "2022-06-27 10:48:09"
    )


def test_collapsed_form_and_historical_missingness_are_display_only(database, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(repo, "engine", lambda: database)
    before = repo.reports_frame(database)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    tables = [w.value for w in app.dataframe if "Herkunft" in w.value and "Maßnahme" in w.value]
    assert tables
    for frame in tables:
        historical = frame[frame.Herkunft.eq("Veröffentlichte Forschungsdaten")]
        assert historical.Status.eq("Nicht dokumentiert").all()
        assert historical["Maßnahme"].eq("Nicht dokumentiert").all()
    app.button(key="open_new_report_806279").click().run()
    assert any(w.label == "Beschreibung der Störung" for w in app.text_area)
    app.button(key="close_new_report_806279").click().run()
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    app.radio(key="report_mode").set_value("Bestehenden Bericht bearbeiten").run()
    status = next(w for w in app.selectbox if w.label == "Status")
    assert status.value == "nicht angegeben" and "Nicht dokumentiert" in status.options
    pd.testing.assert_frame_equal(before, repo.reports_frame(database))


def test_new_device_report_full_flow_and_dashboard_restart(database, monkeypatch):
    """Alle acht angefragten Schritte, ausschließlich im temporären Testbestand."""
    import os
    import socket
    import subprocess
    import sys
    import tempfile
    import time
    import urllib.request

    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(repo, "engine", lambda: database)
    original = repo.reports_frame(database, True)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.text_input(key="new_device_id").set_value("999992")
    app.text_input(key="new_device_name").set_value("Isoliertes automatisiertes Testgerät")
    next(b for b in app.button if b.label == "Gerät anlegen").click().run()
    assert not app.exception and "999992" in set(repo.devices_frame(database)["Geräte-ID"])
    app.selectbox(key="managed_device").set_value("999992").run()
    assert any("keine Messdaten" in info.value for info in app.info)
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    app.button(key="open_new_report_999992").click().run()
    next(w for w in app.text_area if w.label == "Beschreibung der Störung").set_value(
        "Künstlicher isolierter Testbericht"
    )
    next(w for w in app.text_input if w.label == "Quelle / Herkunft").set_value(
        "Automatisierte Testdatenbank"
    )
    next(b for b in app.button if b.label == "Servicebericht speichern").click().run()
    assert not app.exception and not app.error
    assert [w.value for w in app.metric[:4]] == ["47", "25", "11", "5"]
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    with database.connect() as c:
        saved = c.execute(
            text(
                "SELECT id,origin,original,source_row,status FROM service_reports WHERE device_id='999992'"
            )
        ).one()
        assert saved.origin == "manual" and saved.original is None and saved.source_row is None
        assert (
            c.execute(text("SELECT count(*) FROM service_reports WHERE origin='research'")).scalar()
            == 46
        )
    assert repo.import_research(ROOT, database) == 0
    assert repo.import_research(ROOT, database) == 0
    assert len(repo.reports_frame(database)) == 47
    # Wirklichen Dashboard-Server zweimal in eigenen Prozessen auf freiem Port starten.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "SERVICEPULSE_DATABASE_URL": database.url.render_as_string(hide_password=False),
    }
    with tempfile.TemporaryFile() as log:
        for _ in range(2):
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(ROOT / "app.py"),
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    str(port),
                    "--server.headless",
                    "true",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 45
                while True:
                    try:
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/_stcore/health", timeout=2
                        ) as response:
                            assert response.read() == b"ok"
                        break
                    except OSError:
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise AssertionError("Isolierter Dashboard-Start fehlgeschlagen")
                        time.sleep(0.2)
            finally:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True
                    )
                else:
                    process.terminate()
                process.wait(timeout=15)
    # Frischer Dashboardzustand nach den beiden tatsächlichen Server-Prozessstarts.
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception and app.metric[0].value == "47"
    app.selectbox(key="managed_device").set_value("999992").run()
    assert any(
        "Künstlicher isolierter Testbericht" in frame.value.astype(str).to_string()
        for frame in app.dataframe
    )
    app.radio(key="report_mode").set_value("Bestehenden Bericht bearbeiten").run()
    next(
        w for w in app.text_area if w.label == "Reparatur oder Wartungsmaßnahme (optional)"
    ).set_value("Isolierte Testmaßnahme")
    next(w for w in app.selectbox if w.label == "Status").set_value("abgeschlossen")
    next(w for w in app.text_input if w.label == "Grund der Änderung").set_value(
        "Änderungshistorie prüfen"
    )
    next(b for b in app.button if b.label == "Änderungen speichern").click().run()
    assert not app.exception and not app.error
    assert [w.value for w in app.metric[:4]] == ["47", "25", "11", "5"]
    changes = repo.history(saved.id, database)
    assert len(changes) == 2 and changes[-1]["Version"] == 2
    assert changes[-1]["Vorher"]["status"] == "offen"
    assert changes[-1]["Nachher"]["status"] == "abgeschlossen"
    assert changes[-1]["Nachher"]["action"] == "Isolierte Testmaßnahme"
    assert changes[-1]["Grund"] == "Änderungshistorie prüfen"
    pd.testing.assert_frame_equal(original, repo.reports_frame(database, True))
    assert repo.files_frame(database).empty


def test_transaction_failure_rolls_back_report_source_and_audit(database):
    # Zusätzliche Fehlerbedingung ausschließlich in der temporären Testdatenbank.
    with database.begin() as c:
        c.execute(
            text(
                "ALTER TABLE service_actions ADD CONSTRAINT test_rejected_action CHECK (text <> 'rollback fixture')"
            )
        )

    def counts():
        with database.connect() as c:
            return [
                c.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                for table in ["service_reports", "sources", "audit_log", "service_actions"]
            ]

    before = counts()
    values = data()
    values["action"] = "rollback fixture"
    try:
        with pytest.raises(DBAPIError):
            repo.save_report(values, db=database)
        assert counts() == before
    finally:
        with database.begin() as c:
            c.execute(text("ALTER TABLE service_actions DROP CONSTRAINT test_rejected_action"))


def test_concurrent_edits_do_not_overwrite(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    rid = repo.save_report(data(), db=database)
    ready = Barrier(2)

    def edit(label):
        values = data()
        values.update(description=label, action="  " + label + "  ")
        ready.wait(timeout=10)
        try:
            repo.save_report(values, rid, 1, db=database)
            return "saved"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(edit, ["first", "second"])) == ["conflict", "saved"]
    frame = repo.reports_frame(database)
    row = frame.loc[frame.report_id.eq(rid)].iloc[0]
    log = repo.history(rid, database)
    assert len(log) == 2 and row.report_version == 2
    assert log[-1]["Nachher"]["action"] == row.action


def test_migrations_match_models_and_empty_reports_have_stable_columns(database):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from servicepulse.models import Base

    with database.connect() as c:
        assert compare_metadata(MigrationContext.configure(c), Base.metadata) == []
    with database.begin() as c:
        c.execute(
            text("TRUNCATE audit_log,service_actions,service_reports RESTART IDENTITY CASCADE")
        )
    frame = repo.reports_frame(database)
    assert frame.empty and {"status", "action", "component", "report_version", "notes"}.issubset(
        frame.columns
    )


def test_normal_start_only_checks_schema_without_maintenance(database, monkeypatch, tmp_path):
    from types import SimpleNamespace

    from alembic.config import Config

    import scripts.prepare_database as startup
    import servicepulse.database as connection

    for name in ["state.json", "PG_VERSION", ".env"]:
        (tmp_path / name).write_text("test fixture")
    config = Config(str(ROOT / "alembic.ini"))
    monkeypatch.setattr(startup, "ROOT", tmp_path)
    monkeypatch.setattr(startup, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(startup, "CLUSTER", tmp_path)
    monkeypatch.setattr(startup, "Config", lambda path: config)
    monkeypatch.setattr(startup, "local_settings", lambda: {})
    monkeypatch.setattr(connection, "engine", lambda: database)
    calls = []
    monkeypatch.setattr(startup, "ensure_server", lambda settings: calls.append("start"))

    def forbidden(*args, **kwargs):
        raise AssertionError("Normal start must not run maintenance")

    for name in ["prepare", "migrate", "backup", "start_local"]:
        monkeypatch.setattr(startup, name, forbidden)
    for name in ["import_research", "sync_measurements"]:
        monkeypatch.setattr(repo, name, forbidden)
    before = repo.reports_frame(database)
    startup.start_existing()
    assert calls == ["start"]
    pd.testing.assert_frame_equal(before, repo.reports_frame(database))
    # Eine ausstehende Migration wird angezeigt, nicht stillschweigend angewendet.
    monkeypatch.setattr(
        startup.ScriptDirectory,
        "from_config",
        lambda config: SimpleNamespace(get_heads=lambda: ["future-revision"]),
    )
    with pytest.raises(RuntimeError, match="Migration"):
        startup.start_existing()
