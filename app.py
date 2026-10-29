"""ServicePulse – lokal starten mit python -m streamlit run app.py."""
from pathlib import Path
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st
from servicepulse.faults import read_faults, metrics, quality, filter_faults, compare_reference, category_control
from servicepulse.measurements import inventory, numeric_columns, series_window, window_comparison, event_window, offsets, time_bounds

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='ServicePulse', page_icon='❄', layout='wide')
st.markdown('''<style>.stApp {background: #f5f8fc;} h1,h2,h3 {color:#142a43;}
    [data-testid="stMetric"] {background:white;border:1px solid #dce5ef;border-radius:12px;padding:18px;}
    .block-container {padding-top:2rem;} </style>''', unsafe_allow_html=True)

@st.cache_data
def load_excel(path, modified):
    return read_faults(path)

st.caption('SERVICEPULSE  /  WISSENSCHAFTLICHER PROTOTYP')
st.title('Betrieb verstehen. Störungen einordnen.')
st.write('Historische Serviceeinträge und reale Messreihen von Ultratiefkühlgeräten · DTU / Danish National Biobank')
try:
    source = ROOT / 'fault_summary_R1.xlsx'
    df = load_excel(str(source), source.stat().st_mtime_ns)
except Exception as exc:
    st.error(f'Excel konnte nicht eingelesen werden: {exc}')
    st.stop()

files, file_errors = inventory(ROOT / 'data/raw')
with st.sidebar:
    st.header('Analyse eingrenzen')
    st.caption('Eine leere Auswahl liefert keine Einträge. „Alle Filter zurücksetzen“ stellt alles wieder her.')
    if st.button('Alle Filter zurücksetzen'):
        for key in ['devices','categories','date_range','include_undated']:
            st.session_state.pop(key, None)
        st.rerun()
    with st.expander('Geräte auswählen', expanded=False):
        devices = st.multiselect('Geräte', sorted(df.device_id.dropna().unique()), default=sorted(df.device_id.dropna().unique()), key='devices')
    with st.expander('Kategorien auswählen', expanded=False):
        categories = st.multiselect('Kategorien (Originalgruppen)', sorted(df.category.unique()), default=sorted(df.category.unique()), key='categories')
    dated = df.event_date.dropna()
    date_range = st.date_input('Registrierungszeitraum', (dated.min().date(), dated.max().date()), key='date_range') if len(dated) else ()
    include_undated = st.checkbox('Einträge ohne gültiges Datum einbeziehen', value=True, key='include_undated')
    st.divider()
    st.caption(f'Quelle: {source.name} · {len(df)} Einträge\n\nMessdateien: {len(files)} · keine Ausfallprognose')

filtered = filter_faults(df, devices, categories)
if len(date_range) == 2:
    dated_rows = filter_faults(filtered, start=date_range[0], end=date_range[1])
    filtered = pd.concat([dated_rows, filtered[filtered.event_date.isna()]]) if include_undated else dated_rows
elif len(date_range) == 1:
    st.info('Bitte ein Enddatum auswählen. Bis dahin bleibt der Zeitraum ungefiltert.')
m = metrics(filtered)
cols = st.columns(4)
for col, (label, value) in zip(cols, [('Serviceeinträge', m['entries']), ('Betroffene Geräte', m['devices']), ('Geräte mit mehreren Einträgen', m['devices_multiple_entries']), ('Wiederholte Gerät/Kategorie-Paare', m['repeated_device_category_pairs'])]):
    col.metric(label, value)
st.caption('Ein Serviceeintrag ist kein nachgewiesener unabhängiger Ausfall. Wiederholungen können denselben ungelösten Zustand betreffen.')

overview, categories_tab, devices_tab, time_tab, data_tab, method_tab = st.tabs(['Übersicht','Fehlerkategorien','Geräteanalyse','Zeitliche Verläufe','Datenqualität','Methodik & Quellen'])

