"""Reproduzierbare Rohdatenstichproben und Abdeckung dokumentierter Servicetage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json

import duckdb
import pandas as pd

from servicepulse.faults import read_faults
from servicepulse.measurements import offsets, window_comparison
from servicepulse.raw import read_haier_temperature, read_revco_temperature


def main():
    root = Path(__file__).resolve().parents[1]
    clock = offsets(root / "research/reference/data/raw_data/other_data/time_offsets.csv")
    revpath = (
        root / "research/samples/data/raw_data/Revco/806018/temp/240365_tempdatalog_202210.dat"
    )
    haierpath = root / "research/samples/data/raw_data/Haier/809169/lowtemperbox.db"
    rev, rr = read_revco_temperature(revpath, "806018", clock["806018"])
    _, hr = read_haier_temperature(haierpath, "809169", clock["809169"])
    with duckdb.connect() as con:
        con.register("sample", rev[["Datetime", "RTD"]])
        rr["parquet_comparison"] = con.execute(
            """SELECT count(*) FROM sample s JOIN read_parquet(?) p
          ON s.Datetime=p.Datetime AND abs(s.RTD-p.RTD)<0.001""",
            [str(root / "data/raw/Revco/806018_temp.parquet")],
        ).fetchone()[0]
    output = root / "data/processed"
    output.mkdir(exist_ok=True, parents=True)
    (output / "raw_sample_audit.json").write_text(
        json.dumps({"Revco": rr, "Haier": hr}, indent=2), encoding="utf-8"
    )
    rows = []
    with duckdb.connect() as con:
        for row in read_faults(root / "fault_summary_R1.xlsx").itertuples():
            path = root / "data/raw/Revco" / f"{row.device_id}_temp.parquet"
            date = row.event_date
            n = con.execute(
                "SELECT count(*) FROM read_parquet(?) WHERE Datetime >= ? AND Datetime < ?",
                [str(path), date.to_pydatetime(), (date + pd.Timedelta(days=1)).to_pydatetime()],
            ).fetchone()[0]
            comp = window_comparison(path, "RTD", date)
            rows.append(
                dict(
                    source_row=row.source_row,
                    device_id=row.device_id,
                    date=str(date.date()),
                    category=row.category,
                    day_rows=n,
                    before_rows=int(comp.iloc[0]["rows"]),
                    after_rows=int(comp.iloc[1]["rows"]),
                    before_mean=comp.iloc[0]["mean"],
                    after_mean=comp.iloc[1]["mean"],
                )
            )
    pd.DataFrame(rows).to_csv(output / "event_coverage.csv", index=False)
    print("Rohdatenstichproben und Serviceabdeckung gespeichert.")


if __name__ == "__main__":
    main()
