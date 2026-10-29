"""Excel bleibt die maßgebliche Servicequelle; Originalwerte bleiben erhalten."""
from pathlib import Path
import re
import pandas as pd

REQUIRED = {'freezer_id', 'registered_date', 'main_fault', 'Fault categories'}

def read_faults(path, sheet=None, mapping=None):
    book = pd.ExcelFile(path)
    candidates = []
    for name in book.sheet_names:
        frame = pd.read_excel(book, name).rename(columns=mapping or {})
        frame.columns = frame.columns.astype(str).str.strip()
        if REQUIRED.issubset(frame.columns):
            candidates.append((name, frame))
    if sheet is not None:
        candidates = [pair for pair in candidates if pair[0] == sheet]
    if len(candidates) != 1:
        raise ValueError(f'Genau ein passendes Datenblatt erforderlich. Gefunden: {[x[0] for x in candidates]}; erwartet: {sorted(REQUIRED)}')
    name, raw = candidates[0]
    df = raw.copy()
    df['source_file'] = Path(path).name
    df['source_sheet'] = name
    df['source_row'] = range(2, len(df) + 2)
    df['device_id'] = df.freezer_id.astype('string').str.strip().str.replace(r'\.0$', '', regex=True)
    df['device_valid'] = df.device_id.str.fullmatch(r'\d{6}', na=False)
    # Excel timestamps or ISO dates only; ambiguous text is flagged, never guessed.
    df['event_date'] = pd.to_datetime(df.registered_date, format='ISO8601', errors='coerce').dt.normalize()
    df['category_raw'] = df['Fault categories'].astype('string')
    df['category'] = df.category_raw.str.strip().fillna('Unbekannt').replace('', 'Unbekannt')
    df['category_group'] = df.category.str.replace(r'\s*\(No fix\)$', '', regex=True)
    df['no_fix'] = df.category.str.contains('(No fix)', regex=False, na=False)
    df['fault_text'] = df.main_fault.astype('string').str.strip()
    df['duplicate'] = df.duplicated(subset=list(raw.columns), keep=False)
    df['date_precision'] = 'day'
    return df

def filter_faults(df, devices=None, categories=None, start=None, end=None):
    mask = pd.Series(True, index=df.index)
    if devices is not None:
        mask &= df.device_id.isin(devices)
    if categories is not None:
        mask &= df.category.isin(categories)
    if start is not None:
        mask &= df.event_date >= pd.Timestamp(start)
    if end is not None:
        mask &= df.event_date < pd.Timestamp(end).normalize() + pd.Timedelta(days=1)
    return df.loc[mask].copy()

def metrics(df):
    counts = df.loc[df.device_valid].groupby('device_id').size()
    repeated = df.loc[df.device_valid].groupby(['device_id', 'category']).size()
    return {'entries': len(df), 'devices': int(df.loc[df.device_valid, 'device_id'].nunique()),
            'devices_multiple_entries': int((counts > 1).sum()),
            'repeated_device_category_pairs': int((repeated > 1).sum()),
            'invalid_dates': int(df.event_date.isna().sum()),
            'duplicate_rows': int(df.duplicate.sum())}

def quality(df):
    return pd.DataFrame([
        {'Prüfung': 'Fehlende Werte: ' + col, 'Anzahl': int(df[col].isna().sum())}
        for col in sorted(REQUIRED)
    ] + [
        {'Prüfung': 'Ungültige Gerätekennung', 'Anzahl': int((~df.device_valid).sum())},
        {'Prüfung': 'Datum nicht interpretierbar', 'Anzahl': int(df.event_date.isna().sum())},
        {'Prüfung': 'An identischen Duplikaten beteiligte Zeilen', 'Anzahl': int(df.duplicate.sum())},
        {'Prüfung': 'Kategorie mit äußerem Leerraum', 'Anzahl': int((df.category_raw != df.category).fillna(False).sum())},
        {'Prüfung': 'Kategorie Data missing', 'Anzahl': int(df.category.eq('Data missing').sum())},
        {'Prüfung': 'Kategorie No fix', 'Anzahl': int(df.no_fix.sum())},
    ])

def category_control(path, df):
    """Die Kontrolltabelle ist keine zusätzliche Servicequelle."""
    book = pd.ExcelFile(path)
    for sheet in book.sheet_names:
        control = pd.read_excel(book, sheet)
        expected = {'Fault categories','Count of Fault categories'}
        if expected.issubset(control.columns):
            control = control.rename(columns={'Fault categories':'category_group','Count of Fault categories':'reported_count'})
            control['category_group'] = control.category_group.astype('string').str.strip()
            actual = df.groupby('category_group').size().rename('calculated_count').reset_index()
            compared = actual.merge(control[['category_group','reported_count']], on='category_group', how='outer', validate='one_to_one')
            compared['matches'] = compared.calculated_count.eq(compared.reported_count)
            return compared
    return pd.DataFrame(columns=['category_group','calculated_count','reported_count','matches'])

def compare_reference(df, csv_path):
    """Nur eindeutige ID+Tag-Paare vergleichen; Konflikte nicht überschreiben."""
    ref = pd.read_csv(csv_path, dtype={'freezer_id': 'string'})
    ref['device_id'] = ref.freezer_id
    ref['reference_date'] = pd.to_datetime(ref.registered_date, format='%m/%d/%Y', errors='coerce')
    ref['reference_fault'] = ref.main_fault.str.strip()
    merged = df.merge(ref[['device_id','reference_date','reference_fault']],
                      left_on=['device_id','event_date'], right_on=['device_id','reference_date'], how='left', validate='many_to_one')
    merged['reference_status'] = 'Übereinstimmung'
    merged.loc[merged.reference_fault.isna(), 'reference_status'] = 'Kein ID/Tag-Treffer'
    merged.loc[merged.reference_fault.notna() & merged.fault_text.ne(merged.reference_fault), 'reference_status'] = 'Abweichender Fehlertext'
    return merged