def bar_counts(frame, column, label, key):
    counts = frame[column].value_counts().rename_axis(label).reset_index(name='Einträge')
    if len(counts):
        st.plotly_chart(px.bar(counts, x='Einträge', y=label, orientation='h', color_discrete_sequence=['#137e97']).update_layout(yaxis={'categoryorder':'total ascending'}, template='plotly_white'), width='stretch', key=key)
    else:
        st.info('Keine Einträge für diese Auswahl.')

with overview:
    left,right = st.columns([3,2])
    with left:
        st.subheader('Dokumentierte Kategorien')
        bar_counts(filtered, 'category_group', 'Kategorie', 'overview_categories')
    with right:
        st.subheader('Was die Daten beschreiben')
        st.write('Ausgewertet werden dokumentierte Serviceeinträge. Gerätealarme und Türöffnungen bilden eine eigene Datenquelle. Die Stichprobe erlaubt deskriptive Vergleiche, keine belastbaren Ausfallwahrscheinlichkeiten.')
        st.info('„No fix“ bleibt in den Originalgruppen erhalten. „Data missing“ bezeichnet eine Autorenkategorie und ist kein leerer Excel-Wert.')
        st.write(f'Registrierungsdaten ohne Uhrzeit: {len(filtered)}. Ereignismarkierungen zeigen den gesamten Kalendertag.')
    st.subheader('Ausgewählte Einträge')
    st.dataframe(filtered[['device_id','event_date','fault_text','category','source_row']], hide_index=True, width='stretch')
    st.download_button('Auswahl als CSV herunterladen', filtered.to_csv(index=False).encode('utf-8-sig'), file_name='servicepulse_serviceeintraege.csv', mime='text/csv')

with categories_tab:
    st.subheader('Originalkategorien und Gruppierung')
    grouped = st.toggle('„No fix“ für die Häufigkeitsdarstellung zusammenfassen', value=False)
    bar_counts(filtered, 'category_group' if grouped else 'category', 'Kategorie', 'fault_categories')
    st.caption('Berechnung aus den einzelnen Einträgen; das zweite Excel-Blatt wird als Kontrolltabelle behandelt.')

with devices_tab:
    st.subheader('Einträge je Gerät')
    bar_counts(filtered, 'device_id', 'Gerät', 'device_counts')
    repeated = filtered.groupby(['device_id','category']).size().reset_index(name='Einträge')
    st.write('Mehrere Einträge derselben Kategorie am selben Gerät')
    st.dataframe(repeated[repeated['Einträge'] > 1], hide_index=True, width='stretch')
    st.caption('Keine Interpretation als Rezidiv oder neuer unabhängiger Ausfall ohne Prüfung der Serviceberichte.')

