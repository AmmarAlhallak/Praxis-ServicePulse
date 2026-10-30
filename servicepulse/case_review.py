"""Begrenzte Nachprüfung von Messlücken und Revco-Betriebskennzeichen."""
import duckdb
import pandas as pd

def review_temperature(path,start,end):
    params=[str(path),pd.Timestamp(start).to_pydatetime(),pd.Timestamp(end).to_pydatetime()]
    with duckdb.connect() as con:
        gaps=con.execute('''SELECT previous, Datetime AS next_time, epoch(Datetime-previous) AS seconds
          FROM (SELECT Datetime, lag(Datetime) OVER (ORDER BY Datetime) AS previous
          FROM read_parquet(?) WHERE Datetime>=? AND Datetime<?)
          WHERE Datetime-previous > INTERVAL '5 minutes' ORDER BY seconds DESC LIMIT 50''',params).df()
        daily=con.execute('''SELECT date_trunc('day',Datetime) AS day,count(*) AS rows,
          min(RTD) AS minimum,max(RTD) AS maximum,avg(RTD) AS mean,
          count(*)-count(DISTINCT Datetime) AS repeated_timestamps
          FROM read_parquet(?) WHERE Datetime>=? AND Datetime<? GROUP BY 1 ORDER BY 1''',params).df()
        warm=con.execute('''SELECT count(*) AS rows,min(Datetime) AS first_time,max(Datetime) AS last_time,
          min(RTD) AS minimum,max(RTD) AS maximum FROM read_parquet(?)
          WHERE Datetime>=? AND Datetime<? AND RTD>15''',params).df().iloc[0]
        states=con.execute('''SELECT State AS original_state,count(*) AS rows,
          count(*) FILTER(WHERE RTD>15) AS warm_rows,
          (State & 1) AS compressor_1_bit,((State >> 1) & 1) AS compressor_2_bit
          FROM read_parquet(?) WHERE Datetime>=? AND Datetime<? GROUP BY State ORDER BY State''',params).df()
    return gaps,daily,warm,states
