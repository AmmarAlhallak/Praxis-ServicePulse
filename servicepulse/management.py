"""Deutschsprachige Geräte- und Berichtverwaltung für die bestehende App."""
from datetime import date
import uuid
import pandas as pd
import streamlit as st
from servicepulse import repository as repo
from servicepulse.presentation import category_label, CATEGORIES, fault_label

def report_table(frame):
    columns=['device_id','event_date','category','fault_text','status','origin','action']
    view=frame[columns].copy()
    view.event_date=view.event_date.dt.strftime('%d.%m.%Y').fillna('Nicht angegeben')
    view.category=view.category.map(category_label)
    view.fault_text=[fault_label(r.fault_text) if r.origin=='research' else (r.fault_text or 'Nicht angegeben') for r in frame.itertuples()]
    view.origin=view.origin.map({'research':'Veröffentlichte Forschungsdaten','manual':'Selbst erfasst'})
    view=view.rename(columns={'device_id':'Geräte-ID','event_date':'Servicedatum','category':'Fehlerkategorie','fault_text':'Beschreibung','status':'Status','origin':'Herkunft','action':'Maßnahme'})
    st.dataframe(view,hide_index=True,width='stretch')

def report_form(device,frame):
    mode=st.radio('Servicebericht',['Neuen Bericht erfassen','Bestehenden Bericht bearbeiten'],horizontal=True,key='report_mode')
    editing=mode=='Bestehenden Bericht bearbeiten'
    existing=None;rid=None
    if editing:
        if frame.empty:
            st.info('Für dieses Gerät ist noch kein Servicebericht gespeichert.');return
        rid=st.selectbox('Bericht auswählen',frame.report_id.tolist(),format_func=lambda i:f'Bericht {i} · '+('Ohne Datum' if pd.isna(frame.loc[frame.report_id.eq(i),'event_date'].iloc[0]) else frame.loc[frame.report_id.eq(i),'event_date'].iloc[0].strftime('%d.%m.%Y')),key=f'edit_report_{device}')
        existing=frame.loc[frame.report_id.eq(rid)].iloc[0]
        token=f'edit_version_{rid}'
        expected=st.session_state.setdefault(token,int(existing.report_version))
        if st.button('Aktuellen Bericht neu laden',key=f'reload_{rid}'):
            st.session_state.pop(token,None)
            st.session_state[f'form_generation_{rid}']=st.session_state.get(f'form_generation_{rid}',0)+1
            st.rerun()
        if existing.origin=='research':
            st.info('Die veröffentlichte Originalzeile bleibt erhalten. Änderungen betreffen die aktuelle Arbeitsfassung und werden protokolliert.')
        with st.expander('Änderungshistorie und erhaltene Originalwerte'):
            for entry in repo.history(rid):
                st.markdown(f'**Version {entry["Version"]} · {entry["Grund"]}**')
                st.caption(f'{entry["Zeitpunkt"]:%d.%m.%Y %H:%M %Z} · {entry["Bearbeiter"]}')
                st.json({'Vorher':entry['Vorher'],'Nachher':entry['Nachher']},expanded=False)
    else:
        expected=None
    suffix=f'{device}_{rid}_{st.session_state.get(f"form_generation_{rid}",0)}'
    value=lambda key,default='':existing[key] if existing is not None else default
    category_options=sorted(set(CATEGORIES)|set(frame.category)|{'Unbekannt'},key=category_label)
    current=value('category','Unbekannt')
    with st.form(f'report_form_{suffix}'):
        st.caption('Nur Gerät und Herkunft sind erforderlich. Leere Angaben bleiben ausdrücklich „nicht angegeben“; es werden keine Messdaten erzeugt.')
        day=st.date_input('Servicedatum',value=None if existing is None or pd.isna(existing.event_date) else existing.event_date.date(),format='DD.MM.YYYY',key=f'report_date_{suffix}')
        cat=st.selectbox('Fehlerkategorie',category_options,index=category_options.index(current),format_func=category_label,key=f'report_category_{suffix}')
        description=st.text_area('Beschreibung der Störung',value=value('fault_text'),key=f'report_description_{suffix}',help='Freitext; die originale englische Beschreibung eines Forschungsberichts bleibt zusätzlich unverändert erhalten.')
        component=st.text_input('Betroffene Komponente (optional)',value=value('component'),key=f'report_component_{suffix}')
        action=st.text_area('Reparatur oder Wartungsmaßnahme (optional)',value=value('action'),key=f'report_action_{suffix}')
        status=st.selectbox('Status',repo.STATUSES,index=repo.STATUSES.index(value('status','offen')),key=f'report_status_{suffix}')
        notes=st.text_area('Bemerkungen (optional)',value=value('notes'),key=f'report_notes_{suffix}')
        source=st.text_input('Quelle / Herkunft',value=value('source_file'),disabled=editing,key=f'report_source_{suffix}',help='Zum Beispiel eigener Wartungsbericht. Wenn unbekannt: „Nicht bekannt“. Die Erstquelle bleibt bei Bearbeitungen erhalten; Ergänzungen gehören in Bemerkungen.')
        actor=st.text_input('Bearbeiter (optional)',key=f'report_actor_{suffix}')
        reason=st.text_input('Grund der Änderung',value='' if editing else 'Neuer Servicebericht',key=f'report_reason_{suffix}')
        submitted=st.form_submit_button('Änderungen speichern' if editing else 'Servicebericht speichern',type='primary')
    if submitted:
        try:
            request=st.session_state.setdefault('report_request',str(uuid.uuid4()))
            saved=repo.save_report(dict(device_id=device,service_date=day,category=cat,description=description,component=component,action=action,status=status,notes=notes,source=source,actor=actor,reason=reason),rid,expected,request)
            st.session_state.pop('report_request',None)
            if editing:st.session_state.pop(f'edit_version_{rid}',None)
            st.session_state[f'form_generation_{rid}']=st.session_state.get(f'form_generation_{rid}',0)+1
            st.session_state['saved_report']=saved;st.rerun()
        except ValueError as exc:st.error(str(exc))
        except Exception:st.error('Der Bericht wurde nicht gespeichert. Bitte Datenbankverbindung prüfen und erneut versuchen.')

