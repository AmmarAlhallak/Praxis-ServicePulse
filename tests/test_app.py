from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

def test_real_app_default_and_empty_filters():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value=='46'
    app.checkbox(key='all_devices').uncheck().run()
    assert not app.exception
    assert app.metric[0].value=='0'

def test_app_excel_only(tmp_path, monkeypatch):
    import servicepulse.measurements as measurements
    original=measurements.inventory
    monkeypatch.setattr(measurements,'inventory',lambda root:original(tmp_path))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value=='46'

def test_real_device_windows_and_source_warning():
    root = Path(__file__).resolve().parents[1]
    if not all((root / f'data/raw/{model}/{device}_temp.parquet').exists()
               for model,device in [('Revco','806030'),('Revco','806018'),('Haier','809169')]):
        pytest.skip('Optionale reale Parquet-Dateien fehlen; Download siehe docs/datenimport.md')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    def select_device(value):
        widget=app.selectbox(key='measurement_device')
        widget.set_value(value).run()
        assert not app.exception
        assert not app.error
    select_device('806030')
    assert any('Keine Messwerte' in w.value for w in app.warning)==False  # Servicetag selbst hat 24 Werte.
    select_device('806018')
    assert any('806022' in w.value for w in app.warning)
    select_device('809169')
    assert any('Kein Serviceeintrag' in x.value for x in app.info)
    assert not any('Keine Messwerte' in w.value for w in app.warning)
