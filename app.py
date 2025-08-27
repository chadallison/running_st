import math
from datetime import datetime, timedelta
import altair as alt
import pandas as pd
import polars as pl
import streamlit as st

st.set_page_config(page_title = "Chad's Running Report", layout = "wide")

# -------- Helpers -------- #
def format_pace(pace_float):
    if pace_float is None or pd.isna(pace_float):
        return "-"
    pace_min = int(math.floor(pace_float))
    pace_sec = int(round((pace_float - pace_min) * 60))
    return f"{pace_min}:{pace_sec:02d}"

def format_time_minutes(total_minutes):
    if total_minutes is None or pd.isna(total_minutes):
        return "-"
    total_seconds = int(total_minutes * 60)
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{days}d {hours}h {minutes}m {seconds}s"

def section_break():
    st.markdown("---")

def sum_distance(df_filtered):
    return df_filtered.select(pl.col("distance")).sum().item()

def aggregate_by_period(df, date_col = "date", period = "week", sum_col = "distance"):
    if period == "week":
        df_agg = df.with_columns((pl.col(date_col).cast(pl.Datetime) - pl.duration(days = pl.col(date_col).dt.weekday())).alias("week_start"))
        group_col = "week_start"
        df_agg = df_agg.group_by(group_col).agg(pl.col(sum_col).sum().alias("total_distance")).sort(group_col).to_pandas()
    else:
        df_agg = df.with_columns(pl.col(date_col).dt.strftime("%Y-%m").alias("month"))
        df_agg = df_agg.group_by("month").agg(pl.col(sum_col).sum().alias("total_distance")).sort("month").to_pandas()
        df_agg["month_dt"] = pd.to_datetime(df_agg["month"], format = "%Y-%m")
        full_range = pd.date_range(df_agg["month_dt"].min(), df_agg["month_dt"].max(), freq = "MS")
        df_agg = df_agg.set_index("month_dt").reindex(full_range).rename_axis("month_dt").reset_index()
        df_agg["total_distance"] = df_agg["total_distance"].fillna(0)
    return df_agg

def plot_bar_chart(df_plot, x_col, y_col, x_title, y_title, width = 700, height = 350, tooltip_cols = None, color = "#4a6154", size = None, axis_format = None):
    tooltip_cols = tooltip_cols or []
    if axis_format:
        x_axis = alt.X(x_col + ":T", title = x_title, axis = alt.Axis(format = axis_format, labelAngle = -45, tickCount = 20))
    else:
        x_axis = alt.X(x_col + (":T" if "date" in x_col or "week" in x_col or "month" in x_col else ":Q"), title = x_title)
    mark_bar_args = {"color": color}
    if size is not None:
        mark_bar_args["size"] = size
    chart = (
        alt.Chart(df_plot)
        .mark_bar(**mark_bar_args)
        .encode(
            x = x_axis,
            y = alt.Y(y_col, title = y_title),
            tooltip = [alt.Tooltip(c, format = ".2f") if df_plot[c].dtype in [float, int] else alt.Tooltip(c) for c in tooltip_cols]
        )
        .properties(width = width, height = height)
    )
    return chart

# -------- Load Data -------- #
sheet_id = "1oBUbxvufTpkGjnDgfadvUeU9KMo7o71Iu0ykJwERzMc"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Sheet1"

df = (
    pl.read_csv(csv_url)
    .drop("run")
    .with_columns([
        pl.col("date").str.strptime(pl.Date, "%m-%d-%Y"),
        (pl.col("elevation") / pl.col("distance")).alias("elevation_per_mile")
    ])
    .filter((pl.col("distance") >= 1) & (pl.col("elevation_per_mile") <= 250))
)

today = datetime.today()
current_year = today.year

# -------- Precompute Filters -------- #
df_current_year = df.filter(pl.col("date").dt.year() == current_year)
df_past_365 = df.filter(pl.col("date") >= (today - timedelta(days = 365)))
df_past_30 = df.filter(pl.col("date") >= (today - timedelta(days = 30)))
df_past_7 = df.filter(pl.col("date") >= (today - timedelta(days = 7)))
df_current_month = df.filter((pl.col("date").dt.year() == current_year) & (pl.col("date").dt.month() == today.month))

# -------- Most Recent Run -------- #
row = df.sort(pl.col("date"), descending = True).row(0)
distance, pace_float, elevation, date_obj, shoe = [row[df.columns.index(c)] for c in ["distance", "pace", "elevation", "date", "shoe"]]

st.title("Chad's Running Report")
section_break()

