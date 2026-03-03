from datetime import datetime, timedelta
import polars as pl
import streamlit as st

st.set_page_config(page_title = "Chad's Running Report", layout = "wide")

sheet_id = "1oBUbxvufTpkGjnDgfadvUeU9KMo7o71Iu0ykJwERzMc"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Sheet1"

df = (
    pl.read_csv(csv_url)
    .drop("run")
    .with_columns(pl.col("date").str.strptime(pl.Date, "%m-%d-%Y"))
    .filter((pl.col("distance") >= 1) & (pl.col("elevation_per_mile") <= 250))
)

def fmt_pace(decimal_minutes):
    minutes = int(decimal_minutes)
    seconds = round((decimal_minutes - minutes) * 60)
    return f"{minutes}:{seconds:02d} min/mi"

def fmt_time(decimal_minutes):
    total_seconds = int(round(decimal_minutes * 60))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h}:{m:02d}:{s:02d}"

# most recent run
mrr = df.row(-1)
mrr_date, mrr_dist, mrr_pace, mrr_time, mrr_cal, mrr_elev, mrr_hr, mrr_shoe, _ = mrr

st.title("Chad's Running Report")
st.subheader(f"Most Recent Run — {mrr_date}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Distance", f"{mrr_dist} mi")
c2.metric("Total Time", fmt_time(mrr_time))
c3.metric("Avg. Pace", fmt_pace(mrr_pace))
c4.metric("Elevation Gain", f"{mrr_elev} ft")
c5.metric("Avg. Heart Rate", f"{mrr_hr} bpm")
c6.metric("Shoe", mrr_shoe)

st.divider()

# rolling windows
today_dt = datetime.today().date()

def window_stats(days):
    cutoff = today_dt - timedelta(days=days)
    sub = df.filter(pl.col("date") >= cutoff)
    dist = round(sub["distance"].sum(), 2)
    total_time = sub["time"].sum()
    pace = total_time / dist if dist > 0 else 0.0
    runs = sub.shape[0]
    return dist, total_time, pace, runs

def show_window(label, days):
    dist, total_time, pace, runs = window_stats(days)
    st.markdown(f"### {label}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distance", f"{dist} mi")
    c2.metric("Total Time", fmt_time(total_time))
    c3.metric("Avg. Pace", fmt_pace(pace))
    c4.metric("Runs", runs)

show_window("Past 7 Days", 7)
st.divider()
show_window("Past 30 Days", 30)
st.divider()
show_window("Past 90 Days", 90)

st.divider()

# shoe summary
st.markdown("### Shoe Summary")

shoe_stats = (
    df
    .group_by("shoe")
    .agg([
        pl.col("distance").sum().alias("total_miles"),
        pl.col("time").sum().alias("total_time"),
        pl.col("distance").count().alias("runs"),
        pl.col("date").max().alias("last_run"),
    ])
    .with_columns((pl.col("total_time") / pl.col("total_miles")).alias("avg_pace"))
    .filter(pl.col("total_miles") >= 10)
)

# get 5 most recently used shoes
recent_shoes = (
    df
    .group_by("shoe")
    .agg(pl.col("date").max().alias("last_run"))
    .sort("last_run", descending = True)
    .head(5)
    .get_column("shoe")
    .to_list()
)

shoe_stats = (
    shoe_stats
    .filter(pl.col("shoe").is_in(recent_shoes))
    .sort("last_run", descending = True)
)

for row in shoe_stats.iter_rows(named = True):
    st.markdown(f"**{row['shoe']}**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Runs", row["runs"])
    c2.metric("Total Miles", f"{round(row['total_miles'], 1)} mi")
    c3.metric("Total Time", fmt_time(row["total_time"]))
    c4.metric("Avg. Pace", fmt_pace(row["avg_pace"]))
    c5.metric("Last Run", str(row["last_run"]))
    st.markdown("")

st.divider()