def render(df,files,devices):
    st.subheader('Geräte und Service einfach verwalten')
    if 'saved_report' in st.session_state:st.success(f'Bericht {st.session_state.pop("saved_report")} wurde dauerhaft gespeichert. Historie und Statistiken sind aktualisiert.')
    search=st.text_input('Gerät suchen',placeholder='Geräte-ID, Bezeichnung, Modell oder Standort',key='device_search')
    counts=df.groupby('device_id').size()
    listing=devices.copy();listing['Serviceberichte']=listing['Geräte-ID'].map(counts).fillna(0).astype(int)
    listing['Messdaten']=listing['Geräte-ID'].isin(set(files.device_id)).map({True:'Vorhanden',False:'Keine vorhanden'})
    if search.strip():listing=listing[listing.astype(str).apply(lambda c:c.str.contains(search.strip(),case=False,regex=False)).any(axis=1)]
    st.dataframe(listing,hide_index=True,width='stretch',height=250)
    with st.expander('Neues Gerät anlegen'):
        with st.form('new_device'):
            identifier=st.text_input('Geräte-ID (6 Ziffern)',key='new_device_id')
            name=st.text_input('Bezeichnung (optional)',key='new_device_name')
            model=st.text_input('Modell (optional)',key='new_device_model')
            location=st.text_input('Standort (optional)',key='new_device_location')
            add=st.form_submit_button('Gerät anlegen')
        if add:
            try:repo.add_device(identifier.strip(),name,model,location);st.rerun()
            except ValueError as exc:st.error(str(exc))
    if listing.empty:
        st.info('Kein Gerät zur Suche gefunden. Suche ändern oder ein neues Gerät anlegen.');return
    options=listing['Geräte-ID'].tolist()
    device=st.selectbox('Gerät öffnen',options,index=options.index('806279') if '806279' in options else 0,key='managed_device')
    details=devices.loc[devices['Geräte-ID'].eq(device)].iloc[0]
    st.caption(f'Gerät {device} · {details.Bezeichnung or "Bezeichnung nicht angegeben"} · {details.Modell or "Modell nicht angegeben"} · {details.Standort or "Standort nicht angegeben"}')
    own=df[df.device_id.eq(device)]
    st.markdown('#### Bisherige Serviceberichte')
    if own.empty:st.info('Für dieses Gerät ist noch kein Servicebericht dokumentiert.')
    else:
        report_table(own.sort_values('event_date',ascending=False,na_position='last'))
        repeated=own.category.value_counts();repeated=repeated[repeated>1]
        if not repeated.empty:st.write('Mehrfach dokumentiert: '+', '.join(f'{category_label(k)} ({v} Einträge)' for k,v in repeated.items())+'. Das sind nicht automatisch unabhängige Ausfälle.')
    st.markdown('#### Verfügbare Betriebsdaten')
    data=files[files.device_id.eq(device)]
    if data.empty:st.info('Für dieses Gerät sind keine Messdaten registriert. Ein Servicebericht erzeugt keine Sensordaten.')
    else:
        st.write(f'{len(data)} Mess- oder Meldungsdateien verfügbar. Die Betriebsanalyse bietet eine eigene Geräte- und Zeitraumwahl.')
        if st.button('Dieses Gerät für die Betriebsanalyse auswählen'):
            st.session_state['measurement_device']=device;st.success('Gerät ausgewählt. Öffne „Betriebsanalyse & Vergleiche“.')
    with st.expander('Ähnliche dokumentierte Fälle bei anderen Geräten'):
        similar=df[df.category.isin(own.category)&df.device_id.ne(device)]
        if similar.empty:st.info('Keine weiteren Einträge derselben Kategorien vorhanden.')
        else:report_table(similar)
        st.caption('Ähnlichkeit bedeutet hier dieselbe Kategorie; sie belegt weder dieselbe Ursache noch vergleichbare Betriebsbedingungen.')
    st.markdown('#### Bericht erfassen oder bearbeiten')
    report_form(device,own)
