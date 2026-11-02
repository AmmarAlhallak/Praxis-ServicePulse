"""Deutschsprachige Geräte- und Berichtverwaltung für die bestehende App."""

from __future__ import annotations

import uuid

import pandas as pd
import streamlit as st

from servicepulse import repository as repo
from servicepulse.presentation import CATEGORIES, category_label, fault_label


def report_table(frame: pd.DataFrame) -> None:
    """Zeigt Berichte getrennt nach Herkunft und kennzeichnet nicht dokumentierte Angaben."""
    columns = ["device_id", "event_date", "category", "fault_text", "status", "origin", "action"]
    view = frame[columns].copy()
    view.event_date = view.event_date.dt.strftime("%d.%m.%Y").fillna("Nicht angegeben")
    view.category = view.category.map(category_label)
    view.fault_text = [
        fault_label(r.fault_text) if r.origin == "research" else (r.fault_text or "Nicht angegeben")
        for r in frame.itertuples()
    ]
    historical = view.origin.eq("research")
    view.loc[historical & view.action.fillna("").str.strip().eq(""), "action"] = (
        "Nicht dokumentiert"
    )
    view.loc[
        historical & view.status.fillna("").str.strip().isin(["", "nicht angegeben"]), "status"
    ] = "Nicht dokumentiert"
    view.origin = view.origin.map(
        {"research": "Veröffentlichte Forschungsdaten", "manual": "Selbst erfasst"}
    )
    view = view.rename(
        columns={
            "device_id": "Geräte-ID",
            "event_date": "Servicedatum",
            "category": "Fehlerkategorie",
            "fault_text": "Beschreibung",
            "status": "Status",
            "origin": "Herkunft",
            "action": "Maßnahme",
        }
    )
    if "report_version" in frame:
        view.loc[historical & frame.report_version.gt(1), "Herkunft"] = (
            "Forschungsdaten · Arbeitsfassung"
        )
    st.dataframe(view, hide_index=True, width="stretch")


