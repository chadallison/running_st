import math
from datetime import datetime, timedelta
import altair as alt
import polars as pl
import streamlit as st


st.set_page_config(page_title = "Chad's Running Report", layout = "wide")

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
distance = row[most_recent_run.columns.index("distance")]
pace_float = row[most_recent_run.columns.index("pace")]
elevation = row[most_recent_run.columns.index("elevation")]
date_obj = row[most_recent_run.columns.index("date")]
shoe = row[most_recent_run.columns.index("shoe")]
pace_min = int(math.floor(pace_float))
pace_sec = int(round((pace_float - pace_min) * 60))
pace_str = f"{pace_min}:{pace_sec:02d}"
date_str = date_obj.strftime("%a, %b %d, %Y")

st.title("Chad's Running Report")
st.markdown("---")

st.subheader("Most Recent Run")
st.markdown(
    f"Date: **{date_str}**  \n"
    f"**{distance:.2f} miles** @ **{pace_str} min/mi** pace  \n"
    f"Elevation Gain: **{int(elevation)} ft**  \n"
    f"Shoe: **{shoe}**"
)
st.markdown("---")

total_dist = df.select(pl.col("distance")).sum().item()
run_cnt = df.height
avg_dist = total_dist / run_cnt

total_time = df.select(pl.col("time")).sum().item()
total_seconds = int(total_time * 60)
days = total_seconds // 86400
hours = (total_seconds % 86400) // 3600
minutes = (total_seconds % 3600) // 60
seconds = total_seconds % 60
formatted_time = f"{days}d {hours}h {minutes}m {seconds}s"

st.subheader("All-Time Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Distance", f"{total_dist:,.2f} mi")
col2.metric("Number of Runs", f"{run_cnt:,d}")
col3.metric("Avg Distance", f"{avg_dist:,.2f} mi")
col4.metric("Total Time", formatted_time)
st.markdown("---")

one_year_ago = datetime.today() - timedelta(days = 365)
total_dist_365_days = df.filter(pl.col("date") >= one_year_ago).select(pl.col("distance")).sum().item()

current_yr = datetime.now().year
this_year_dist = df.filter(pl.col("date").dt.year() == current_yr).select(pl.col("distance")).sum().item()

current_month = datetime.now().month
this_month_dist = df.filter(pl.col("date").dt.year() == current_yr).filter(pl.col("date").dt.month() == current_month).select(pl.col("distance")).sum().item()

thirty_days_ago = datetime.today() - timedelta(days = 30)
total_dist_30_days = df.filter(pl.col("date") >= thirty_days_ago).select(pl.col("distance")).sum().item()

st.subheader("Recent Performance")
col5, col6, col7, col8 = st.columns(4)
col5.metric("Past 365 Days", f"{total_dist_365_days:,.2f} mi")
col6.metric(f"{current_yr} YTD", f"{this_year_dist:,.2f} mi")
col7.metric("This Month", f"{this_month_dist:,.2f} mi")
col8.metric("Past 30 Days", f"{total_dist_30_days:,.2f} mi")
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

shoe_df = recent_shoes_agg.to_pandas()

chart = (
    alt.Chart(shoe_df)
    .mark_bar()
    .encode(
        x = alt.X("total_distance", title = "Total Distance (mi)"),
        y = alt.Y("shoe", sort = "-x", title = "Shoe"),
        color = alt.value("#4a6154"),
        tooltip = [
            alt.Tooltip("run_count", title = "Runs"),
            alt.Tooltip("total_distance", title = "Total Distance (mi)", format = ".2f"),
            alt.Tooltip("avg_distance", title = "Avg Distance (mi)", format = ".2f"),
            alt.Tooltip("max_distance", title = "Max Distance (mi)", format = ".2f"),
            alt.Tooltip("time_hours", title = "Total Time (hrs)", format = ".2f")
        ]
    )
    .properties(height = 300)
)

st.subheader("Shoe-Level Summary (Past 2 Months)")
st.altair_chart(chart, use_container_width = True)
st.markdown("---")
