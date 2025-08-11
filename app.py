import streamlit as st
import polars as pl
from datetime import datetime, timedelta
import math

st.title("Chad's Running Report")
st.markdown("---")

sheet_id = "1oBUbxvufTpkGjnDgfadvUeU9KMo7o71Iu0ykJwERzMc"
sheet_name = "Sheet1"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

df = (
    pl.read_csv(csv_url)
    .drop("run")
    .with_columns(pl.col("date").str.strptime(pl.Date, "%m-%d-%Y"))
)

most_recent_run = df.sort(pl.col("date"), descending = True).head(1)
row = most_recent_run.row(0)
distance = row[most_recent_run.columns.index("distance") ]
pace_float = row[most_recent_run.columns.index("pace") ]
elevation = row[most_recent_run.columns.index("elevation") ]
date_obj = row[most_recent_run.columns.index("date") ]
shoe = row[ most_recent_run.columns.index("shoe") ]
pace_min = int(math.floor(pace_float))
pace_sec = int(round((pace_float - pace_min) * 60))
pace_str = f"{pace_min}:{pace_sec:02d}"
date_str = date_obj.strftime("%a, %b %d, %Y")

st.header("Most recent run")
st.subheader(
    f"{distance:.2f} miles @ {pace_str} min/mi pace with "
    f"{int(elevation)} feet of elevation gain on {date_str} in the {shoe}"
)

st.markdown("---")

total_dist = df.select(pl.col("distance")).sum().item()
st.header("Total distance, all time")
st.subheader(f"{total_dist:,.2f} miles")
st.markdown("---")

run_cnt = df.height
st.header("Number of runs, all time")
st.subheader(f"{run_cnt:,d}")
st.markdown("---")

avg_dist = total_dist / run_cnt
st.header("Avg. distance per run, all time")
st.subheader(f"{avg_dist:,.2f} miles")
st.markdown("---")

total_time = df.select(pl.col("time")).sum().item()
total_seconds = int(total_time * 60)
days = total_seconds // 86400
hours = (total_seconds % 86400) // 3600
minutes = (total_seconds % 3600) // 60
seconds = total_seconds % 60
formatted = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
st.subheader(f"Total time running, all time: {formatted}")
st.markdown("---")

one_year_ago = datetime.today() - timedelta(days = 365)
total_dist_365_days = df.filter(pl.col("date") >= one_year_ago).select(pl.col("distance")).sum().item()
st.subheader(f"Total distance, past 365 days: {total_dist_365_days:,.2f} miles")
st.markdown("---")

current_yr = datetime.now().year
this_year_dist = df.filter(pl.col("date").dt.year() == current_yr).select(pl.col("distance")).sum().item()
st.subheader(f"Total distance, {current_yr}: {this_year_dist:,.2f} miles")
st.markdown("---")

current_month = datetime.now().month
this_month_dist = df.filter(pl.col("date").dt.year() == current_yr).filter(pl.col("date").dt.month() == current_month).select(pl.col("distance")).sum().item()
st.subheader(f"Total distance, this month: {this_month_dist:,.2f} miles")
st.markdown("---")

thirty_days_ago = datetime.today() - timedelta(days = 30)
total_dist_30_days = df.filter(pl.col("date") >= thirty_days_ago).select(pl.col("distance")).sum().item()
st.subheader(f"Total distance, past 30 days: {total_dist_30_days:,.2f} miles")
st.markdown("---")

recent_shoes = (
    df
    .filter(pl.col("date") >= (datetime.today() - timedelta(days = 60)))
    .select(pl.col("shoe"))
    .unique()
    .to_series()
    .to_list()
)

recent_shoes_agg = (
    df
    .filter(pl.col("shoe").is_in(recent_shoes))
    .group_by(pl.col("shoe"))
    .agg(
        pl.col("shoe").count().alias("run_count"),
        pl.col("distance").sum().alias("total_distance"),
        pl.col("distance").mean().round(2).alias("avg_distance"),
        pl.col("distance").max().alias("max_distance"),
        pl.col("time").max().alias("max_time_minutes"),
        (pl.col("time").sum() / 60).round(2).alias("time_hours")
    )
    .sort(pl.col("total_distance"), descending = True)
)

st.subheader("Shoe-level summary (shoes used in past two months)")
st.dataframe(recent_shoes_agg)
st.markdown("---")