with time_tab:
    st.subheader('Registrierungen im Zeitverlauf')
    timeline = filtered.dropna(subset=['event_date']).assign(Monat=lambda x:x.event_date.dt.to_period('M').astype(str)).groupby('Monat').size().reset_index(name='Einträge')
    if len(timeline):
        st.plotly_chart(px.bar(timeline, x='Monat', y='Einträge', color_discrete_sequence=['#137e97']), width='stretch', key='service_timeline')
    st.subheader('Reale Betriebsdaten')
    if files.empty:
        st.info('Keine lesbaren Parquet-Dateien vorhanden. Excel-Auswertungen sind verfügbar. Import und Downloadanleitung siehe unten und docs/datenimport.md.')
    else:
        temps = files[files.kind.eq('temp')]
        options = sorted(temps.device_id.unique())
        if options:
            preferred = '806279' if '806279' in options else options[0]
            device = st.selectbox('Messgerät (gesamter Messdatenbestand)', options, index=options.index(preferred))
            matches = temps[temps.device_id.eq(device)]
            selected_path = st.selectbox('Messdatei', matches.path.tolist())
            path = Path(selected_path)
            numeric = numeric_columns(path)
            measure = st.selectbox('Messgröße', numeric, index=numeric.index('RTD') if 'RTD' in numeric else 0)
            candidates = filtered[filtered.device_id.eq(device) & filtered.event_date.notna()]
            mode = st.radio('Zeitraum', ['Um Serviceeintrag', 'Freier Zeitraum'], horizontal=True)
            chosen_date = None
            if mode == 'Um Serviceeintrag' and not candidates.empty:
                candidate_ids = candidates.index.tolist()
                leak_ids = candidates[candidates.category.eq('Refrigerant leakage')].index.tolist()
                row_id = st.selectbox('Serviceeintrag', candidate_ids, index=candidate_ids.index(leak_ids[0]) if leak_ids else 0, format_func=lambda i:f'{df.loc[i,"event_date"]:%d.%m.%Y} · {df.loc[i,"fault_text"]}')
                chosen_date = df.loc[row_id,'event_date']
                days = st.slider('Tage vor und nach dem Ereignistag', 1, 30, 7)
                start, end = chosen_date-pd.Timedelta(days=days), chosen_date+pd.Timedelta(days=days+1)
                if device == '806031' and chosen_date == pd.Timestamp('2023-02-03'):
                    st.warning('Datumswiderspruch: Excel 03.02.2023, Autoren-CSV und Auftragsdatum im Servicebericht 02.03.2023. Excel wurde nicht automatisch korrigiert.')
            if device == '806018':
                st.warning('Gerätezuordnung ungeklärt: Die Rohdatenstichprobe Oktober 2022 im Ordner 806018 nennt Unit Name 806022. Die veröffentlichte Parquet-Zuordnung wurde beibehalten; keine gesicherte Geräteidentität behauptet.')
            if mode != 'Um Serviceeintrag' or candidates.empty:
                if mode == 'Um Serviceeintrag':
                    st.info('Kein Serviceeintrag für dieses Gerät in der aktuellen Auswahl. Freien Zeitraum verwenden.')
                first_time, last_time = time_bounds(path)
                last_day = pd.Timestamp(last_time).normalize() if last_time is not None else pd.Timestamp('2023-04-01')
                first_day = max(pd.Timestamp(first_time).normalize(), last_day-pd.Timedelta(days=6)) if first_time is not None else last_day
                dates = st.date_input('Messzeitraum', (first_day.date(), last_day.date()))
                start = pd.Timestamp(dates[0]) if len(dates) else pd.Timestamp('2023-04-01')
                end = pd.Timestamp(dates[-1])+pd.Timedelta(days=1) if len(dates) else start+pd.Timedelta(days=1)
            bucket = st.selectbox('Darstellungsintervall', ['hour','day','minute'], format_func=lambda v:{'hour':'Stunde','day':'Tag','minute':'Minute'}[v])
            if (end-start).days > 366 and bucket == 'minute':
                st.warning('Minutenansicht auf maximal 366 Tage begrenzt. Zeitraum verkleinern oder Stunden wählen.')
            else:
                try:
                    curve = series_window(path, measure, start, end, bucket)
                    if curve.empty:
                        st.warning('Keine Messwerte in diesem Zeitraum. Keine Zuordnung zu entfernten Messpunkten vorgenommen.')
                    else:
                        figure = px.line(curve, x='time', y=['mean','minimum','maximum'], labels={'value':measure,'time':'Zeit (Quellenzeit ohne Zeitzone)','variable':'Aggregation'}, color_discrete_sequence=['#137e97','#b6cbd8','#dc9253'])
                        # Explizite NaN-Punkte verhindern Linien über längere Messlücken.
                        for trace in figure.data:
                            frequency = {'minute':'min','hour':'h','day':'D'}[bucket]
                            series = pd.Series(trace.y, index=pd.DatetimeIndex(trace.x)).asfreq(frequency)
                            trace.x, trace.y = series.index, series.values
                            trace.connectgaps = False
                        marks = candidates[(candidates.event_date >= start) & (candidates.event_date < end)]
                        for day in marks.event_date.unique():
                            figure.add_vrect(x0=pd.Timestamp(day), x1=pd.Timestamp(day)+pd.Timedelta(days=1), fillcolor='#d15c48', opacity=.18, line_width=0)
                        st.plotly_chart(figure, width='stretch', key='measurement_curve')
                        st.caption('Schattierung: dokumentierter Servicetag, kein exakter Fehlerbeginn. Temperatur-Parquet bereits durch Autoren zeitkorrigiert. Keine erneute Uhrkorrektur. RTD und Temperaturen in °C; Mains Voltage in V. State bleibt als Bitcode in den Quelldaten und wird nicht gemittelt.')
                        st.download_button('Dargestellte Aggregate als CSV', curve.to_csv(index=False).encode('utf-8-sig'), 'servicepulse_messwerte.csv')
                    if chosen_date is not None:
                        st.write('Deskriptiver Vorher/Nachher-Vergleich ohne Ereignistag')
                        st.dataframe(window_comparison(path, measure, chosen_date, days), hide_index=True, width='stretch')
                        st.caption('Arithmetische, messpunktgewichtete Werte; keine Zeitgewichtung, keine Interpolation, keine Kausalaussage. Stichprobenzahlen und Zeitgrenzen auf Lücken prüfen.')
                    event_files = files[files.device_id.eq(device) & files.kind.eq('events')]
                    offpath = ROOT/'research/reference/data/raw_data/other_data/time_offsets.csv'
                    if len(event_files) > 1:
                        st.warning('Mehrere Geräteereignisdateien für diese ID vorhanden; automatische Verknüpfung ausgesetzt. Dateien vorab eindeutig zuordnen.')
                    elif not event_files.empty and offpath.exists():
                        clock_offsets = offsets(offpath)
                        if device in clock_offsets:
                            with st.expander('Geräteereignisse (maximal 1.000 Zeilen)'):
                                st.caption(f'Autorenkorrektur auf interne Uhr addiert: {clock_offsets[device]}. Ein konstanter Offset belegt keine historische Uhrgenauigkeit.')
                                st.dataframe(event_window(event_files.iloc[0].path, start, end, clock_offsets[device]), width='stretch')
                        else:
                            st.warning('Kein Uhrenoffset vorhanden; Geräteereignisse werden nicht zeitlich verknüpft.')
                except Exception as exc:
                    st.error(f'Messdatenabfrage fehlgeschlagen: {exc}')
    with st.expander('Weitere Parquet-Datei importieren'):
        st.caption('Dateiname: 806030_temp.parquet oder 806030_events.parquet. Herkunft und Lizenz eigener Dateien bitte separat dokumentieren. Große Dateien direkt nach data/raw/<Modell>/ kopieren.')
        st.caption('Erwartete Zeitkonvention der Autoren: _temp bereits zeitkorrigiert, _events interne Geräteuhr. Andere Zeitkonventionen vor dem Import fachlich klären.')
        upload = st.file_uploader('Parquet-Datei', type='parquet')
        if upload is not None and st.button('Datei prüfen und lokal übernehmen'):
            destination = ROOT/'data/raw/imported'/Path(upload.name).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                if destination.exists():
                    raise ValueError('Zieldatei existiert bereits; bitte bewusst im Dateisystem ersetzen.')
                content = upload.getvalue()
                # Schema vor Übernahme prüfen, dabei regulären Dateinamen verwenden.
                import pyarrow.parquet as pq
                import pyarrow as pa
                import io, re
                if not re.fullmatch(r'\d{6}_(temp|events)\.parquet', destination.name):
                    raise ValueError('Ungültiger Dateiname.')
                schema = pq.ParquetFile(io.BytesIO(content)).schema_arrow
                if 'Datetime' not in schema.names:
                    raise ValueError('Datetime fehlt.')
                if not pa.types.is_timestamp(schema.field('Datetime').type):
                    raise ValueError('Datetime muss als Arrow-Zeitstempel gespeichert sein.')
                if destination.name.endswith('_temp.parquet') and not any((pa.types.is_integer(field.type) or pa.types.is_floating(field.type) or pa.types.is_decimal(field.type)) and field.name not in ['index','__index_level_0__','State'] for field in schema):
                    raise ValueError('Keine numerische Messgröße vorhanden.')
                destination.write_bytes(content)
                st.success(f'Importiert: {destination.name}; SHA256 {hashlib.sha256(content).hexdigest()}')
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

