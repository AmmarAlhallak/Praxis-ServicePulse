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
    app.button(key="open_edit_report_806279").click().run()
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
    assert not any(w.key == "report_mode" for w in app.radio)
    listing = next(w.value for w in app.dataframe if "Standort" in w.value)
    assert listing.Bezeichnung.eq("Nicht dokumentiert").all()
    assert listing.Standort.eq("Nicht dokumentiert").all()
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
    app.button(key="open_edit_report_806279").click().run()
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    assert any("Original ist schreibgeschützt" in w.value for w in app.warning)
    rid = app.selectbox(key="edit_report_806279").value
    app.checkbox(key=f"enable_research_edit_806279_{rid}").check().run()
    status = next(w for w in app.selectbox if w.label == "Status")
    assert status.value == "nicht angegeben" and "Nicht dokumentiert" in status.options
    pd.testing.assert_frame_equal(before, repo.reports_frame(database))
    originals = repo.reports_frame(database, originals=True)
    next(w for w in app.text_area if w.label == "Beschreibung der Störung").set_value(
        "Explizite Arbeitsfassung ausschließlich in der Testdatenbank"
    )
    next(w for w in app.text_input if w.label == "Grund der Änderung").set_value(
        "Kennzeichnung der Forschungs-Arbeitsfassung prüfen"
    )
    next(b for b in app.button if b.label == "Arbeitsfassung speichern").click().run()
    assert not app.exception and not app.error
    assert not any(w.label == "Beschreibung der Störung" for w in app.text_area)
    pd.testing.assert_frame_equal(originals, repo.reports_frame(database, originals=True))
    assert len(repo.history(rid, database)) == 2
    assert any(
        "Forschungsdaten · Arbeitsfassung" in w.value.Herkunft.tolist()
        for w in app.dataframe
        if "Herkunft" in w.value
    )


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
    app.button(key="open_edit_report_999992").click().run()
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


def test_archive_restore_filters_audit_and_backups(database):
    originals = repo.reports_frame(database, True)
    base = repo.reports_frame(database)
    rid = repo.save_report(data(), db=database)
    full = repo.reports_frame(database)
    archive_backup = repo.archive_report(
        rid, 1, confirmed=True, reason="Testarchivierung", actor="pytest", db=database
    )
    assert archive_backup.exists() and archive_backup.stat().st_size > 0
    assert archive_backup.name.startswith(database.url.database + "_")
    pd.testing.assert_frame_equal(base, repo.reports_frame(database))
    archived = repo.reports_frame(database, archived=True)
    assert archived.report_id.tolist() == [rid] and archived.archived.all()
    with database.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM service_actions WHERE report_id=:id"), {"id": rid}
            ).scalar()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM sources WHERE id=(SELECT source_id FROM service_reports WHERE id=:id)"
                ),
                {"id": rid},
            ).scalar()
            == 1
        )
    log = repo.history(rid, database)
    assert len(log) == 2 and log[-1]["Bearbeiter"] == "pytest"
    assert log[-1]["Vorher"]["archived"] is False and log[-1]["Nachher"]["archived"] is True
    assert log[-1]["Nachher"]["action"] == "Testmaßnahme"
    assert "Archiviert:" in log[-1]["Grund"] and archive_backup.name in log[-1]["Grund"]
    restore_backup = repo.restore_report(
        rid, 2, confirmed=True, reason="Testwiederherstellung", actor="pytest", db=database
    )
    assert restore_backup.exists() and restore_backup != archive_backup
    assert repo.reports_frame(database, archived=True).empty
    restored = repo.reports_frame(database)
    pd.testing.assert_frame_equal(
        full.drop(columns="report_version"), restored.drop(columns="report_version")
    )
    log = repo.history(rid, database)
    assert len(log) == 3 and log[-1]["Nachher"]["archived"] is False
    assert log[-1]["Vorher"]["archived"] is True and "Wiederhergestellt:" in log[-1]["Grund"]
    pd.testing.assert_frame_equal(originals, repo.reports_frame(database, True))


def test_archive_confirmation_research_and_sql_protection(database, monkeypatch):
    before = repo.reports_frame(database)
    rid = int(before.report_id.iloc[0])

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid requests must not reach backup")

    monkeypatch.setattr(repo, "backup_database", forbidden)
    with pytest.raises(ValueError, match="bestätigen"):
        repo.archive_report(rid, 1, reason="Test", db=database)
    for change in [repo.archive_report, repo.restore_report]:
        with pytest.raises(ValueError, match="Forschungsberichte"):
            change(rid, 1, confirmed=True, reason="Test", db=database)
    with pytest.raises(DBAPIError):
        with database.begin() as c:
            c.execute(
                text("UPDATE service_reports SET archived=true,version=version+1 WHERE id=:id"),
                {"id": rid},
            )
    pd.testing.assert_frame_equal(before, repo.reports_frame(database))
    assert len(repo.history(rid, database)) == 1


