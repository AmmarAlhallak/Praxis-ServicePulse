"""Validierenden Messdatei-Import getrennt von der Betriebsanalyse anzeigen."""

from pathlib import Path

import pandas as pd
import streamlit as st

from servicepulse import repository as repo
from servicepulse.imports import import_parquet
from servicepulse.ui.common import technical_error


def render_imports(files: pd.DataFrame, root: Path) -> None:
    """Zeigt den bestehenden Import mit Herkunftsprüfung und Überschreibschutz."""
    with st.expander("Datenverwaltung · Weitere Messdateien importieren"):
        st.write(
            f"Es sind bereits **{len(files)} veröffentlichte bzw. lokal ergänzte Messdateien** verfügbar. Im geprüften Forschungsbestand sind es 106. Für die normale Nutzung ist kein erneuter Import nötig."
        )
        st.caption(
            "Parquet ist das Dateiformat der Betriebsmessdaten. Nur zum Ergänzen weiterer Dateien verwenden. Vorhandene Dateien werden nicht überschrieben."
        )
        st.markdown(
            "Dateiname beispielsweise `806279_temp.parquet` für Messwerte oder `806279_events.parquet` für Meldungen. Herkunft und Lizenz zusätzlicher Dateien separat dokumentieren. Temperaturdateien müssen bereits zeitkorrigiert sein, Meldungsdateien die interne Gerätezeit der Autorenpipeline verwenden."
        )
        upload_source = st.text_input(
            "Herkunft und Nutzungsrecht der Messdatei",
            key="measurement_source",
            help="Bitte Quelle und Berechtigung zur Nutzung dokumentieren.",
        )
        upload = st.file_uploader(
            "Messdatei auswählen (Parquet, höchstens 300 MB)", type="parquet", key="parquet_upload"
        )
        if upload is not None and st.button("Datei prüfen und importieren", key="import_parquet"):
            try:
                destination, digest = import_parquet(
                    upload.getvalue(),
                    upload.name,
                    root / "data/raw/imported",
                    registry=repo.file_digests(),
                    source=upload_source,
                )
                try:
                    repo.register_file(destination, upload_source)
                except Exception:
                    destination.unlink()
                    raise
                st.session_state["import_success"] = destination.name
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(
                    "Die Datei konnte nicht gespeichert werden. Bitte Speicherplatz und Schreibrechte prüfen."
                )
                technical_error(exc)
        if "import_success" in st.session_state:
            st.success(
                f"Datei erfolgreich geprüft und übernommen: {st.session_state.pop('import_success')}"
            )
        st.caption(
            "Größere Dateien nach der lokalen Importanleitung in docs/datenimport.md direkt nach data/raw/<Modell>/ kopieren. Danach den Qualitätsbericht neu erstellen."
        )
