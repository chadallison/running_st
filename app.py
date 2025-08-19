import math
from datetime import datetime, timedelta
import altair as alt
import pandas as pd
import polars as pl
import streamlit as st

st.set_page_config(page_title = "Chad's Running Report", layout = "wide")

# google sheet info and csv url for reading data
sheet_id = "1oBUbxvufTpkGjnDgfadvUeU9KMo7o71Iu0ykJwERzMc"
sheet_name = "Sheet1"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

# load data from csv, parse date column as date type, drop 'run' column
df = (
    pl.read_csv(csv_url)
    .drop("run")
    .with_columns(pl.col("date").str.strptime(pl.Date, "%m-%d-%Y"))
    .with_columns((pl.col("elevation") / pl.col("distance")).alias("elevation_per_mile"))
    .filter(pl.col("distance") >= 1)
    .filter(pl.col("elevation_per_mile") <= 250)
)

# get the most recent run row for summary display
most_recent_run = df.sort(pl.col("date"), descending = True).head(1)
row = most_recent_run.row(0)
distance = row[most_recent_run.columns.index("distance")]
pace_float = row[most_recent_run.columns.index("pace")]
elevation = row[most_recent_run.columns.index("elevation")]
date_obj = row[most_recent_run.columns.index("date")]
shoe = row[most_recent_run.columns.index("shoe")]

# convert pace float (e.g., 8.5) to min:sec string (e.g., 8:30)
pace_min = int(math.floor(pace_float))
pace_sec = int(round((pace_float - pace_min) * 60))
pace_str = f"{pace_min}:{pace_sec:02d}"

# format date for display
date_str = date_obj.strftime("%a, %b %d, %Y")

# app title and separator
st.title("Chad's Running Report")
st.markdown("---")

# display most recent run details
st.subheader("Most Recent Run")
st.markdown(
    f"Date: **{date_str}**  \n"
    f"**{distance:.2f} miles** @ **{pace_str} min/mi** pace  \n"
    f"Elevation Gain: **{int(elevation)} ft**  \n"
    f"Shoe: **{shoe}**"
)
st.markdown("---")

# calculate total stats for all time
total_dist = df.select(pl.col("distance")).sum().item()
run_cnt = df.height
avg_dist = total_dist / run_cnt

# calculate total running time and convert seconds to days/hours/minutes/seconds
total_time = df.select(pl.col("time")).sum().item()
total_seconds = int(total_time * 60)
days = total_seconds // 86400
hours = (total_seconds % 86400) // 3600
minutes = (total_seconds % 3600) // 60
seconds = total_seconds % 60
formatted_time = f"{days}d {hours}h {minutes}m {seconds}s"

# display all-time stats in four columns
st.subheader("All-Time Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Distance", f"{total_dist:,.2f} mi")
col2.metric("Number of Runs", f"{run_cnt:,d}")
col3.metric("Avg Distance", f"{avg_dist:,.2f} mi")
col4.metric("Total Time", formatted_time)
st.markdown("---")

# calculate recent performance metrics for various recent time windows
one_year_ago = datetime.today() - timedelta(days = 365)
total_dist_365_days = (
    df.filter(pl.col("date") >= one_year_ago)
      .select(pl.col("distance")).sum().item()
)

current_yr = datetime.now().year
this_year_dist = (
    df.filter(pl.col("date").dt.year() == current_yr)
      .select(pl.col("distance")).sum().item()
)

current_month = datetime.now().month
this_month_dist = (
    df.filter(pl.col("date").dt.year() == current_yr)
      .filter(pl.col("date").dt.month() == current_month)
      .select(pl.col("distance")).sum().item()
)

thirty_days_ago = datetime.today() - timedelta(days = 30)
total_dist_30_days = (
    df.filter(pl.col("date") >= thirty_days_ago)
      .select(pl.col("distance")).sum().item()
)

seven_days_ago = datetime.today() - timedelta(days = 7)
total_dist_7_days = (
    df.filter(pl.col("date") >= seven_days_ago)
      .select(pl.col("distance")).sum().item()
)

# display recent performance metrics in five columns
st.subheader("Recent Performance")
col5, col6, col7, col8, col9 = st.columns(5)
col5.metric("Past 365 Days", f"{total_dist_365_days:,.2f} mi")
col6.metric(f"{current_yr} YTD", f"{this_year_dist:,.2f} mi")
col7.metric("This Month", f"{this_month_dist:,.2f} mi")
col8.metric("Past 30 Days", f"{total_dist_30_days:,.2f} mi")
col9.metric("Past 7 Days", f"{total_dist_7_days:,.2f} mi")
st.markdown("---")


# get list of shoes used in the last 60 days
recent_shoes = (
    df
    .filter(pl.col("date") >= (datetime.today() - timedelta(days = 60)))
    .select(pl.col("shoe"))
    .unique()
    .to_series()
    .to_list()
)

