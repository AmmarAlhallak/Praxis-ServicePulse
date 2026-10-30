"""Filterzustand, belegbare Falltexte und Aktualität von Prüfprotokollen."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import pandas as pd
from servicepulse.faults import filter_faults
from servicepulse.presentation import german_number

QUESTION = ('Wie lassen sich historische Serviceeinträge und Betriebszeitreihen von Ultratiefkühlgeräten '
            'nachvollziehbar aufbereiten und interaktiv untersuchen, sodass Störungshäufigkeiten, '
            'wiederkehrende Einträge, Temperaturverläufe und Datenlücken sichtbar werden?')
DEMO_CASES = {
    'temperature': ('806279','2022-06-28','Temperaturveränderung'),
    'gap': ('806030','2015-01-28','Messlücke'),
    'conflict': ('806031','2023-02-03','Datumswiderspruch'),
}

def apply_service_selection(df, devices=None, categories=None, limit_dates=False,
                            start=None, end=None, include_undated=True):
    selected = filter_faults(df, devices, categories)
    if limit_dates:
        if start is None or end is None:
            return selected.iloc[:0].copy(), 'Zeitraum unvollständig: Bitte Start- und Enddatum angeben. Bis dahin werden keine Serviceeinträge ausgewählt.'
        if pd.Timestamp(start) > pd.Timestamp(end):
            return selected.iloc[:0].copy(), 'Das Startdatum liegt nach dem Enddatum. Bitte den Zeitraum korrigieren; aktuell sind keine Serviceeinträge ausgewählt.'
        dated = filter_faults(selected,start=start,end=end)
        selected = pd.concat([dated,selected[selected.event_date.isna()]]) if include_undated else dated
    elif not include_undated:
        selected = selected[selected.event_date.notna()]
    return selected.copy(), None

def case_observation(comparison, day, column_unit):
    before, after = comparison.iloc[0], comparison.iloc[1]
    if before.valid == 0 or after.valid == 0:
        return (f'Am Servicetag liegen {german_number(day.valid)} gültige Messpunkte vor. '
                f'Vorher sind es {german_number(before.valid)}, nachher {german_number(after.valid)}. '
                'Mindestens ein Vergleichsfenster ist leer; ein Vorher-Nachher-Unterschied kann dafür nicht berechnet werden.')
    difference = after['mean']-before['mean']
    direction = 'niedriger' if difference < 0 else 'höher' if difference > 0 else 'gleich'
    return (f'Der beobachtete Durchschnitt liegt nach dem Servicetag um {german_number(abs(difference),2)} '
            f'{column_unit} {direction}: vorher {german_number(before["mean"],2)}, '
            f'nachher {german_number(after["mean"],2)} {column_unit}. '
            f'Dafür stehen {german_number(before.valid)} bzw. {german_number(after.valid)} gültige Messpunkte zur Verfügung. '
            'Die Aussage gilt ausschließlich für die vorhandenen Messwerte, nicht für unbeobachtete Zeiten oder eine Reparaturwirkung.')

def coverage_rows(comparison, day, days):
    records=[]
    for label,row,hours in [('Vorher',comparison.iloc[0],days*24),('Servicetag',day,24),('Nachher',comparison.iloc[1],days*24)]:
        observed=int(row.observed_hours)
        records.append({'Zeitraum':label,'Gültige Messpunkte':int(row.valid),
                        'Stunden mit Messpunkten':observed,'Stunden ohne Messpunkte':hours-observed})
    return pd.DataFrame(records)

def inputs_fingerprint(source, files):
    """Aktualitätskennung, kein Ersatz für fachliche Datenvalidierung."""
    records=[(str(Path(p).resolve()),Path(p).stat().st_size,Path(p).stat().st_mtime_ns) for p in sorted(files.path)]
    digest=hashlib.sha256(Path(source).read_bytes())
    digest.update(json.dumps(records).encode('utf-8'))
    return digest.hexdigest()

def read_test_report(root):
    root=Path(root);path=root/'docs/testlauf_postgresql.xml'
    if not path.exists():path=root/'docs/testlauf_praxis.xml'
    if not path.exists():return None
    sources=[root/'app.py',*root.glob('servicepulse/*.py'),*root.glob('tests/*.py')]
    if any(p.stat().st_mtime>path.stat().st_mtime for p in sources):return None
    try:
        suites=list(ET.parse(path).getroot().iter('testsuite'))
        result={key:sum(int(s.get(key,'0')) for s in suites) for key in ['tests','failures','errors','skipped']}
        result['passed']=result['tests']-result['failures']-result['errors']-result['skipped']
        return result
    except (ET.ParseError,ValueError,OSError):return None