@pytest.mark.parametrize("restore", [False, True])
def test_failed_backup_prevents_archive_change(database, monkeypatch, restore):
    rid = repo.save_report(data(), db=database)
    if restore:
        repo.archive_report(rid, 1, confirmed=True, reason="Vorbereitung im Test", db=database)
    expected = 2 if restore else 1
    before = repo.reports_frame(database, archived=restore)
    history = repo.history(rid, database)

    def failed(*args, **kwargs):
        raise RuntimeError("Sicherung fehlgeschlagen")

    monkeypatch.setattr(repo, "backup_database", failed)
    change = repo.restore_report if restore else repo.archive_report
    with pytest.raises(RuntimeError, match="Sicherung"):
        change(rid, expected, confirmed=True, reason="Test", db=database)
    pd.testing.assert_frame_equal(before, repo.reports_frame(database, archived=restore))
    assert repo.history(rid, database) == history


def test_archived_reports_readonly_and_version_conflicts(database):
    rid = repo.save_report(data(), db=database)
    with pytest.raises(ValueError, match="inzwischen geändert"):
        repo.archive_report(rid, 0, confirmed=True, reason="Test", db=database)
    with pytest.raises(ValueError, match="Grund"):
        repo.archive_report(rid, 1, confirmed=True, db=database)
    repo.archive_report(rid, 1, confirmed=True, reason="Test", db=database)
    with pytest.raises(ValueError, match="schreibgeschützt"):
        repo.save_report(data(), rid, 2, db=database)
    with pytest.raises(ValueError, match="bereits"):
        repo.archive_report(rid, 2, confirmed=True, reason="Test", db=database)
    with pytest.raises(ValueError, match="inzwischen geändert"):
        repo.restore_report(rid, 1, confirmed=True, reason="Test", db=database)
    for sql_text in [
        "UPDATE service_reports SET description='tampered',version=version+1 WHERE id=:id",
        "UPDATE service_reports SET archived=false,description='tampered',version=version+1 WHERE id=:id",
    ]:
        with pytest.raises(DBAPIError):
            with database.begin() as c:
                c.execute(text(sql_text), {"id": rid})
    assert len(repo.history(rid, database)) == 2
    assert len(repo.reports_frame(database, archived=True)) == 1


def test_archive_ui_confirmation_statistics_and_restore(database, monkeypatch):
    from streamlit.testing.v1 import AppTest

    rid = repo.save_report(data(), db=database)
    original = repo.reports_frame(database, True)
    monkeypatch.setattr(repo, "engine", lambda: database)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception and app.metric[0].value == "47"
    app.button(key="open_edit_report_806279").click().run()
    # Forschungsberichte erhalten keinen Archivierungsknopf.
    assert not any(button.label == "Bericht archivieren" for button in app.button)
    app.selectbox(key="edit_report_806279").set_value(rid).run()
    app.button(key=f"open_archivieren_{rid}_1").click().run()
    next(b for b in app.button if b.label == "Archivierung bestätigen").click().run()
    assert app.error and app.metric[0].value == "47"
    assert not repo.reports_frame(database).archived.any()
    app.text_input(key=f"reason_archivieren_{rid}_1").set_value("UI-Testarchivierung")
    app.checkbox(key=f"confirmed_archivieren_{rid}_1").check()
    next(b for b in app.button if b.label == "Archivierung bestätigen").click().run()
    assert not app.exception and not app.error and app.metric[0].value == "46"
    assert app.selectbox(key="archived_report").value == rid
    app.button(key="open_edit_report_806279").click().run()
    assert rid not in repo.reports_frame(database).report_id.tolist()
    assert not any(
        "Bericht " + str(rid) + " ·" in option
        for option in app.selectbox(key="edit_report_806279").options
    )
    app.button(key=f"open_wiederherstellen_{rid}_2").click().run()
    app.text_input(key=f"reason_wiederherstellen_{rid}_2").set_value("UI-Testwiederherstellung")
    app.checkbox(key=f"confirmed_wiederherstellen_{rid}_2").check()
    next(b for b in app.button if b.label == "Wiederherstellung bestätigen").click().run()
    assert not app.exception and not app.error and app.metric[0].value == "47"
    assert repo.reports_frame(database, archived=True).empty
    assert len(repo.history(rid, database)) == 3
    pd.testing.assert_frame_equal(original, repo.reports_frame(database, True))


