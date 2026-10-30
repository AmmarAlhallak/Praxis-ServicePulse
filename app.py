"""ServicePulse starten und die vier bestehenden Bereiche zusammenführen."""

from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from servicepulse import repository as repo
from servicepulse.database import ROOT
from servicepulse.faults import compare_reference
from servicepulse.management import render as render_management
from servicepulse.ui.common import database_problem
from servicepulse.ui.operation import render_operation
from servicepulse.ui.overview import render_overview
from servicepulse.ui.quality import render_quality
from servicepulse.ui.shell import configure_page, render_service_filters

configure_page()
st.caption("SERVICEPULSE  /  ANALYSE VON ULTRATIEFKÜHLGERÄTEN")
st.title("Kälteanlagen im Blick.")
st.write("Geräte verwalten, Service dokumentieren und Betriebsdaten nachvollziehbar untersuchen.")
try:
    reports = repo.reports_frame()
    originals = repo.reports_frame(originals=True)
    devices = repo.devices_frame()
    files = repo.files_frame()
except Exception as exc:
    database_problem(exc)
    st.stop()
file_errors = [
    {"path": path, "error": "Registrierte Datei fehlt lokal"}
    for path in files.path
    if not Path(path).exists()
]
files = files.loc[files.path.map(lambda path: Path(path).exists()).astype(bool)].copy()
reference = ROOT / "research/reference/data/raw_data/other_data/freezer_faults.csv"
comparison = compare_reference(originals, reference) if reference.exists() else None
conflicts = (
    comparison[comparison.reference_status.ne("Übereinstimmung")]
    if comparison is not None
    else None
)
selected = render_service_filters(reports, files)
overview, management, operation, quality = st.tabs(
    [
        "Übersicht",
        "Geräte & Serviceberichte",
        "Betriebsanalyse & Vergleiche",
        "Datenqualität & Forschung",
    ]
)
with overview:
    render_overview(reports, selected, devices)
with management:
    try:
        render_management(reports, files, devices)
    except SQLAlchemyError as exc:
        database_problem(exc)
with operation:
    render_operation(reports, selected, files, devices, ROOT)
with quality:
    render_quality(ROOT, reports, originals, files, file_errors, conflicts)