# aggregate shoe data for recent shoes
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

# convert aggregated shoe data to pandas for Altair plotting
shoe_df = recent_shoes_agg.to_pandas()

# create bar chart for shoe-level summary
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
            alt.Tooltip("avg_distance", title = "Avg. Distance (mi)", format = ".2f"),
            alt.Tooltip("max_distance", title = "Max Distance (mi)", format = ".2f"),
            alt.Tooltip("time_hours", title = "Total Time (hrs)", format = ".2f")
        ]
    )
    .properties(height = 300)
)

# display shoe-level summary chart
st.subheader("Shoe-Level Summary (Shoes Used in Past Two Months)")
st.altair_chart(chart, use_container_width = True)
st.markdown("---")

# filter data for current year
df_year = df.filter(pl.col("date").dt.year() == datetime.now().year)

# add column for week start date (monday) by subtracting weekday from date
df_year = df_year.with_columns(
    (pl.col("date").cast(pl.Datetime) - pl.duration(days = pl.col("date").dt.weekday())).alias("week_start")
)

# aggregate total distance by week
weekly_distance = (
    df_year
    .group_by("week_start")
    .agg(pl.col("distance").sum().alias("total_distance"))
    .sort("week_start")
)

# convert weekly aggregated data to pandas for Altair
weekly_distance_df = weekly_distance.to_pandas()

# create bar chart for weekly distance instead of line chart
bar_chart = (
    alt.Chart(weekly_distance_df)
    .mark_bar(color = "#4a6154", size = 25)
    .encode(
        x = alt.X(
            "week_start:T",
            title = "Week Starting",
            axis = alt.Axis(format = "%b %d", labelAngle = -45, tickCount = 20)
        ),
        y = alt.Y("total_distance", title = "Total Distance (mi)"),
        tooltip = [
            alt.Tooltip("week_start:T", title = "Week Starting", format = "%Y-%m-%d"),
            alt.Tooltip("total_distance", title = "Distance (mi)", format = ".2f")
        ]
    )
    .properties(
        width = 700,
        height = 350
    )
)

# display weekly distance bar chart
st.subheader(f"Weekly Distance for {datetime.now().year}")
st.altair_chart(bar_chart, use_container_width = True)
st.markdown("---")

# create new column with year-month string for monthly aggregation
df_monthly = df.with_columns(
    pl.col("date").dt.strftime("%Y-%m").alias("year_month")
)

# aggregate total distance by month
monthly_distance = (
    df_monthly
    .group_by("year_month")
    .agg(pl.col("distance").sum().alias("total_distance"))
    .sort("year_month")
)

# convert monthly aggregated data to pandas for Altair and date range handling
monthly_distance_df = monthly_distance.to_pandas()

# convert year_month string to datetime for proper date handling
monthly_distance_df["year_month_dt"] = pd.to_datetime(monthly_distance_df["year_month"], format = "%Y-%m")

# create a full monthly date range from min to max to include months with zero distance
full_range = pd.date_range(
    start = monthly_distance_df["year_month_dt"].min(),
    end = monthly_distance_df["year_month_dt"].max(),
    freq = "MS"
)

# reindex to full monthly range and fill missing distances with 0
monthly_distance_df = (
    monthly_distance_df
    .set_index("year_month_dt")
    .reindex(full_range)
    .rename_axis("year_month_dt")
    .reset_index()
)

monthly_distance_df["total_distance"] = monthly_distance_df["total_distance"].fillna(0)

# create monthly distance bar chart
monthly_chart = (
    alt.Chart(monthly_distance_df)
    .mark_bar(color = "#4a6154", size = 10)
    .encode(
        x = alt.X(
            "year_month_dt:T",
            title = "Month",
            axis = alt.Axis(format = "%b %Y", labelAngle = -45, tickCount = 20)
        ),
        y = alt.Y("total_distance", title = "Total Distance (mi)"),
        tooltip = [
            alt.Tooltip("year_month_dt:T", title = "Month", format = "%b %Y"),
            alt.Tooltip("total_distance", title = "Distance (mi)", format = ".2f")
        ]
    )
    .properties(
        width = 700,
        height = 350
    )

)

# display monthly distance bar chart
st.subheader("Monthly Distance, All Time")
st.altair_chart(monthly_chart, use_container_width = True)
st.markdown("---")

# filter data for current year
df_year_elev = df.filter(pl.col("date").dt.year() == datetime.now().year)

# add week_start column (Monday) by subtracting weekday from date
df_year_elev = df_year_elev.with_columns(
    (pl.col("date").cast(pl.Datetime) - pl.duration(days = pl.col("date").dt.weekday())).alias("week_start")
)

# aggregate total elevation gain by week (in feet)
weekly_elevation = (
    df_year_elev
    .group_by("week_start")
    .agg(pl.col("elevation").sum().alias("total_elevation_ft"))
    .sort("week_start")
)

