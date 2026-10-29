"""ServicePulse: deutsche Darstellung auf unveränderten Forschungsdaten."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from servicepulse.faults import read_faults, metrics, quality, filter_faults, compare_reference, category_control
from servicepulse.measurements import inventory, numeric_columns, series_window, window_comparison, event_window, offsets, time_bounds, serviceday_summary
from servicepulse.presentation import category_label, fault_label, measure_label, unit, german_number, display_frame, faults_export, style_figure, counts_figure, measurement_figure
from servicepulse.imports import import_parquet
from servicepulse.research import QUESTION, DEMO_CASES, apply_service_selection, case_observation, coverage_rows, inputs_fingerprint, read_test_report

ROOT = Path(__file__).resolve().parent
CHART_CONFIG = {'displayModeBar': False, 'responsive': True, 'displaylogo': False}
st.set_page_config(page_title='ServicePulse · Kälteanlagen verstehen', page_icon='❄', layout='wide')
st.markdown('''<style>
.stApp {background:#f3f7fa;color:#183447;}
.block-container {max-width:1440px;padding-top:4.5rem;padding-bottom:3rem;}
h1,h2,h3 {color:#16364a;letter-spacing:-.025em;} h1{font-size:2.35rem !important;}
[data-testid="stSidebar"] {background:#eaf1f5;border-right:1px solid #d9e5ec;}
[data-testid="stMetric"] {background:#fff;border:1px solid #dce7ed;border-radius:14px;padding:16px;}
[data-testid="stMetricValue"] {color:#126e80;}
[data-testid="stMetricLabel"] p {white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}
[data-testid="stMetricLabel"] {min-height:4rem;}
[data-testid="stTabs"] [role="tablist"] {gap:10px;border-bottom:1px solid #d8e4eb;}
[data-testid="stTabs"] [role="tab"] {padding:14px 8px;font-weight:600;white-space:nowrap;}
[data-testid="stExpander"] {background:#fff;border-radius:12px;}
[data-testid="stElementToolbar"], [data-testid="stToolbarActions"] {display:none;}
[data-testid="stFileUploaderDropzoneInstructions"] {display:none;}
[data-testid="stFileUploaderDropzone"] button {font-size:0;}
[data-testid="stFileUploaderDropzone"] button::after {content:'Datei auswählen';font-size:14px;}
@media(max-width:800px){h1{font-size:1.8rem !important;}.block-container{padding-left:1rem;padding-right:1rem;}}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load_excel(path, modified):
    return read_faults(path)

def table(frame, key=None, height='auto'):
    st.dataframe(display_frame(frame),hide_index=True,width='stretch',height=height,key=key)

def chart(figure, key):
    st.plotly_chart(figure,width='stretch',key=key,config=CHART_CONFIG)

def show_counts(frame, column, label, key):
    if frame.empty:
        st.info('Für diese Auswahl liegen keine Serviceeinträge vor.')
    else:
        chart(counts_figure(frame,column,label),key)

def technical_error(exc):
    with st.expander('Technische Fehlerdetails'):
        st.code(str(exc),language=None)

st.caption('SERVICEPULSE  /  ANALYSE VON ULTRATIEFKÜHLGERÄTEN')
st.title('Betrieb verstehen. Service einordnen.')
st.write('Reale Betriebsdaten und dokumentierte Serviceeinträge – verständlich aufbereitet, wissenschaftlich eingeordnet.')
try:
    source = ROOT/'fault_summary_R1.xlsx'
    df = load_excel(str(source), source.stat().st_mtime_ns)
except Exception as exc:
    st.error('Die Serviceübersicht konnte nicht geladen werden. Bitte prüfe, ob die Excel-Datei im Projektordner liegt und lesbar ist.')
    technical_error(exc)
    st.stop()
files,file_errors = inventory(ROOT/'data/raw')
reference = ROOT/'research/reference/data/raw_data/other_data/freezer_faults.csv'
compared = compare_reference(df,reference) if reference.exists() else None
conflicts = compared[compared.reference_status.ne('Übereinstimmung')] if compared is not None else None
if st.session_state.get('service_filter_version') != 2:
    for old_key in ['devices','categories','date_range','all_devices','all_categories','limit_service_dates','service_start','service_end']:
        st.session_state.pop(old_key,None)
    st.session_state['service_filter_version']=2

def choose_demo(code):
    selected_device,selected_date,_=DEMO_CASES[code]
    matching=df[df.device_id.eq(selected_device)&df.event_date.eq(pd.Timestamp(selected_date))]
    if matching.empty:
        return
    st.session_state['measurement_device']=selected_device
    st.session_state[f'service_day_{selected_device}']=matching.index[0]
    st.session_state[f'measure_{selected_device}']='RTD'
    st.session_state['comparison_days']=7
    st.session_state['period_mode']='Rund um einen Servicetag'
    st.session_state['link_service_filters']=False

with st.sidebar:
    st.markdown('### ❄ ServicePulse')
    st.caption('Historische Daten · lokale Analyse')
    st.subheader('Serviceauswahl')
    st.caption('Diese Filter gelten für Übersicht, Störungsanalyse und Serviceexport. „Temperatur & Betrieb“ hat eine eigene Fall- und Zeitraumwahl; eine Verknüpfung ist dort optional möglich.')
    if st.button('Alle Filter zurücksetzen',width='stretch'):
        for key in ['devices','categories','date_range','include_undated','all_devices','all_categories','limit_service_dates','service_start','service_end']:
            st.session_state.pop(key,None)
        st.rerun()
    with st.expander('Geräte auswählen'):
        device_options = sorted(df.device_id.dropna().unique())
        all_devices=st.checkbox('Alle Geräte berücksichtigen',value=True,key='all_devices')
        device_selection=st.multiselect('Geräte-ID suchen',device_options,default=[],key='devices',disabled=all_devices,placeholder='Geräte-ID eingeben oder auswählen',help='Für einzelne Geräte das Häkchen bei „Alle Geräte“ entfernen. Die Auswahl ist durchsuchbar. Eine dann leere Auswahl zeigt keine Einträge.')
        devices=None if all_devices else device_selection
    with st.expander('Fehlerkategorien auswählen'):
        category_options=sorted(df.category.unique(),key=category_label)
        all_categories=st.checkbox('Alle Kategorien berücksichtigen',value=True,key='all_categories')
        category_selection=st.multiselect('Fehlerkategorie suchen',category_options,default=[],format_func=category_label,key='categories',disabled=all_categories,placeholder='Kategorie eingeben oder auswählen',help='Die deutschen Namen sind Anzeigeübersetzungen. Originalkategorien bleiben unverändert erhalten.')
        categories=None if all_categories else category_selection
    dates=df.event_date.dropna()
    limit_dates=st.checkbox('Servicezeitraum eingrenzen',value=False,key='limit_service_dates')
    start_date=st.date_input('Servicedatum ab',dates.min().date() if len(dates) else None,format='DD.MM.YYYY',key='service_start',disabled=not limit_dates)
    end_date=st.date_input('Servicedatum bis',dates.max().date() if len(dates) else None,format='DD.MM.YYYY',key='service_end',disabled=not limit_dates)
    include_undated=st.checkbox('Einträge ohne gültiges Datum einbeziehen',value=True,key='include_undated')
    st.divider()
    st.caption(f'{len(df)} Serviceeinträge · {df.loc[df.device_valid,"device_id"].nunique()} betroffene Geräte\n\n{len(files)} verfügbare Messdateien')
    with st.expander('Begriffe kurz erklärt'):
        st.markdown('''**Serviceeintrag:** eine dokumentierte Meldung oder Maßnahme aus der Serviceübersicht, kein automatisch bestätigter Ausfall.

**Fehlerkategorie:** die von den Forschern zugeordnete Gruppe eines Eintrags.

**Ohne Behebung:** Originalzusatz „No fix“; der Bericht dokumentiert keine Behebung. Weitere Einträge können denselben Zustand betreffen.

**Messdaten fehlen:** Originalkategorie „Data missing“; keine leere Excel-Zelle.

**Messabdeckung:** zeigt, ob und wie viele Messpunkte in einem Zeitfenster vorliegen. Einzelne Punkte belegen keine lückenlose Aufzeichnung.''')

filtered,filter_problem=apply_service_selection(df,devices,categories,limit_dates,start_date,end_date,include_undated)
if filter_problem:
    st.warning(filter_problem)
device_summary=f'alle {len(device_options)}' if all_devices else ', '.join(devices) if devices else 'keine'
category_summary=f'alle {len(category_options)}' if all_categories else ', '.join(map(category_label,categories)) if categories else 'keine'
period_summary='gesamter dokumentierter Zeitraum' if not limit_dates else f'{start_date:%d.%m.%Y} – {end_date:%d.%m.%Y}' if start_date and end_date and not filter_problem else 'ungültig / unvollständig'
active_summary=f'Aktive Servicefilter · Geräte: {device_summary} · Kategorien: {category_summary} · Zeitraum: {period_summary} · Einträge ohne Datum: {"einbezogen" if include_undated else "ausgeschlossen"}'
with st.sidebar:
    st.info(active_summary)
m=metrics(filtered)
metric_items=[('Serviceeinträge',m['entries'],'Dokumentierte Einträge in der aktuellen Auswahl. Ein Eintrag kann mehrere Komponenten betreffen.'),
              ('Betroffene Geräte',m['devices'],'Unterschiedliche gültige Geräte-IDs mit mindestens einem ausgewählten Eintrag.'),
              ('Mehrfach dokumentierte Geräte',m['devices_multiple_entries'],'Geräte mit mehr als einem Eintrag. Das beweist keine wiederholten unabhängigen Ausfälle.'),
              ('Wiederholte Gerät/Kategorie-Paare',m['repeated_device_category_pairs'],'Anzahl der Geräte- und Originalkategorie-Kombinationen mit mehreren Einträgen. „Ohne Behebung“ bleibt eigenständig.')]
for column,(label,value,help_text) in zip(st.columns(4),metric_items):
    column.metric(label,value,help=help_text)
st.caption(f'Aktuelle Serviceauswahl: {len(filtered)} von {len(df)} Einträgen. Mehrere Einträge können denselben ungelösten Zustand beschreiben.')
st.caption(active_summary)
overview,research,analysis,operation,data_quality,method=st.tabs(['Übersicht','Forschungsfrage & Ergebnisse','Störungsanalyse','Temperatur & Betrieb','Datenqualität','Methodik & Quellen'])

with overview:
    st.subheader('Welche Serviceanlässe sind dokumentiert?')
    left,right=st.columns([3,2],gap='large')
    with left:
        show_counts(filtered,'category_group','Fehlerkategorie','overview_categories')
        st.caption('Für diesen Überblick ist „ohne Behebung“ zur zugehörigen Hauptkategorie zusammengefasst. Alle Einträge bleiben enthalten.')
    with right:
        st.markdown('#### Die Auswahl einordnen')
        if not filtered.empty:
            top=filtered.category_group.value_counts()
            st.write(f'**{category_label(top.index[0])}** ist mit **{int(top.iloc[0])} Einträgen** die häufigste Gruppe in der aktuellen Auswahl.')
        st.info('Ein Serviceeintrag ist kein nachgewiesener unabhängiger Ausfall. Aus diesen Häufigkeiten ergibt sich keine Ausfallwahrscheinlichkeit.')
        st.markdown('**So gehst du vor**\n\n1. Serviceauswahl links eingrenzen.\n2. Häufigkeiten unter „Störungsanalyse“ vergleichen.\n3. Unter „Temperatur & Betrieb“ einen Servicetag im Messverlauf ansehen.')
    st.subheader('Serviceeinträge der aktuellen Auswahl')
    table(filtered[['device_id','event_date','category','fault_text']],key='service_rows',height=310)
    st.download_button('Serviceauswahl als CSV herunterladen',faults_export(filtered),'servicepulse_serviceeintraege.csv','text/csv',key='export_faults',help='Enthält deutsche Lesehilfen und alle Originalspalten, Originalwerte und Quellzeilen zur Nachprüfung.')
    with st.expander('Originalwerte und Herkunft der ausgewählten Einträge'):
        st.caption('Unveränderte Originalwerte und technische Zusatzfelder. Die Originalkategorien sind auch im CSV-Export enthalten.')
        st.dataframe(filtered,hide_index=True,width='stretch',height=300)

with analysis:
    left,right=st.columns([3,2],gap='large')
    with left:
        st.subheader('Fehlerkategorien vergleichen')
        grouped=st.toggle('Einträge ohne Behebung mit der Hauptkategorie zusammenfassen',value=False,key='group_categories',help='Ändert nur dieses Diagramm. Originalkategorien und Kennzahlen bleiben unverändert.')
        show_counts(filtered,'category_group' if grouped else 'category','Fehlerkategorie','fault_categories')
        st.caption('Dargestellt sind dokumentierte Serviceeinträge nach Autorenkategorie. Häufigere Meldungen belegen weder eine höhere Ausfallwahrscheinlichkeit noch unabhängige Defekte. Die Abgrenzung einzelner Serviceepisoden bleibt offen.')
    with right:
        st.subheader('Einträge nach Geräten')
        show_counts(filtered,'device_id','Geräte-ID','device_counts')
        if not filtered.empty:
            counts=filtered.device_id.value_counts()
            st.write(f'Beispiel aus der Auswahl: Gerät {counts.index[0]} hat {int(counts.iloc[0])} dokumentierte Einträge.')
        st.caption('Die Beobachtungsdauern und Messlücken unterscheiden sich je Gerät. Diese Rohhäufigkeiten sind keine Ausfallraten und kein fairer Zuverlässigkeitsrang. Vergleichbare Betriebszeiten und Serviceepisoden müssen dafür erst definiert werden.')
    st.subheader('Mehrere Einträge derselben Kategorie')
    repeated=filtered.groupby(['device_id','category']).size().reset_index(name='Serviceeinträge')
    repeated=repeated[repeated.Serviceeinträge>1]
    if repeated.empty:
        st.caption('In dieser Auswahl gibt es keine mehrfach dokumentierte Kombination aus Gerät und Originalkategorie.')
    table(repeated,key='repeated_rows')
    st.caption('Die Tabelle zählt Kombinationen, keine unabhängigen Ausfälle. Eine ungelöste Störung kann mehrere Serviceeinträge verursachen.')
    st.subheader('Wann wurde Service registriert?')
    timeline=filtered.dropna(subset=['event_date']).assign(Monat=lambda x:x.event_date.dt.to_period('M').dt.to_timestamp()).groupby('Monat').size().reset_index(name='Serviceeinträge')
    if len(timeline):
        figure=px.bar(timeline,x='Monat',y='Serviceeinträge',color_discrete_sequence=['#147d92'])
        figure.update_traces(hovertemplate='%{x|%m.%Y}<br>Serviceeinträge: %{y}<extra></extra>')
        figure.update_xaxes(tickformat='%m.%Y')
        chart(style_figure(figure,300),'service_timeline')
        peak=timeline.loc[timeline.Serviceeinträge.idxmax()]
        st.write(f'Ein Monat mit der höchsten Eintragszahl in dieser Auswahl ist {peak["Monat"]:%m.%Y} mit {int(peak.Serviceeinträge)} Einträgen. Daraus folgt kein saisonales Ausfallmuster; Beobachtungsumfang und Berichtspraxis können sich unterscheiden.')
    st.caption('Registrierungsdaten haben Tagesauflösung. Ein Registrierungsdatum beschreibt nicht den nachgewiesenen Beginn eines Defekts.')

with operation:
    st.subheader('Den Servicetag im Betrieb betrachten')
    st.write('Die Fallanalyse hat eine eigene Geräte-, Service- und Zeitraumwahl. Die Servicefilter links verändern diesen Untersuchungsfall standardmäßig nicht.')
    temperatures=files[files.kind.eq('temp')]
    for area,(code,(example_device,example_date,example_label)) in zip(st.columns(3),DEMO_CASES.items()):
        available=not df[df.device_id.eq(example_device)&df.event_date.eq(pd.Timestamp(example_date))].empty and example_device in set(temperatures.device_id)
        area.button(f'Beispiel: {example_label}',key=f'demo_{code}',on_click=choose_demo,args=(code,),disabled=not available,width='stretch',help=f'Gerät {example_device}, {pd.Timestamp(example_date):%d.%m.%Y}, Kammertemperatur und sieben Tage je Vergleichsfenster. Verwendet die gesamte Servicequelle, ohne die Servicefilter links zu ändern.')
    if temperatures.empty:
        st.info('Keine lesbaren Betriebsmessdateien vorhanden. Die Serviceanalyse funktioniert mit Excel weiter. Messdateien lassen sich nach der Importanleitung ergänzen.')
    else:
        options=sorted(temperatures.device_id.unique())
        preferred='806279' if '806279' in options else options[0]
        device=st.selectbox('1 · Gerät auswählen',options,index=options.index(preferred),key='measurement_device',help='Die Geräte-ID bleibt die eindeutige Kennung. Hier sind alle Geräte mit Messdaten verfügbar, auch ohne Serviceeintrag.')
        matches=temperatures[temperatures.device_id.eq(device)]
        with st.expander('Expertenansicht · Messdatei und Originalfelder'):
            selected_path=st.selectbox('Messdatei auswählen',matches.path.tolist(),format_func=lambda p:Path(p).name,key=f'measurement_file_{device}')
            st.code(selected_path,language=None)
            st.caption('Veröffentlichte Temperaturdaten sind bereits nach Autorenmethode zeitkorrigiert. Originalfelder und Bitcodes bleiben in der Datei erhalten.')
            linked=st.checkbox('Servicefilter links auch auf Fallliste und Markierungen anwenden',value=False,key='link_service_filters')
        path=Path(selected_path)
        numeric=numeric_columns(path)
        case_source=filtered if linked else df
        candidates=case_source[case_source.device_id.eq(device)&case_source.event_date.notna()]
        st.caption('Fallliste: aktive Serviceauswahl.' if linked else 'Fallliste: alle dokumentierten Serviceeinträge dieses Geräts. Der nachfolgende Messzeitraum ist unabhängig vom Servicezeitraum links.')
        mode=st.radio('Untersuchungsart',['Rund um einen Servicetag','Freier Zeitraum'],horizontal=True,key='period_mode')
        chosen_date=None
        if mode=='Rund um einen Servicetag' and not candidates.empty:
            indices=candidates.index.tolist()
            leak_ids=candidates[candidates.category.eq('Refrigerant leakage')].index.tolist()
            row_id=st.selectbox('2 · Dokumentierten Serviceeintrag auswählen',indices,index=indices.index(leak_ids[0]) if leak_ids else 0,format_func=lambda i:f'{df.loc[i,"event_date"]:%d.%m.%Y} · {category_label(df.loc[i,"category"])}',key=f'service_day_{device}')
            chosen_date=df.loc[row_id,'event_date']
            st.caption(f'Dokumentierter Anlass: {fault_label(df.loc[row_id,"fault_text"])} · Geräte-ID {device}')
            st.caption(f'Quelle: {df.loc[row_id,"source_file"]}, Excel-Zeile {int(df.loc[row_id,"source_row"])}. Originalfelder und englische Beschreibung bleiben im Serviceexport erhalten.')
            measure=st.selectbox('3 · Messgröße wählen',numeric,index=numeric.index('RTD') if 'RTD' in numeric else 0,format_func=measure_label,key=f'measure_{device}')
            days=st.slider('Tage vor und nach dem Servicetag',1,30,7,key='comparison_days')
            start,end=chosen_date-pd.Timedelta(days=days),chosen_date+pd.Timedelta(days=days+1)
            if device=='806031' and chosen_date==pd.Timestamp('2023-02-03'):
                st.warning('Datumswiderspruch: Excel nennt den 03.02.2023, Autorenliste und Auftragsdatum im Bericht den 02.03.2023. Das Excel-Datum wurde nicht automatisch verändert.')
        else:
            if mode=='Rund um einen Servicetag':
                st.info('Kein Serviceeintrag für dieses Gerät in der gewählten Fallliste. Du kannst trotzdem einen freien Messzeitraum betrachten.')
            measure=st.selectbox('3 · Messgröße wählen',numeric,index=numeric.index('RTD') if 'RTD' in numeric else 0,format_func=measure_label,key=f'measure_{device}')
            first,last=time_bounds(path)
            last_day=pd.Timestamp(last).normalize() if last is not None else pd.Timestamp('2023-04-01')
            first_day=max(pd.Timestamp(first).normalize(),last_day-pd.Timedelta(days=6)) if first is not None else last_day
            measurement_dates=st.date_input('Messzeitraum von – bis',(first_day.date(),last_day.date()),format='DD.MM.YYYY',key=f'measurement_dates_{device}')
            start=pd.Timestamp(measurement_dates[0]) if len(measurement_dates) else first_day
            end=pd.Timestamp(measurement_dates[-1])+pd.Timedelta(days=1) if len(measurement_dates) else last_day+pd.Timedelta(days=1)
            if len(measurement_dates)!=2:
                st.info('Bitte Anfang und Ende auswählen. Bei einem gewählten Datum wird zunächst dieser einzelne Tag angezeigt.')
        if device=='806018':
            st.warning('Gerätezuordnung ungeklärt: Eine Rohdatei im Geräteordner 806018 nennt die Kennung 806022. Die Zuordnung der Autoren bleibt erhalten, ist aber fachlich noch zu klären.')
        st.caption('RTD ist der Widerstandstemperatursensor in der Kühlkammer. Er misst lokal und beschreibt nicht zwingend die Temperatur an jedem Ort der Kammer.')
        bucket=st.selectbox('Werte zusammenfassen pro', ['hour','day','minute'],format_func=lambda value:{'hour':'Stunde','day':'Tag','minute':'Minute'}[value],key='aggregation',help='Jedes Intervall zeigt den Durchschnitt sowie den kleinsten und größten beobachteten Messwert. Es wird nicht über Messlücken interpoliert.')
        st.markdown(f'#### 4 · Messverlauf: {measure_label(measure)} · Gerät {device}')
        st.caption(f'Zeitraum: {start:%d.%m.%Y} bis {(end-pd.Timedelta(days=1)):%d.%m.%Y}')
        if (end-start).days>366 and bucket=='minute':
            st.warning('Bitte für die Minutenansicht höchstens 366 Tage auswählen oder auf Stunden bzw. Tage umstellen.')
        else:
            try:
                curve=series_window(path,measure,start,end,bucket)
                if curve.empty:
                    st.warning('Keine Messwerte in diesem Zeitraum. Es werden keine entfernten Messpunkte als Ersatz verwendet.')
                else:
                    marks=candidates[(candidates.event_date>=start)&(candidates.event_date<end)]
                    chart(measurement_figure(curve,measure,bucket,marks.event_date.unique()),'measurement_curve')
                    st.caption('Mittelwert: Durchschnitt der vorhandenen Messwerte. Minimum und Maximum: kleinster und größter Wert je Intervall. Leere Intervalle bleiben Lücken; die Kurve enthält keine erfundenen Zwischenwerte.')
                    st.download_button('Messverlauf als CSV herunterladen',curve.to_csv(index=False).encode('utf-8-sig'),'servicepulse_messwerte.csv','text/csv',key='export_measurements',help='Exportiert die unveränderten berechneten Aggregate und Messpunktzahlen mit technischen Originalbezeichnungen.')
                st.info('Die farbige Fläche markiert den dokumentierten Servicetag – keinen nachgewiesenen Fehlerbeginn. Ein Unterschied vor und nach diesem Tag beweist keine Reparaturwirkung.')
                if chosen_date is not None:
                    comparison=window_comparison(path,measure,chosen_date,days)
                    day=serviceday_summary(path,measure,chosen_date)
                    st.subheader('5 · Vor und nach dem Servicetag')
                    st.caption(f'Jeweils {days} Tage; der Servicetag selbst ist aus beiden Vergleichsfenstern ausgeschlossen. Der Durchschnitt gewichtet jeden vorhandenen Messwert gleich.')
                    for area,(_,row) in zip(st.columns(2),comparison.iterrows()):
                        with area:
                            label='Vor dem Servicetag' if row['window']=='Vorher' else 'Nach dem Servicetag'
                            st.metric(label,f'{german_number(row["mean"],2)} {unit(measure)}' if pd.notna(row['mean']) else 'Keine Messwerte',help='Durchschnitt der vorhandenen Messwerte im jeweiligen Fenster.')
                            st.caption(f'Gültige Messpunkte: {german_number(row["valid"])} · Median: {german_number(row["median"],2)} {unit(measure)}')
                            st.caption(f'Minimum: {german_number(row["minimum"],2)} {unit(measure)} · Maximum: {german_number(row["maximum"],2)} {unit(measure)}')
                    st.caption(f'Am Servicetag selbst: {german_number(day.valid)} gültige Messpunkte. Diese gehen nicht in die beiden Vergleichsmittelwerte ein.')
                    if (comparison.valid==0).any():
                        st.warning('Mindestens ein Vergleichsfenster enthält keine gültigen Messwerte. Ein Vorher-Nachher-Vergleich ist für dieses Fenster nicht möglich.')
                    st.caption('Unterschiedliche Messpunktzahlen und Lücken können die Vergleichbarkeit begrenzen. Auch viele Messpunkte belegen keine kontinuierliche Aufzeichnung.')
                    st.subheader('6 · Beobachtung und Datenlücken verstehen')
                    st.write(case_observation(comparison,day,unit(measure)))
                    st.dataframe(coverage_rows(comparison,day,days),hide_index=True,width='stretch',key='case_coverage')
                    st.caption('Eine Stunde gilt hier als beobachtet, sobald mindestens ein gültiger Messwert vorliegt. Das ist keine vollständige Stundenabdeckung. Doppelte Zeitstempel erhöhen nicht die Anzahl beobachteter Stunden.')
                    st.info('Noch zu prüfen: Betriebszustände, Türöffnungen, Abtauen, zeitlicher Beginn des Defekts und Inhalt der Serviceberichte. Ohne diese Prüfungen lässt sich eine Veränderung nicht einer Reparatur zuschreiben.')
                    with st.expander('Expertenansicht · Vergleichsfenster und Messpunktzahlen'):
                        table(comparison)
                        st.caption('Median: mittlerer Wert der sortierten Messwerte. Die Grenzen zeigen den ersten und letzten vorhandenen Messpunkt, keine garantierte lückenlose Abdeckung.')
                event_files=files[files.device_id.eq(device)&files.kind.eq('events')]
                offpath=ROOT/'research/reference/data/raw_data/other_data/time_offsets.csv'
                with st.expander('Expertenansicht · Geräteereignisse und Uhrkorrektur'):
                    st.caption('Gerätemeldungen wie Türöffnungen sind keine zusätzlichen Serviceeinträge. Bis zu 1.000 Originalmeldungen; diese werden zur Nachprüfbarkeit nicht automatisch übersetzt.')
                    if len(event_files)>1:
                        st.warning('Mehrere Meldungsdateien für dieselbe Geräte-ID. Die Zuordnung muss zuerst geklärt werden.')
                    elif not event_files.empty and offpath.exists():
                        clock=offsets(offpath)
                        if device in clock:
                            st.caption(f'Konstante Uhrkorrektur der Autoren: {clock[device]}. Historische Uhrdrift ist damit nicht geprüft.')
                            table(event_window(event_files.iloc[0].path,start,end,clock[device]),height=250)
                        else:
                            st.warning('Keine Uhrkorrektur für dieses Gerät vorhanden; Meldungen werden nicht zeitlich zugeordnet.')
                    else:
                        st.info('Keine eindeutig zuordenbaren Meldungsdaten mit Uhrenreferenz vorhanden.')
            except Exception as exc:
                st.error('Die Messdaten konnten für diese Auswahl nicht ausgewertet werden. Bitte eine andere Messgröße oder einen anderen Zeitraum wählen und die Datenqualität prüfen.')
                technical_error(exc)
    with st.expander('Erweiterte Funktion · Weitere Messdateien importieren'):
        st.write(f'Es sind bereits **{len(files)} veröffentlichte bzw. lokal ergänzte Messdateien** verfügbar. Im geprüften Forschungsbestand sind es 106. Für die normale Nutzung ist kein erneuter Import nötig.')
        st.caption('Parquet ist das Dateiformat der Betriebsmessdaten. Nur zum Ergänzen weiterer Dateien verwenden. Vorhandene Dateien werden nicht überschrieben.')
        st.markdown('Dateiname beispielsweise `806279_temp.parquet` für Messwerte oder `806279_events.parquet` für Meldungen. Herkunft und Lizenz zusätzlicher Dateien separat dokumentieren. Temperaturdateien müssen bereits zeitkorrigiert sein, Meldungsdateien die interne Gerätezeit der Autorenpipeline verwenden.')
        upload=st.file_uploader('Messdatei auswählen (Parquet, höchstens 300 MB)',type='parquet',key='parquet_upload')
        if upload is not None and st.button('Datei prüfen und importieren',key='import_parquet'):
            try:
                destination,digest=import_parquet(upload.getvalue(),upload.name,ROOT/'data/raw/imported')
                st.session_state['import_success']=destination.name
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error('Die Datei konnte nicht gespeichert werden. Bitte Speicherplatz und Schreibrechte prüfen.')
                technical_error(exc)
        if 'import_success' in st.session_state:
            st.success(f'Datei erfolgreich geprüft und übernommen: {st.session_state.pop("import_success")}')
        st.caption('Größere Dateien nach der lokalen Importanleitung in docs/datenimport.md direkt nach data/raw/<Modell>/ kopieren. Danach den Qualitätsbericht neu erstellen.')

with data_quality:
    st.subheader('Wie belastbar ist die Datengrundlage?')
    st.caption('Diese Qualitätsübersicht bezieht sich auf den gesamten lokalen Datenbestand, unabhängig von den Servicefiltern.')
    audit_path=ROOT/'data/processed/measurement_quality.csv'
    coverage_path=ROOT/'data/processed/event_coverage.csv'
    audit=None
    if not files.empty and audit_path.exists():
        snapshot=pd.read_csv(audit_path,dtype={'device_id':'string'})
        same_files=set(snapshot.path)==set(files.path)
        fresh=all(Path(path).stat().st_mtime<=audit_path.stat().st_mtime for path in files.path)
        if same_files and fresh:
            audit=snapshot
        else:
            st.warning('Der gespeicherte Messdatenbericht passt nicht mehr zum aktuellen Dateibestand. Bitte den Qualitätsbericht aktualisieren; alte Summen werden nicht als aktuell angezeigt.')
    coverage=None
    if not files.empty and coverage_path.exists():
        snapshot=pd.read_csv(coverage_path,dtype={'device_id':'string'})
        current_keys=set(zip(df.source_row,df.device_id,df.event_date.dt.strftime('%Y-%m-%d')))
        saved_keys=set(zip(snapshot.source_row,snapshot.device_id,snapshot.date))
        if current_keys==saved_keys and set(snapshot.device_id).issubset(set(temperatures.device_id)) and coverage_path.stat().st_mtime>=source.stat().st_mtime:
            coverage=snapshot
        else:
            st.warning('Die gespeicherte Messabdeckung passt nicht zur aktuellen Servicequelle oder es fehlen zugehörige Messdateien. Bitte die Abdeckung erneut berechnen.')
    areas=st.columns(4)
    areas[0].metric('Servicetage mit Messpunkten',f'{int((coverage.day_rows>0).sum())} / {len(coverage)}' if coverage is not None else 'Nicht geprüft',help='Mindestens ein Messpunkt am dokumentierten Tag. Das ist keine Aussage über vollständige Tagesabdeckung.')
    areas[1].metric('Fehlende Zeitwerte',german_number(audit.null_times.sum()) if audit is not None else 'Nicht geprüft',help='Zeilen ohne gültigen Zeitwert im gespeicherten Prüfbericht über Mess- und Meldungsdateien.')
    temp_audit=audit[audit.kind.eq('temp')] if audit is not None else None
    areas[2].metric('Mehrfache Temperatur-Zeitstempel',german_number(temp_audit.repeated_timestamps.sum()) if temp_audit is not None else 'Nicht geprüft',help='Zusätzliche Temperaturzeilen mit einem bereits vorhandenen Zeitpunkt. Das beweist nicht, dass alle Messwerte identisch sind.')
    areas[3].metric('Quellenwidersprüche',str(len(conflicts)) if conflicts is not None else 'Nicht geprüft',help='Excel-Einträge mit anderem Fehlertext oder ohne passenden Eintrag am selben Tag in der Autorenliste.')
    st.markdown('#### Was bedeuten diese Qualitätszahlen fachlich?')
    st.markdown('''- **Mindestens ein Messpunkt ist keine vollständige Abdeckung.** Ein Servicetag kann nur wenige Werte enthalten; Vorher- und Nachherfenster können leer sein.
- **Null fehlende Zeitwerte bedeutet nicht null Messlücken.** Jede vorhandene Zeile kann ein Datum besitzen, während zwischen diesen Zeilen Monate ohne Aufzeichnung liegen.
- **Wiederholte Zeitstempel können Mittelwerte beeinflussen.** Mehrfach vorhandene Zeilen erhalten im messpunktgewichteten Mittel mehrfaches Gewicht. Sie bleiben erhalten, bis eine fachlich begründete Duplikatregel feststeht.
- **Mehrfach dokumentiert bedeutet nicht mehrfach unabhängig ausgefallen.** Berichte können denselben ungelösten Zustand oder verschiedene Maßnahmen zum selben Fall beschreiben.''')
    if coverage is not None:
        both=int(((coverage.before_rows>0)&(coverage.after_rows>0)).sum())
        st.info(f'Für {both} von {len(coverage)} Einträgen gibt es Messpunkte sowohl in den sieben Tagen vor als auch nach dem Servicetag. Lücken und ungleiche Messpunktzahlen bleiben möglich.')
    if temp_audit is not None:
        gap_days=temp_audit.max_gap_seconds.max()/86400
        st.warning(f'Messlücken beachten: Die größte beobachtete Lücke in einer Temperaturdatei beträgt rund {german_number(gap_days)} Tage. Zeiträume ohne Werte werden nicht aufgefüllt.')
    st.markdown('#### Bekannte Grenzen')
    st.write('Servicedaten besitzen keine verlässliche Uhrzeit. Bei Gerät 806031 widersprechen sich Datumsangaben; bei 806030 und 808783 unterscheiden sich Beschreibungen. Eine Rohdatenstichprobe im Ordner 806018 nennt Geräte-ID 806022. Diese Widersprüche werden nicht automatisch korrigiert.')
    if conflicts is not None:
        table(conflicts[['device_id','event_date','reference_status']],key='source_conflicts')
    else:
        st.info('Die Autorenliste liegt lokal nicht vor. Der automatische Quellenvergleich ist daher nicht verfügbar.')
    with st.expander('Messabdeckung je Serviceeintrag'):
        st.caption('Messpunktzahlen sind keine Betriebsstunden. Ein leerer Tag kann auch zwischen vorhandenen Aufzeichnungen liegen.')
        if coverage is not None:
            compact=display_frame(coverage[['device_id','date','day_rows','before_rows','after_rows']]).rename(columns={
                'Messpunkte am Servicetag':'Am Servicetag', 'Messpunkte vor dem Servicetag':'7 Tage davor',
                'Messpunkte nach dem Servicetag':'7 Tage danach'})
            st.dataframe(compact,hide_index=True,width='stretch',height=300)
        else:
            st.info('Kein aktueller Bericht zur Messabdeckung verfügbar. Die Daten können trotzdem direkt in der Messansicht abgefragt werden.')
    with st.expander('Qualität der Serviceübersicht und Kategorienkontrolle'):
        service_quality=quality(df).copy()
        service_quality['Prüfung']=service_quality['Prüfung'].replace({'Fehlende Werte: Fault categories':'Fehlende Fehlerkategorien','Fehlende Werte: freezer_id':'Fehlende Geräte-IDs','Fehlende Werte: registered_date':'Fehlende Servicedaten','Fehlende Werte: main_fault':'Fehlende Fehlerbeschreibungen','Kategorie Data missing':'Einträge der Originalkategorie „Messdaten fehlen“','Kategorie No fix':'Einträge ohne dokumentierte Behebung'})
        st.dataframe(service_quality,hide_index=True,width='stretch')
        table(category_control(source,df))
    with st.expander('Technische Details · vollständige Prüfberichte und Originalwerte'):
        st.caption('Feldüberschriften sind als Lesehilfe übersetzt. Unveränderte Originalfelder stehen im CSV-Export und in den lokalen Berichten zur Verfügung.')
        table(files,height=260)
        if audit is not None:
            table(audit,height=300)
            st.download_button('Vollständigen Messdatenbericht als CSV herunterladen',audit.to_csv(index=False).encode('utf-8-sig'),'servicepulse_datenqualitaet.csv','text/csv',key='export_quality')
        if coverage is not None:
            table(coverage,height=300)
        if conflicts is not None:
            st.dataframe(conflicts,hide_index=True,width='stretch',height=200)
    if file_errors:
        st.error(f'{len(file_errors)} Datei(en) konnten nicht gelesen werden. Sie sind nicht Teil der Messauswahl.')
        with st.expander('Technische Details · nicht lesbare Dateien'):
            table(pd.DataFrame(file_errors))
    if audit is None:
        st.caption('Prüfberichte lassen sich in VS Code über die Aufgabe „Datenbank und Qualitätsberichte aktualisieren“ erstellen. Das ist für die normale Filterbedienung nicht nötig.')

with research:
    st.subheader('Forschungsfrage & Ergebnisse')
    st.caption('Dieser Bereich beschreibt den gesamten vorhandenen Datenbestand, unabhängig von den Servicefiltern. Die Forschungsfrage ist vorläufig und mit Prof. Blunck abzustimmen.')
    st.markdown('#### 1 · Forschungsfrage')
    st.info(QUESTION)
    st.markdown('#### 2 · Verwendete Datenquellen')
    full=metrics(df)
    st.write(f'Die Service-Excel enthält {full["entries"]} Einträge an {full["devices"]} Geräten. Lokal sind {len(files)} lesbare Mess- und Meldungsdateien für {files.device_id.nunique()} Geräte verfügbar. Die Service-Excel, Autorenlisten und publizierten Parquets stammen aus dem Datensatz von Huang und Mitautoren (2023). Serviceberichte werden als separate Originalquelle zur Klärung von Widersprüchen verwendet.')
    st.markdown('#### 3 · Untersuchungsmethode')
    st.write('Originalwerte erhalten, Kennungen und Datumsfelder nachvollziehbar aufbereiten, Servicezeilen deskriptiv zählen, Messreihen nach Geräte-ID und Kalendertag untersuchen. DuckDB fragt die Parquets zeitlich begrenzt ab. Vorher-Nachher-Mittelwerte sind messpunktgewichtet und schließen den Servicetag aus. Lücken bleiben leer.')
    st.markdown('#### 4 · Messbare Zielgrößen')
    st.markdown('Eintragszahl · betroffene Geräte · Kategorienhäufigkeiten · mehrfache Gerät/Kategorie-Kombinationen · Messpunkte vor, am und nach einem Servicetag · Stunden mit/ohne Messpunkte · Temperaturdurchschnitt, Minimum und Maximum. Diese Größen beschreiben Dokumentation und Beobachtung; sie messen keine bewiesenen unabhängigen Ausfälle.')
    st.markdown('#### 5 · Vergleichs- und Kontrollverfahren')
    control=category_control(source,df)
    control_ok=not control.empty and bool(control.matches.all())
    checks=[{'Kontrolle':'Berechnete Kategorien gegen zweites Excel-Blatt','Stand':f'{int(control.matches.sum())} von {len(control)} Gruppen stimmen überein' if not control.empty else 'Kontrollblatt nicht vorhanden','Bedeutung':'Rechnerische Konsistenz, keine Validierung der tatsächlichen Fehlerursache.'},
            {'Kontrolle':'Serviceeinträge gegen Messdaten','Stand':f'{int((coverage.day_rows>0).sum())} von {len(coverage)} Tagen mit Messpunkten' if coverage is not None else 'Aktueller Abdeckungsbericht fehlt','Bedeutung':'Ein Treffer belegt nur einzelne Messungen; Zeitfenster separat prüfen.'},
            {'Kontrolle':'Excel gegen Autoren-CSV','Stand':f'{len(conflicts)} Einträge mit Abweichung' if conflicts is not None else 'Autorenliste fehlt','Bedeutung':'Keine automatische Umdeutung oder Korrektur von Datum und Fehlertext.'}]
    st.dataframe(pd.DataFrame(checks),hide_index=True,width='stretch',key='research_checks')
    with st.expander('Nachvollziehen: Kategorienhäufigkeiten und Excel-Kontrolle'):
        table(control)
        if not control.empty and not control_ok:
            st.warning('Mindestens eine Kontrollsumme weicht ab. Dies muss vor der fachlichen Interpretation geklärt werden.')
    run=read_test_report(ROOT)
    if run is None:
        st.caption('Für diesen Code-Stand liegt hier noch kein aktuelles Testprotokoll vor. Reproduktion: python -m pytest -q --junitxml=docs/testlauf_praxis.xml')
    else:
        st.write(f'Aktuelles automatisiertes Prüfprotokoll: {run["passed"]} bestandene Tests, {run["skipped"]} übersprungen, {run["failures"]+run["errors"]} fehlgeschlagen. Dazu gehört ein SQL-/pandas-Vergleich für reale Stundenaggregate, sofern die optionale Messdatei vorliegt.')
    verification_path=ROOT/'docs/lokale_pruefung.json'
    try:
        verification=json.loads(verification_path.read_text(encoding='utf-8-sig')) if verification_path.exists() else {}
        current=verification.get('status')=='ok' and verification.get('inputs_fingerprint')==inputs_fingerprint(source,files)
    except (OSError,ValueError,KeyError):
        current=False
    if current:
        checked=pd.Timestamp(verification['checked_at']).tz_convert('Europe/Budapest')
        st.success(f'Lokaler Datenabgleich für diesen Dateistand erfolgreich, ausgeführt am {checked:%d.%m.%Y um %H:%M}: Excel-Inhalte, DuckDB-Tabellen, SQL-Views und Parquet-Metadaten stimmen überein.')
    else:
        st.caption('Kein zum aktuellen Dateistand passendes Abgleichprotokoll verfügbar. Den schreibgeschützten Datenabgleich mit python scripts/check_local.py ausführen; Prüfprotokolle sind keine Garantie fachlich richtiger Labels.')
    st.markdown('#### 6 · Tatsächlich ermittelte Ergebnisse')
    st.write(f'{full["entries"]} Serviceeinträge an {full["devices"]} Geräten; {full["devices_multiple_entries"]} Geräte mit mehreren Einträgen und {full["repeated_device_category_pairs"]} wiederholte Original-Gerät/Kategorie-Paare.')
    category_counts=df.category.value_counts()
    if not category_counts.empty:
        st.write(f'Die häufigste Originalkategorie ist {category_label(category_counts.index[0])} mit {int(category_counts.iloc[0])} Einträgen. Das ist eine Dokumentationshäufigkeit, kein Anteil unabhängig ausgefallener Geräte.')
    if coverage is not None:
        st.write(f'{int((coverage.day_rows>0).sum())} von {len(coverage)} Servicetagen haben mindestens einen Temperaturmesspunkt. Bei {int(((coverage.before_rows>0)&(coverage.after_rows>0)).sum())} Einträgen gibt es Messpunkte in beiden angrenzenden Siebentagefenstern. Vollständige Abdeckung folgt daraus nicht.')
    if temp_audit is not None:
        st.write(f'Der aktuelle Messdatenbericht enthält {int(temp_audit.repeated_timestamps.sum())} zusätzliche Temperaturzeilen mit bereits vorkommendem Zeitstempel. Diese werden nicht stillschweigend entfernt.')
    st.caption('Die ausgewählten Fallbeispiele und ihre konkreten Temperatur- und Abdeckungswerte werden unter „Temperatur & Betrieb“ direkt aus den Messdateien berechnet.')
    st.markdown('#### 7 · Wissenschaftliche Einschränkungen')
    st.write('Wenige dokumentierte und nicht notwendigerweise unabhängige Fälle, unsichere Servicezeiten, Quellenwidersprüche, unterschiedliche Beobachtungsdauern und lange Messlücken begrenzen die Aussagekraft. Geräte ohne Servicebericht sind nicht als gesund validiert. Weder Ausfallwahrscheinlichkeiten noch Reparaturwirkungen oder Prognosegenauigkeiten werden behauptet.')
    st.markdown('#### 8 · Noch offene Fragen')
    st.markdown('''- Welche Berichte gehören zu derselben Serviceepisode, welche zu unabhängigen Defekten?
- Welche Zeitpunkte bezeichnen Auftrag, Reparatur oder tatsächlichen Fehlerbeginn?
- Wie lassen sich Geräteidentität, historische Uhren und gleiche Beobachtungsbedingungen absichern?
- Welche Mindestabdeckung ist für sinnvolle deskriptive Vergleiche erforderlich?
- Können später einfache Referenzverfahren auf vergleichbaren Betriebsfenstern geprüft werden? Diese Verfahren und eine mögliche Risikofrage gehören zur Bachelorperspektive und sind noch nicht implementiert.''')

with method:
    st.subheader('Was diese Anwendung zeigt – und was die Daten erlauben')
    st.markdown('''ServicePulse beschreibt historische Betriebswerte und dokumentierte Serviceeinträge. Die Daten stammen aus dem wissenschaftlichen ULT-Datensatz von Huang und Mitautoren (2023), erhoben an Geräten der Dänischen Nationalen Biobank. Es werden keine Ausfälle oder Messwerte simuliert und keine Ausfallwahrscheinlichkeiten vorhergesagt.

**Serviceeintrag und Ausfall sind unterschiedliche Dinge.** Ein Bericht kann mehrere Komponenten oder Termine betreffen. Mehrere Berichte können denselben ungelösten Zustand beschreiben. Ein Gerät ohne Serviceeintrag ist nicht automatisch störungsfrei.

**Zeitangaben sind begrenzt.** Markierungen zeigen den dokumentierten Kalendertag, keinen gesicherten Fehlerbeginn. Die Zeitzone ist nicht eindeutig spezifiziert. Uhrkorrekturen der Autoren werden offengelegt, aber nicht als Nachweis historischer Uhrgenauigkeit behandelt.

**Vergleiche sind beschreibend.** Vorher-Nachher-Werte können sich durch Lücken, unterschiedliche Messpunktzahlen oder veränderte Betriebszustände unterscheiden. Daraus folgt keine bewiesene Reparaturwirkung.''')
    with st.expander('Deutsche Bezeichnungen und englische Originalkategorien'):
        translation=pd.DataFrame({'Deutsche Bezeichnung':[category_label(v) for v in sorted(df.category.unique())],'Originalwert':sorted(df.category.unique())})
        st.dataframe(translation,hide_index=True,width='stretch')
        st.caption('„No fix“ wird als „ohne Behebung“ angezeigt. „Data missing“ bleibt eine eigene Autorenkategorie. Übersetzungen sind Lesehilfen, keine neue fachliche Diagnose.')
    st.markdown('''#### Herkunft und Nutzungsbedingungen

- [Wissenschaftlicher Artikel](https://doi.org/10.1038/s41597-023-02808-6) · Huang und Mitautoren, 2023 · Lizenz CC BY 4.0
- [Wissenschaftliche Datensammlung](https://doi.org/10.6084/m9.figshare.c.6805332.v1) · Datenlizenz laut Figshare-Metadaten: CC0
- [Verarbeitungscode der Autoren](https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data) · separate Referenz; keine ausdrückliche Codelizenz im geprüften Stand gefunden

Die eigenen Entwicklungsleistungen umfassen die Datenprüfung, Excel-Aufbereitung, begrenzte SQL-Abfragen mit DuckDB, Visualisierung und Benutzerführung. Die veröffentlichten Messdateien und Autorenannotationen bleiben als wissenschaftliche Quellen erkennbar.''')
    with st.expander('Technische Methodik und lokale Dokumentation'):
        st.write('Die kleine Service-Excel wird direkt eingelesen. Große Messreihen bleiben in Parquet-Dateien und werden zeitlich begrenzt mit DuckDB abgefragt. Datenbank und gespeicherte Berichte sind abgeleitete Prüfergebnisse. SQLite wird nur zum schreibgeschützten Lesen originaler Haier-Rohdaten benutzt.')
        st.code('docs/datenanalyse.md\ndocs/repository_pruefung.md\ndocs/lizenzen_herkunft.md\ndocs/technik_sql.md',language=None)