def report_form(device: str, frame: pd.DataFrame) -> None:
    """Zeigt ein geschlossenes Anlageformular oder eine versionierte Bearbeitung mit Historie."""
    panel_key = f"report_panel_{device}"
    open_key = f"new_report_open_{device}"
    new_area, edit_area = st.columns(2)
    with new_area:
        if st.button(
            "Neuen Servicebericht erfassen", key=f"open_new_report_{device}", type="primary"
        ):
            st.session_state[panel_key] = "new"
    with edit_area:
        if st.button("Bericht bearbeiten", key=f"open_edit_report_{device}", disabled=frame.empty):
            st.session_state[panel_key] = "edit"
    mode = st.session_state.get(panel_key)
    if mode not in {"new", "edit"}:
        return
    editing = mode == "edit"
    if st.button("Formular schließen", key=f"close_new_report_{device}"):
        st.session_state.pop(panel_key, None)
        st.rerun()
    existing = None
    rid = None
    if editing:
        if frame.empty:
            st.info("Für dieses Gerät ist noch kein Servicebericht gespeichert.")
            return
        rid = st.selectbox(
            "Bericht auswählen",
            frame.report_id.tolist(),
            format_func=lambda i: (
                f"Bericht {i} · "
                + (
                    "Ohne Datum"
                    if pd.isna(frame.loc[frame.report_id.eq(i), "event_date"].iloc[0])
                    else frame.loc[frame.report_id.eq(i), "event_date"].iloc[0].strftime("%d.%m.%Y")
                )
            ),
            key=f"edit_report_{device}",
        )
        existing = frame.loc[frame.report_id.eq(rid)].iloc[0]
        token = f"edit_version_{rid}"
        expected = st.session_state.setdefault(token, int(existing.report_version))
        if st.button("Aktuellen Bericht neu laden", key=f"reload_{rid}"):
            st.session_state.pop(token, None)
            st.session_state[f"form_generation_{rid}"] = (
                st.session_state.get(f"form_generation_{rid}", 0) + 1
            )
            st.rerun()
        if existing.origin == "research":
            st.warning(
                "Historischer Forschungsbericht: Das Original ist schreibgeschützt. Änderungen werden ausschließlich als Arbeitsfassung gespeichert und protokolliert."
            )
        with st.expander("Originalwerte und Änderungshistorie (schreibgeschützt)"):
            for entry in repo.history(rid):
                st.markdown(f"**Version {entry['Version']} · {entry['Grund']}**")
                st.caption(f"{entry['Zeitpunkt']:%d.%m.%Y %H:%M %Z} · {entry['Bearbeiter']}")
                st.json({"Vorher": entry["Vorher"], "Nachher": entry["Nachher"]}, expanded=False)
        if existing.origin == "research" and not st.checkbox(
            "Arbeitsfassung dieses Forschungsberichts bearbeiten",
            key=f"enable_research_edit_{device}_{rid}",
        ):
            return
        if existing.origin == "manual":
            archive_controls(existing, expected_version=expected)
    else:
        expected = None
    suffix = f"{device}_{rid}_{st.session_state.get(f'form_generation_{rid}', 0)}"

    def form_value(key: str, default=""):
        return existing[key] if existing is not None else default

    category_options = sorted(
        set(CATEGORIES) | set(frame.category) | {"Unbekannt"}, key=category_label
    )
    current = form_value("category", "Unbekannt")
    with st.form(f"report_form_{suffix}"):
        st.caption(
            "Nur Gerät und Herkunft sind erforderlich. Leere Angaben bleiben ausdrücklich „nicht angegeben“; es werden keine Messdaten erzeugt."
        )
        day = st.date_input(
            "Servicedatum",
            value=None
            if existing is None or pd.isna(existing.event_date)
            else existing.event_date.date(),
            format="DD.MM.YYYY",
            key=f"report_date_{suffix}",
        )
        cat = st.selectbox(
            "Fehlerkategorie",
            category_options,
            index=category_options.index(current),
            format_func=category_label,
            key=f"report_category_{suffix}",
        )
        description = st.text_area(
            "Beschreibung der Störung",
            value=form_value("fault_text"),
            key=f"report_description_{suffix}",
            help="Freitext; die originale englische Beschreibung eines Forschungsberichts bleibt zusätzlich unverändert erhalten.",
        )
        component = st.text_input(
            "Betroffene Komponente (optional)",
            value=form_value("component"),
            key=f"report_component_{suffix}",
        )
        action = st.text_area(
            "Reparatur oder Wartungsmaßnahme (optional)",
            value=form_value("action"),
            key=f"report_action_{suffix}",
            placeholder="Nicht dokumentiert" if editing and existing.origin == "research" else None,
        )
        status = st.selectbox(
            "Status",
            repo.STATUSES,
            index=repo.STATUSES.index(form_value("status", "offen")),
            key=f"report_status_{suffix}",
            format_func=lambda v: (
                "Nicht dokumentiert"
                if editing and existing.origin == "research" and v == "nicht angegeben"
                else v
            ),
        )
        notes = st.text_area(
            "Bemerkungen (optional)", value=form_value("notes"), key=f"report_notes_{suffix}"
        )
        source = st.text_input(
            "Quelle / Herkunft",
            value=form_value("source_file"),
            disabled=editing,
            key=f"report_source_{suffix}",
            help="Zum Beispiel eigener Wartungsbericht. Wenn unbekannt: „Nicht bekannt“. Die Erstquelle bleibt bei Bearbeitungen erhalten; Ergänzungen gehören in Bemerkungen.",
        )
        actor = st.text_input("Bearbeiter (optional)", key=f"report_actor_{suffix}")
        reason = st.text_input(
            "Grund der Änderung",
            value="" if editing else "Neuer Servicebericht",
            key=f"report_reason_{suffix}",
        )
        save_label = "Servicebericht speichern"
        if editing:
            save_label = (
                "Arbeitsfassung speichern"
                if existing.origin == "research"
                else "Änderungen speichern"
            )
        submitted = st.form_submit_button(save_label, type="primary")
    if submitted:
        try:
            request = st.session_state.setdefault("report_request", str(uuid.uuid4()))
            saved = repo.save_report(
                dict(
                    device_id=device,
                    service_date=day,
                    category=cat,
                    description=description,
                    component=component,
                    action=action,
                    status=status,
                    notes=notes,
                    source=source,
                    actor=actor,
                    reason=reason,
                ),
                rid,
                expected,
                request,
            )
            st.session_state.pop("report_request", None)
            if editing:
                st.session_state.pop(f"edit_version_{rid}", None)
            st.session_state[f"form_generation_{rid}"] = (
                st.session_state.get(f"form_generation_{rid}", 0) + 1
            )
            st.session_state.pop(panel_key, None)
            if not editing:
                st.session_state[open_key] = False
            st.session_state["saved_report"] = saved
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Der Bericht wurde nicht gespeichert. Bitte Datenbankverbindung prüfen und erneut versuchen."
            )