def test_archive_backup_can_restore_prechange_state(database, test_cluster, tmp_path):
    import os

    from scripts.prepare_database import run

    settings, _ = test_cluster
    rid = repo.save_report(data(), db=database)
    backup = repo.archive_report(
        rid, 1, confirmed=True, reason="Sicherungswiederherstellung prüfen", db=database
    )
    name = "servicepulse_archive_restore_" + uuid.uuid4().hex
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
            backup,
            env={**os.environ, "PGPASSWORD": settings["admin_password"]},
        )
        assert len(repo.reports_frame(restored)) == 47
        assert repo.reports_frame(restored, archived=True).empty
        assert len(repo.history(rid, restored)) == 1
    finally:
        restored.dispose()
        with psycopg.connect(**args) as c:
            c.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_archive_works_with_restricted_application_role(database, test_cluster):
    settings, _ = test_cluster
    with database.begin() as c:
        c.execute(text("GRANT USAGE ON SCHEMA public TO servicepulse_app"))
        c.execute(
            text(
                "GRANT SELECT,INSERT,UPDATE ON devices,categories,sources,service_reports,service_actions,measurement_files TO servicepulse_app"
            )
        )
        c.execute(text("GRANT SELECT,INSERT ON audit_log TO servicepulse_app"))
        c.execute(text("GRANT SELECT ON alembic_version TO servicepulse_app"))
        c.execute(text("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO servicepulse_app"))
    app = create_engine(
        connection_url(settings, database=database.url.database), hide_parameters=True
    )
    try:
        rid = repo.save_report(data(), db=app)
        repo.archive_report(rid, 1, confirmed=True, reason="App-Rollentest", db=app)
        repo.restore_report(rid, 2, confirmed=True, reason="App-Rollentest", db=app)
        assert len(repo.history(rid, app)) == 3
        with pytest.raises(DBAPIError):
            with app.begin() as c:
                c.execute(text("DELETE FROM service_reports WHERE id=:id"), {"id": rid})
    finally:
        app.dispose()


def test_archive_competes_safely_with_edit(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    rid = repo.save_report(data(), db=database)
    ready = Barrier(2)

    def change(kind):
        ready.wait(timeout=10)
        try:
            if kind == "archive":
                repo.archive_report(rid, 1, confirmed=True, reason="Paralleltest", db=database)
            else:
                values = data()
                values["description"] = "Parallele Teständerung"
                repo.save_report(values, rid, 1, db=database)
            return "saved"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(change, ["archive", "edit"])) == ["conflict", "saved"]
    assert len(repo.history(rid, database)) == 2
    with database.connect() as c:
        assert (
            c.execute(
                text("SELECT version FROM service_reports WHERE id=:id"), {"id": rid}
            ).scalar()
            == 2
        )


def test_archive_database_failure_rolls_back(database):
    rid = repo.save_report(data(), db=database)
    with database.begin() as c:
        c.execute(
            text("ALTER TABLE service_reports ADD CONSTRAINT test_no_archive CHECK (NOT archived)")
        )
    try:
        with pytest.raises(DBAPIError):
            repo.archive_report(rid, 1, confirmed=True, reason="Rollback-Test", db=database)
        assert len(repo.reports_frame(database)) == 47
        assert repo.reports_frame(database, archived=True).empty
        assert len(repo.history(rid, database)) == 1
    finally:
        with database.begin() as c:
            c.execute(text("ALTER TABLE service_reports DROP CONSTRAINT test_no_archive"))


def test_upgrade_existing_0003_preserves_reports_and_audit(test_cluster):
    from alembic import command
    from alembic.config import Config

    from servicepulse.database import backup_database

    settings, _ = test_cluster
    name = "servicepulse_migration_test_" + uuid.uuid4().hex
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
    legacy = create_engine(connection_url(settings, True, database=name), hide_parameters=True)
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        with legacy.begin() as c:
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "0003")
            c.execute(
                text("INSERT INTO devices (id,name,model,location) VALUES ('999993','','','')")
            )
            c.execute(text("INSERT INTO categories (id,code) VALUES (1,'Legacy')"))
            c.execute(
                text(
                    "INSERT INTO sources (id,kind,name,details) VALUES (1,'manual','Migrationstest','{}'::jsonb)"
                )
            )
            c.execute(
                text(
                    "INSERT INTO service_reports (device_id,category_id,source_id,description,component,status,notes,origin,import_key,version) VALUES ('999993',1,1,'Legacy-Bericht','','offen','','manual','manual:legacy',1)"
                )
            )
        with legacy.connect() as c:
            before_report = c.execute(text("SELECT to_jsonb(t) FROM service_reports t")).scalar()
            before_audit = c.execute(text("SELECT to_jsonb(t) FROM audit_log t")).scalar()
        snapshot = backup_database(legacy)
        assert snapshot.exists()
        migrate(legacy)
        with legacy.connect() as c:
            after_report = c.execute(text("SELECT to_jsonb(t) FROM service_reports t")).scalar()
            assert after_report.pop("archived") is False
            assert before_report == after_report
            assert before_audit == c.execute(text("SELECT to_jsonb(t) FROM audit_log t")).scalar()
            assert c.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0004"
        assert len(repo.reports_frame(legacy)) == 1
    finally:
        legacy.dispose()
        with psycopg.connect(**args) as c:
            c.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
