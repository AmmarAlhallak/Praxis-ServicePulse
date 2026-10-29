"""Integration mit den tatsächlich vorhandenen lokalen Daten, schreibgeschützt."""
from datetime import date
from pathlib import Path
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from scripts.check_local import check
from servicepulse.measurements import series_window, time_bounds, numeric_columns

ROOT = Path(__file__).resolve().parents[1]

def test_existing_duckdb_matches_excel_and_parquet_inventory():
    if not (ROOT/'data/processed/servicepulse.duckdb').exists():
        pytest.skip('Optionaler lokaler Build fehlt')
    result = check(ROOT)
    assert result['entries'] == 46
    assert result['devices'] == 24

def test_real_parquet_sql_against_independent_pandas_aggregation():
    path = ROOT/'data/raw/Revco/806279_temp.parquet'
    if not path.exists():
        pytest.skip('Optionale reale Messdatei fehlt')
    start, end = pd.Timestamp('2022-06-29'), pd.Timestamp('2022-06-30')
    raw = pd.read_parquet(path, columns=['Datetime','RTD'], filters=[('Datetime','>=',start),('Datetime','<',end)])
    expected = raw.groupby(raw.Datetime.dt.floor('h')).RTD.agg(['mean','min','max','count']).reset_index()
    actual = series_window(path,'RTD',start,end)
    assert not actual.empty
    pd.testing.assert_frame_equal(expected.set_axis(actual.columns,axis=1),actual,
                                  check_dtype=False,atol=1e-10,rtol=1e-10)
    assert 'State' not in numeric_columns(path)
    first,last = time_bounds(path)
    assert pd.Timestamp(first) < start < end < pd.Timestamp(last)

def test_combined_dashboard_filters_device_analysis_charts_and_reset():
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    app.checkbox(key='all_devices').uncheck()
    app.checkbox(key='all_categories').uncheck()
    app.checkbox(key='limit_service_dates').check().run()
    app.multiselect(key='devices').set_value(['806279'])
    app.multiselect(key='categories').set_value(['Refrigerant leakage'])
    app.date_input(key='service_start').set_value(date(2022,6,28))
    app.date_input(key='service_end').set_value(date(2022,6,28))
    app.run()
    assert not app.exception and not app.error
    assert [metric.value for metric in app.metric[:4]] == ['1','1','0','0']
    assert len(app.get('plotly_chart')) >= 4
    repeated = next(table.value for table in app.dataframe if set(table.value.columns)=={'Geräte-ID','Fehlerkategorie','Serviceeinträge'})
    assert repeated.empty
    specifications = [json.loads(chart.proto.spec) for chart in app.get('plotly_chart')]
    curves = [spec for spec in specifications if any(trace.get('name')=='Mittelwert' for trace in spec['data'])]
    if (ROOT/'data/raw/Revco/806279_temp.parquet').exists():
        assert len(curves)==1
        assert len(curves[0]['layout']['shapes'])==1
    next(button for button in app.button if button.label=='Alle Filter zurücksetzen').click().run()
    assert not app.exception and not app.error
    assert app.metric[0].value=='46'

def test_vscode_configs_use_project_environment():
    workspace=json.loads((ROOT/'ServicePulse.code-workspace').read_text(encoding='utf-8'))
    assert workspace['folders']==[{'path':'.'}]
    config=json.loads((ROOT/'.vscode/launch.json').read_text(encoding='utf-8'))['configurations'][0]
    assert config['module']=='streamlit'
    assert config['python']=='${workspaceFolder}/.venv/Scripts/python.exe'
    assert config['cwd']=='${workspaceFolder}'