def render(df: pd.DataFrame, files: pd.DataFrame, devices: pd.DataFrame) -> None:
    """Zeigt Geräte, gespeicherte Berichte und kontrollierte Eingaben für die Verwaltung."""
    st.subheader("Geräte und Service einfach verwalten")
    if "archive_notice" in st.session_state:
        st.success(st.session_state.pop("archive_notice"))
    if "saved_report" in st.session_state:
        st.success(
            f"Bericht {st.session_state.pop('saved_report')} wurde dauerhaft gespeichert. Historie und Statistiken sind aktualisiert."
        )
    search = st.text_input(
        "Gerät suchen",
        placeholder="Geräte-ID, Bezeichnung, Modell oder Standort",
        key="device_search",
    )
    counts = df.groupby("device_id").size()
    listing = devices.copy()
    listing["Serviceberichte"] = listing["Geräte-ID"].map(counts).fillna(0).astype(int)
    listing["Messdaten"] = (
        listing["Geräte-ID"]
        .isin(set(files.device_id))
        .map({True: "Vorhanden", False: "Keine vorhanden"})
    )
    if search.strip():
        listing = listing[
            listing.astype(str)
            .apply(lambda c: c.str.contains(search.strip(), case=False, regex=False))
            .any(axis=1)
        ]
    listing[["Bezeichnung", "Modell", "Standort"]] = (
        listing[["Bezeichnung", "Modell", "Standort"]]
        .replace(r"^\s*$", "Nicht dokumentiert", regex=True)
        .fillna("Nicht dokumentiert")
    )
    st.caption("Durchsuchbare Geräteliste. Zum Öffnen unten eine Geräte-ID auswählen.")
    st.dataframe(listing, hide_index=True, width="stretch", height=250)
    with st.expander("Neues Gerät anlegen"):
        with st.form("new_device"):
            identifier = st.text_input("Geräte-ID (6 Ziffern)", key="new_device_id")
            name = st.text_input("Bezeichnung (optional)", key="new_device_name")
            model = st.text_input("Modell (optional)", key="new_device_model")
            location = st.text_input("Standort (optional)", key="new_device_location")
            add = st.form_submit_button("Gerät anlegen")
        if add:
            try:
                repo.add_device(identifier.strip(), name, model, location)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    if listing.empty:
        st.info("Kein Gerät zur Suche gefunden. Suche ändern oder ein neues Gerät anlegen.")
        render_archive()
        return
    options = listing["Geräte-ID"].tolist()
    device = st.selectbox(
        "Gerät aus der Liste öffnen",
        options,
        index=options.index("806279") if "806279" in options else 0,
        key="managed_device",
    )
    details = listing.loc[listing["Geräte-ID"].eq(device)].iloc[0]
    st.caption(
        f"Geöffnetes Gerät: {device} · Bezeichnung: {details.Bezeichnung} · Modell: {details.Modell} · Standort: {details.Standort}"
    )
    own = df[df.device_id.eq(device)]
    st.markdown("#### Bisherige Serviceberichte")
    if own.empty:
        st.info("Für dieses Gerät ist noch kein Servicebericht dokumentiert.")
    else:
        report_table(own.sort_values("event_date", ascending=False, na_position="last"))
        repeated = own.category.value_counts()
        repeated = repeated[repeated > 1]
        if not repeated.empty:
            st.write(
                "Mehrfach dokumentiert: "
                + ", ".join(f"{category_label(k)} ({v} Einträge)" for k, v in repeated.items())
                + ". Das sind nicht automatisch unabhängige Ausfälle."
            )
    st.markdown("#### Verfügbare Betriebsdaten")
    data = files[files.device_id.eq(device)]
    if data.empty:
        st.info(
            "Für dieses Gerät sind keine Messdaten registriert. Ein Servicebericht erzeugt keine Sensordaten."
        )
    else:
        st.write(
            f"{len(data)} Mess- oder Meldungsdateien verfügbar. Die Betriebsanalyse bietet eine eigene Geräte- und Zeitraumwahl."
        )
        if st.button("Dieses Gerät für die Betriebsanalyse auswählen"):
            st.session_state["measurement_device"] = device
            st.success("Gerät ausgewählt. Öffne „Betriebsanalyse & Vergleiche“.")
    with st.expander("Ähnliche dokumentierte Fälle bei anderen Geräten"):
        similar = df[df.category.isin(own.category) & df.device_id.ne(device)]
        if similar.empty:
            st.info("Keine weiteren Einträge derselben Kategorien vorhanden.")
        else:
            report_table(similar)
        st.caption(
            "Ähnlichkeit bedeutet hier dieselbe Kategorie; sie belegt weder dieselbe Ursache noch vergleichbare Betriebsbedingungen."
        )
    st.markdown("#### Bericht erfassen oder bearbeiten")
    report_form(device, own)
    render_archive()