st.subheader("Most Recent Run")
st.markdown(
    f"Date: **{date_obj.strftime('%a, %b %d, %Y')}**  \n"
    f"**{distance:.2f} miles** @ **{format_pace(pace_float)} min/mi** pace  \n"
    f"Elevation Gain: **{int(elevation)} ft**  \n"
    f"Shoe: **{shoe}**"
)
section_break()

# -------- All-Time Stats -------- #
total_dist = df.select(pl.col("distance")).sum().item()
run_cnt = df.height
avg_dist = total_dist / run_cnt
total_time = df.select(pl.col("time")).sum().item()

st.subheader("All-Time Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Distance", f"{total_dist:,.2f} mi")
col2.metric("Number of Runs", f"{run_cnt:,d}")
col3.metric("Avg Distance", f"{avg_dist:,.2f} mi")
col4.metric("Total Time", format_time_minutes(total_time))
section_break()

# -------- Recent Performance -------- #
recent_metrics = {
    "Past 365 Days": df_past_365,
    f"{current_year} YTD": df_current_year,
    "This Month": df_current_month,
    "Past 30 Days": df_past_30,
    "Past 7 Days": df_past_7
}

st.subheader("Recent Performance")
cols = st.columns(len(recent_metrics))
for col, (label, df_filtered) in zip(cols, recent_metrics.items()):
    col.metric(label, f"{sum_distance(df_filtered):,.2f} mi")
section_break()

# -------- Shoe-Level Summary (past 60 days) -------- #
recent_shoes = df.filter(pl.col("date") >= (today - timedelta(days = 60))).select(pl.col("shoe")).unique().to_series().to_list()
shoe_df = (
    df.filter(pl.col("shoe").is_in(recent_shoes))
    .group_by("shoe")
    .agg([
        pl.len().alias("run_count"),
        pl.col("distance").sum().alias("total_distance"),
        pl.col("distance").mean().round(2).alias("avg_distance"),
        pl.col("distance").max().alias("max_distance"),
        (pl.col("time").sum() / 60).round(2).alias("time_hours")
    ])
    .sort("total_distance", descending = True)
    .to_pandas()
)
chart = plot_bar_chart(shoe_df, "total_distance", "shoe", "Total Distance (mi)", "Shoe",
                       tooltip_cols = ["run_count","total_distance","avg_distance","max_distance","time_hours"])
st.subheader("Shoe-Level Summary (Shoes Used in Past Two Months)")
st.altair_chart(chart, use_container_width = True)
section_break()

# -------- Weekly Distance Chart -------- #
weekly_df = aggregate_by_period(df_current_year, period = "week")
weekly_chart = plot_bar_chart(weekly_df, "week_start", "total_distance", "Week Starting", "Total Distance (mi)",
                              tooltip_cols = ["total_distance"], size = 25, axis_format = "%b %d")
st.subheader(f"Weekly Distance for {current_year}")
st.altair_chart(weekly_chart, use_container_width = True)
section_break()

# -------- Monthly Distance Chart -------- #
monthly_df = aggregate_by_period(df, period = "month")
monthly_chart = plot_bar_chart(monthly_df, "month_dt", "total_distance", "Month", "Total Distance (mi)",
                               tooltip_cols = ["total_distance"], size = 10, axis_format = "%b %Y")
st.subheader("Monthly Distance, All Time")
st.altair_chart(monthly_chart, use_container_width = True)
section_break()

# -------- Weekly Elevation Gain -------- #
df_elev_year = df_current_year.with_columns((pl.col("date").cast(pl.Datetime) - pl.duration(days = pl.col("date").dt.weekday())).alias("week_start"))
weekly_elev = df_elev_year.group_by("week_start").agg(pl.col("elevation").sum().alias("total_elevation_ft")).sort("week_start")
weekly_elev = weekly_elev.with_columns(
    (pl.col("total_elevation_ft") / 5280).alias("total_elevation_mi"),
    (pl.col("total_elevation_ft") / 5280).cum_sum().alias("cumulative_elevation_mi")
)
weekly_elev_df = weekly_elev.to_pandas()
elev_chart = (
    alt.Chart(weekly_elev_df)
    .mark_area(color = "#4a6154", opacity = 0.7)
    .encode(
        x = alt.X("week_start:T", title = "Week Starting", axis = alt.Axis(format = "%b %d", labelAngle = -45, tickCount = 20)),
        y = alt.Y("cumulative_elevation_mi", title = "Cumulative Elevation Gain (mi)"),
        tooltip = [
            alt.Tooltip("week_start:T", title = "Week Starting", format = "%Y-%m-%d"),
            alt.Tooltip("total_elevation_mi", title = "Weekly Gain (mi)", format = ".2f"),
            alt.Tooltip("cumulative_elevation_mi", title = "Cumulative Gain (mi)", format = ".2f")
        ]
    )
    .properties(width = 700, height = 350)
)
st.subheader(f"Cumulative Weekly Elevation Gain for {current_year}")
st.altair_chart(elev_chart, use_container_width = True)
section_break()

