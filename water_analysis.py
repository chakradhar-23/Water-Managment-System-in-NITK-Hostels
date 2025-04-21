import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import timedelta
import requests
from io import StringIO
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Water Dashboard Interactive", layout="wide")
st.title("💧 Interactive Smart Water Dashboard (All Tanks)")

# 🔁 Auto-refresh every 20 seconds
st_autorefresh(interval=20000, limit=None, key="refresh")

# Tank configurations
TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

def fetch_data(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    df = pd.read_csv(StringIO(requests.get(url).text))
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df["smoothed"] = df["liters"].rolling(window=100, min_periods=1).mean()
    return df

def classify_trend(series, threshold=0.05):
    trends = []
    for i in range(len(series)):
        if i < 5 or pd.isna(series[i - 5]):
            trends.append("unknown")
            continue
        slope = series[i] - series[i - 5]
        if slope > threshold:
            trends.append("inflow")
        elif slope < -threshold:
            trends.append("usage")
        else:
            trends.append("both")
    return trends

def interactive_time_series(df_dict, column="smoothed"):
    df_all = pd.DataFrame()
    for tank, df in df_dict.items():
        temp = df[["created_at", column]].copy()
        temp["Tank"] = tank
        df_all = pd.concat([df_all, temp])
    fig = px.line(df_all, x="created_at", y=column, color="Tank", title="Water Level Trends (Smoothed)",
                  labels={"created_at": "Time", column: "Liters"}, height=500)
    st.plotly_chart(fig, use_container_width=True)

tank_dfs = {}
refill_candidates = []

for label, config in TANKS.items():
    st.subheader(f"📦 {label}")
    df = fetch_data(config["channel_id"], config["api_key"], config["capacity"])
    df["diff"] = df["smoothed"].diff()
    df["trend"] = classify_trend(df["smoothed"])
    df["inflow"] = df.apply(lambda row: row["diff"] if row["trend"] == "inflow" and row["diff"] > 0 else 0, axis=1)
    df["usage"] = df.apply(lambda row: -row["diff"] if row["trend"] == "usage" and row["diff"] < 0 else 0, axis=1)
    df["hour"] = df["created_at"].dt.floor("h")
    df["date"] = df["created_at"].dt.date
    tank_dfs[label] = df

    # Current level metric
    latest_level = df["liters"].iloc[-1]
    percentage = (latest_level / config["capacity"]) * 100
    st.metric(label="Current Water Level", value=f"{latest_level:.2f} L", delta=f"{percentage:.1f}%")

    # Hourly usage
    usage_hourly = df.groupby("hour")["usage"].sum().reset_index()
    fig1 = px.bar(usage_hourly, x="hour", y="usage", title="Hourly Usage", labels={"usage": "Liters"})
    st.plotly_chart(fig1, use_container_width=True)

    # Hourly inflow
    inflow_hourly = df.groupby("hour")["inflow"].sum().reset_index()
    fig2 = px.bar(inflow_hourly, x="hour", y="inflow", title="Hourly Inflow", labels={"inflow": "Liters"})
    st.plotly_chart(fig2, use_container_width=True)

    # Daily usage
    daily_usage = df.groupby("date")["diff"].sum()
    avg_daily = -daily_usage.clip(upper=0).mean()
    st.info(f"📅 Average Daily Usage: **{avg_daily:.2f} L/day**")

    # Peak usage hour
    if not usage_hourly.empty:
        peak_row = usage_hourly.loc[usage_hourly["usage"].idxmax()]
        st.success(f"⏰ Peak Usage Hour: {peak_row['hour']} — {peak_row['usage']:.2f} L")

    # Refill condition based on recent rate
    last_45 = df.tail(45)
    if len(last_45) > 1:
        time_diff = (last_45["created_at"].iloc[-1] - last_45["created_at"].iloc[0]).total_seconds()
        level_diff = last_45["smoothed"].iloc[-1] - last_45["smoothed"].iloc[0]
        rate = -level_diff / time_diff if time_diff > 0 else 0
        high_usage = rate > 0.05
        low_level = latest_level < 0.3 * config["capacity"]
        refill = high_usage and low_level
        if refill:
            st.error(f"🚨 Refill Recommended (Recent Rate: {rate:.3f} L/s)")
        else:
            st.success("✅ No Immediate Refill Required")

    # CSV Export
    st.download_button(f"Download {label} CSV", df.to_csv(index=False), file_name=f"{label.replace(' ', '_')}.csv")

# Combined Multi-Tank Chart
st.header("📊 Multi-Tank Water Level Comparison")
interactive_time_series(tank_dfs)