# convert to miles and calculate cumulative
weekly_elevation = weekly_elevation.with_columns(
    (pl.col("total_elevation_ft") / 5280).alias("total_elevation_mi"),
    (pl.col("total_elevation_ft") / 5280).cum_sum().alias("cumulative_elevation_mi")
)

# convert to pandas for Altair
weekly_elevation_df = weekly_elevation.to_pandas()

# create cumulative elevation area chart (miles)
elev_chart = (
    alt.Chart(weekly_elevation_df)
    .mark_area(
        color = "#4a6154",
        opacity = 0.7
    )
    .encode(
        x = alt.X(
            "week_start:T",
            title = "Week Starting",
            axis = alt.Axis(format = "%b %d", labelAngle = -45, tickCount = 20)
        ),
        y = alt.Y("cumulative_elevation_mi", title = "Cumulative Elevation Gain (mi)"),
        tooltip = [
            alt.Tooltip("week_start:T", title = "Week Starting", format = "%Y-%m-%d"),
            alt.Tooltip("total_elevation_mi", title = "Weekly Gain (mi)", format = ".2f"),
            alt.Tooltip("cumulative_elevation_mi", title = "Cumulative Gain (mi)", format = ".2f")
        ]
    )
    .properties(
        width = 700,
        height = 350
    )
)

st.subheader(f"Cumulative Weekly Elevation Gain for {datetime.now().year}")
st.altair_chart(elev_chart, use_container_width = True)
st.markdown("---")

res_year = df.filter(pl.col("date").dt.year() == current_yr)

res_year_df = res_year.to_pandas()
res_year_df["pace_str"] = (
    res_year_df["pace"].astype(int).astype(str)
    + ":"
    + ((res_year_df["pace"] % 1) * 60).round(0).astype(int).astype(str).str.zfill(2)
)

pace_min, pace_max = res_year_df["pace"].min(), res_year_df["pace"].max()
distance_min, distance_max = res_year_df["distance"].min(), res_year_df["distance"].max()
mean_distance, mean_pace = res_year_df["distance"].mean(), res_year_df["pace"].mean()

scatter = (
    alt.Chart(res_year_df)
    .mark_circle(size = 80, opacity = 0.75)
    .encode(
        x = alt.X(
            "distance",
            title = "Distance (mi.)",
            scale = alt.Scale(domain = [distance_min, distance_max])
        ),
        y = alt.Y(
            "pace",
            scale = alt.Scale(domain = [pace_min, pace_max]),
            axis = alt.Axis(
                title = "Pace (mm:ss)",
                labelExpr = "floor(datum.value) + ':' + format(round((datum.value % 1)*60), '02')"
            )
        ),
        color = alt.Color(
            "shoe",
            legend = alt.Legend(title = "Shoe")
        ),
        tooltip = [
            "date:T",
            "distance",
            alt.Tooltip("pace_str", title = "pace"),
            "elevation"
        ]
    )
)

mean_distance_line = alt.Chart(pd.DataFrame({"mean_distance": [mean_distance]})).mark_rule(
    color = "white",
    strokeDash = [5, 5]
).encode(x = "mean_distance:Q")

mean_pace_line = alt.Chart(pd.DataFrame({"mean_pace": [mean_pace]})).mark_rule(
    color = "white",
    strokeDash = [5, 5]
).encode(y = "mean_pace:Q")

scatter_chart = (
    scatter
    + mean_distance_line
    + mean_pace_line
).properties(
    width = 700,
    height = 400
)

st.subheader(f"Distance vs. Pace ({current_yr})")
st.altair_chart(scatter_chart, use_container_width = True)
st.markdown("---")

st.subheader("All Runs")

res = (
    df
    .with_columns([
        pl.col("elevation_per_mile").round(2),
        (
            pl.col("pace").floor().cast(pl.Int32).cast(pl.Utf8)
            + ":" +
            (((pl.col("pace") % 1) * 60).round(0).cast(pl.Int32).cast(pl.Utf8).str.zfill(2))
        ).alias("pace"),
        (
            pl.col("time").floor().cast(pl.Int32).cast(pl.Utf8)
            + ":" +
            (((pl.col("time") % 1) * 60).round(0).cast(pl.Int32).cast(pl.Utf8).str.zfill(2))
        ).alias("time"),
        pl.col("date").cast(pl.Utf8)
    ])
    .select(["date", "distance", "pace", "time", "calories", "elevation", "bpm", "elevation_per_mile", "shoe"])
    .sort(pl.col("date"), descending = True)
)

st.dataframe(res)
st.markdown("---")

st.write("The data in this report is sourced from a Google Sheet which I manually update. The data is a mixture of activities from Nike Run Club, Strava, and Garmin. I have only recently purchased and begun wearing my Garmin watch, and plan to use it as my source-of-truth data moving forward.")
st.markdown("---")
