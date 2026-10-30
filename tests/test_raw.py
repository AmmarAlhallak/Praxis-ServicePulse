import pandas as pd

from servicepulse.raw import read_haier_temperature, read_revco_temperature


def test_revco_header_id_conflict_and_clock(tmp_path):
    path = tmp_path / "raw.dat"
    path.write_text("Unit Name : 654321\nDate\tTime\tRTD\n10/01/2022\t00:00:00\t-80\n")
    df, report = read_revco_temperature(path, "123456", pd.Timedelta(hours=1))
    assert report["identifier_conflict"]
    assert df.Datetime.item() == pd.Timestamp("2022-10-01 01:00:00")


def test_haier_timestamp_join_not_row_position(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing

    import pytest

    path = tmp_path / "test.db"
    with closing(sqlite3.connect(path)) as con:
        pd.DataFrame({"TIME": ["2022-01-01 00:00:01", "2022-01-01 00:06:01"]}).to_sql(
            "EACH_POINT_DATA_CHANGE", con, index=False
        )
        pd.DataFrame(
            {"TIME": ["2022-01-01 00:06:00", "2022-01-01 00:00:00"], "TEMPERATURE": [-81.0, -79.0]}
        ).to_sql("TEMPER_RECORD", con, index=False)
    connections = []
    original_connect = sqlite3.connect

    def record_connection(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", record_connection)
    df, report = read_haier_temperature(path, "123456")
    assert df.RTD.tolist() == [-79.0, -81.0]
    assert report["unmatched_rtd"] == 0
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connections[0].execute("SELECT 1")