with data_tab:
    st.subheader('Qualität der gesamten Servicequelle')
    st.dataframe(quality(df), hide_index=True, width='stretch')
    with st.expander('Kontrolle gegen das zweite Excel-Blatt'):
        st.dataframe(category_control(source,df),hide_index=True,width='stretch')
    reference = ROOT/'research/reference/data/raw_data/other_data/freezer_faults.csv'
    if reference.exists():
        compared = compare_reference(df, reference)
        st.write('Abweichungen zwischen Excel und Autoren-CSV')
        st.dataframe(compared[compared.reference_status.ne('Übereinstimmung')][['device_id','event_date','fault_text','reference_date','reference_fault','reference_status']], hide_index=True, width='stretch')
    st.write('Verfügbare Messdateien')
    st.dataframe(files.drop(columns='path'), hide_index=True, width='stretch')
    audit = ROOT/'data/processed/measurement_quality.csv'
    if audit.exists():
        with st.expander('Vollständige Messdatenprüfung je Datei'):
            st.dataframe(pd.read_csv(audit), hide_index=True, width='stretch')
    coverage_path = ROOT/'data/processed/event_coverage.csv'
    if coverage_path.exists():
        coverage = pd.read_csv(coverage_path)
        st.write(f'Messabdeckung: {int((coverage.day_rows>0).sum())}/{len(coverage)} Servicetage mit Messpunkten. {int(((coverage.before_rows>0)&(coverage.after_rows>0)).sum())}/{len(coverage)} mit Messpunkten in beiden Siebentagefenstern; keine Aussage über lückenlose Abdeckung.')
        st.dataframe(coverage, hide_index=True, width='stretch')
    if file_errors:
        st.error('Nicht lesbare Messdateien'); st.dataframe(file_errors)

