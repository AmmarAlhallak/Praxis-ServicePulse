"""Gezielte Regressionen aus dem Review, ohne Schreiben in den Nutzbestand."""

import io
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from servicepulse import repository as repo
from servicepulse.imports import import_parquet
from servicepulse.measurements import inspect_file

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("function", ["reports_frame", "files_frame"])
def test_database_outage_is_understandable(monkeypatch, function):
    def unavailable(*args, **kwargs):
        raise OperationalError("test query", {}, Exception("isolierte Verbindungsunterbrechung"))

    monkeypatch.setattr(repo, function, unavailable)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert any("Datenbank ist nicht erreichbar" in error.value for error in app.error)


def test_timezone_aware_upload_requires_explicit_policy(tmp_path):
    frame = pd.DataFrame(
        {"Datetime": pd.date_range("2022-01-01", periods=2, tz="UTC"), "RTD": [-80.0, -79.0]}
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    with pytest.raises(ValueError, match="Zeitstempel mit Zeitzone"):
        import_parquet(buffer.getvalue(), "123456_temp.parquet", tmp_path)
    assert not list(tmp_path.iterdir())
    file = tmp_path / "123456_temp.parquet"
    file.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError, match="Zeitstempel mit Zeitzone"):
        inspect_file(file)


def test_database_configuration_errors_do_not_fall_back(monkeypatch):
    import servicepulse.database as db

    monkeypatch.setattr(db, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("SERVICEPULSE_DATABASE_URL", raising=False)
    db.engine.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="noch nicht eingerichtet"):
            db.engine()
        monkeypatch.setenv("SERVICEPULSE_DATABASE_URL", "sqlite:///not_used.db")
        with pytest.raises(ValueError, match="PostgreSQL"):
            db.engine()
    finally:
        db.engine.cache_clear()


def test_history_database_outage_has_no_unhandled_exception(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OperationalError("history test", {}, Exception("NEVER_DISPLAY_TEST_PASSWORD"))

    monkeypatch.setattr(repo, "history", unavailable)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.radio(key="report_mode").set_value("Bestehenden Bericht bearbeiten").run()
    assert not app.exception
    assert any("Datenbank ist nicht erreichbar" in error.value for error in app.error)
    assert all("NEVER_DISPLAY_TEST_PASSWORD" not in code.value for code in app.code)


def test_test_proof_tracks_nested_ui_modules(tmp_path):
    import os

    from servicepulse.research import read_test_report

    (tmp_path / "docs").mkdir()
    (tmp_path / "servicepulse/ui").mkdir(parents=True)
    module = tmp_path / "servicepulse/ui/operation.py"
    module.write_text("# synthetic module")
    (tmp_path / "app.py").write_text("# synthetic entry point")
    proof = tmp_path / "docs/testlauf_review.xml"
    proof.write_text(
        '<testsuites><testsuite tests="3" failures="0" errors="0" skipped="0" /></testsuites>'
    )
    os.utime(tmp_path / "app.py", (100, 100))
    os.utime(module, (100, 100))
    os.utime(proof, (200, 200))
    assert read_test_report(tmp_path)["passed"] == 3
    os.utime(module, (300, 300))
    assert read_test_report(tmp_path) is None