def archive_controls(report: pd.Series, *, expected_version: int, restore: bool = False) -> None:
    """Verlangt eine ausdrückliche, berichtsbezogene Bestätigung vor jeder Archivänderung."""
    if report.origin != "manual":
        return
    rid = int(report.report_id)
    operation = "wiederherstellen" if restore else "archivieren"
    token = f"{operation}_{rid}_{expected_version}"
    pending = f"pending_{token}"
    if st.button(f"Bericht {operation}", key=f"open_{token}"):
        st.session_state[pending] = True
    if not st.session_state.get(pending):
        return
    st.warning(
        f"Eigenen Bericht {rid} für Gerät {report.device_id} {operation}? "
        + (
            "Er erscheint danach wieder in den normalen Auswertungen."
            if restore
            else "Er wird aus normalen Auswertungen und Historien entfernt und bleibt im Archiv wiederherstellbar."
        )
    )
    with st.form(f"confirm_{token}"):
        reason = st.text_input("Grund", key=f"reason_{token}")
        actor = st.text_input("Bearbeiter (optional)", key=f"actor_{token}")
        confirmed = st.checkbox(
            f"Ich bestätige: Bericht {rid} für Gerät {report.device_id} {operation}.",
            key=f"confirmed_{token}",
        )
        submitted = st.form_submit_button(
            "Wiederherstellung bestätigen" if restore else "Archivierung bestätigen"
        )
    if st.button("Abbrechen", key=f"cancel_{token}"):
        st.session_state.pop(pending, None)
        st.rerun()
    if submitted:
        try:
            change = repo.restore_report if restore else repo.archive_report
            change(rid, int(expected_version), confirmed=confirmed, reason=reason, actor=actor)
            st.session_state.pop(pending, None)
            st.session_state.pop(f"report_panel_{report.device_id}", None)
            st.session_state.pop(f"edit_version_{rid}", None)
            st.session_state["archive_notice"] = (
                f"Bericht {rid} wurde "
                + ("wiederhergestellt." if restore else "archiviert.")
                + " Sicherung und Änderungsprotokoll sind vorhanden."
            )
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Archivstatus konnte nicht geändert werden. Bitte neu laden und die Datenbankverbindung prüfen."
            )


def render_archive() -> None:
    """Zeigt archivierte eigene Berichte getrennt von normalen Servicehistorien."""
    with st.expander("Archivierte Serviceberichte"):
        archived = repo.reports_frame(archived=True)
        if archived.empty:
            st.caption("Keine archivierten Serviceberichte vorhanden.")
            return
        report_table(archived)
        rid = st.selectbox(
            "Archivierten Bericht öffnen",
            archived.report_id.tolist(),
            key="archived_report",
            format_func=lambda value: (
                f"Bericht {value} · Gerät {archived.loc[archived.report_id.eq(value), 'device_id'].iloc[0]}"
            ),
        )
        report = archived.loc[archived.report_id.eq(rid)].iloc[0]
        st.caption("Änderungsprotokoll einschließlich Archivierung und Wiederherstellung")
        st.json(repo.history(int(rid)), expanded=False)
        archive_controls(report, expected_version=int(report.report_version), restore=True)