with method_tab:
    st.subheader('Herkunft und eigene Entwicklungsleistung')
    st.markdown('''Die Forschungsdaten und Autorenlabels stammen von Huang et al. (2023). ServicePulse enthält eine eigene Excel-Aufbereitung, Qualitätskontrollen, DuckDB-Abfragen, Filter, Visualisierungen und Dokumentation. Der Autorencode wird als separate Referenz aufbewahrt und nicht ausgeführt.

    - [Wissenschaftlicher Artikel](https://doi.org/10.1038/s41597-023-02808-6) · CC BY 4.0
    - [Datensammlung](https://doi.org/10.6084/m9.figshare.c.6805332.v1) · Figshare-Metadaten: CC0
    - [GitLab-Repository](https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data) · keine explizite Codelizenz im geprüften Baum gefunden

    Servicekalendertage bleiben unverändert. Bereits zugeordnete `main_fault`-Labels im Messdatenbestand sind Autorenannotationen und keine zusätzlich gezählten Ausfälle. Geräte ohne Serviceeintrag gelten nicht automatisch als störungsfrei. Zeitzone und Sommerzeit sind in den Dateien nicht spezifiziert; es wird kein UTC behauptet.

    Details: `docs/repository_pruefung.md`, `docs/datenanalyse.md`, `docs/lizenzen_herkunft.md`.''')