# -------- Distance vs Pace Scatter -------- #
res_year_df = df_current_year.to_pandas()
res_year_df["pace_str"] = res_year_df["pace"].apply(format_pace)
distance_min, distance_max = res_year_df["distance"].min(), res_year_df["distance"].max()
pace_min, pace_max = res_year_df["pace"].min(), res_year_df["pace"].max()
mean_distance, mean_pace = res_year_df["distance"].mean(), res_year_df["pace"].mean()

scatter = alt.Chart(res_year_df).mark_circle(size = 80, opacity = 0.75).encode(
    x = alt.X("distance", title = "Distance (mi.)", scale = alt.Scale(domain = [distance_min, distance_max])),
    y = alt.Y("pace", scale = alt.Scale(domain = [pace_min, pace_max]), axis = alt.Axis(title = "Pace (mm:ss)", labelExpr = "floor(datum.value) + ':' + format(round((datum.value % 1)*60), '02')")),
    color = alt.Color("shoe", legend = alt.Legend(title = "Shoe")),
    tooltip = ["date:T", "distance", alt.Tooltip("pace_str", title = "pace"), "elevation"]
)

mean_distance_line = alt.Chart(pd.DataFrame({"mean_distance": [mean_distance]})).mark_rule(color = "white", strokeDash = [5, 5]).encode(x = "mean_distance:Q")
mean_pace_line = alt.Chart(pd.DataFrame({"mean_pace": [mean_pace]})).mark_rule(color = "white", strokeDash = [5, 5]).encode(y = "mean_pace:Q")

scatter_chart = (scatter + mean_distance_line + mean_pace_line).properties(width = 700, height = 400)
st.subheader(f"Distance vs. Pace ({current_year})")
st.altair_chart(scatter_chart, use_container_width = True)
section_break()

# -------- Lifetime Shoe Summary -------- #
shoe_summary = (
    df.group_by("shoe")
    .agg([
        pl.len().alias("run_count"),
        pl.col("distance").sum().round(2).alias("total_distance"),
        (pl.col("time").sum() / 60).round(2).alias("total_time"),
        pl.col("distance").mean().round(2).alias("avg_distance"),
        pl.col("pace").mean().alias("avg_pace_float"),
        pl.col("distance").max().round(2).alias("max_distance"),
        pl.col("date").min().alias("first_run"),
        pl.col("date").max().alias("most_recent_date")
    ])
    .sort("total_distance", descending = True)
    .to_pandas()
)
shoe_summary["avg_pace"] = shoe_summary["avg_pace_float"].apply(format_pace)
shoe_summary["first_run"] = pd.to_datetime(shoe_summary["first_run"]).dt.strftime("%b %d, %Y")
shoe_summary["most_recent_date"] = pd.to_datetime(shoe_summary["most_recent_date"]).dt.strftime("%b %d, %Y")
shoe_summary = shoe_summary[["shoe", "run_count", "total_distance", "avg_distance", "max_distance", "total_time", "avg_pace", "first_run", "most_recent_date"]]

st.subheader("Lifetime Shoe Summary")
st.dataframe(shoe_summary, hide_index = True)
section_break()

# -------- All Runs Table -------- #
res = (
    df.with_columns([
        pl.col("elevation_per_mile").round(2),
        pl.col("date").cast(pl.Utf8)
    ])
    .select(["date", "distance", "pace", "time", "calories", "elevation", "bpm", "elevation_per_mile", "shoe"])
    .sort(pl.col("date"), descending = True)
).to_pandas()

res["pace"] = res["pace"].apply(format_pace)
res["time"] = res["time"].apply(format_pace)

st.subheader("All Runs")
st.dataframe(res, hide_index = True)
section_break()

st.write("The data in this report is sourced from a Google Sheet which I manually update. The data is a mixture of activities from Nike Run Club, Strava, and Garmin. I have only recently purchased and begun wearing my Garmin watch, and plan to use it as my source-of-truth data moving forward.")
section_break()
