import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import timedelta
import requests
from io import StringIO

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
    df["smoothed"] = df["liters"].rolling(window=50, min_periods=1).mean()
    return df[["created_at", "liters", "smoothed"]]

def classify_trend(series, threshold=0.01):
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

st.set_page_config(page_title="Water Dashboard Interactive", layout="wide")
st.title("💧 Interactive Smart Water Dashboard (All Tanks)")

tank_dfs = {}
refill_candidates = []

for label, config in TANKS.items():
    df = fetch_data(config["channel_id"], config["api_key"], config["capacity"])
    df["diff"] = df["smoothed"].diff()
    df["trend"] = classify_trend(df["smoothed"])
    df["inflow"] = df.apply(lambda row: row["diff"] if row["trend"] == "inflow" and row["diff"] > 0 else 0, axis=1)
    df["usage"] = df.apply(lambda row: -row["diff"] if row["trend"] == "usage" and row["diff"] < 0 else 0, axis=1)
    df["hour"] = df["created_at"].dt.floor("h")
    tank_dfs[label] = df

    # Check recent trend (last 15 minutes ~ 45 readings)
    recent = df.tail(45)
    avg_usage_rate = recent["usage"].mean()
    current_level = df["smoothed"].iloc[-1]
    if avg_usage_rate > 0.1 and current_level < config["capacity"] * 0.4:
        refill_candidates.append((label, current_level, avg_usage_rate))

# Smoothed Water Level Chart
st.subheader("📊 Smoothed Water Level (Interactive)")
combined = pd.concat([df.assign(Tank=label) for label, df in tank_dfs.items()])
fig = px.line(combined, x="created_at", y="smoothed", color="Tank", title="Smoothed Water Levels")
fig.update_layout(xaxis_title="Time", yaxis_title="Liters", height=500)
st.plotly_chart(fig, use_container_width=True)

# Hourly Usage Charts
st.subheader("📉 Hourly Usage (Liters)")
for label, df in tank_dfs.items():
    usage_hourly = df.groupby("hour")["usage"].sum().reset_index()
    fig = px.bar(usage_hourly, x="hour", y="usage", title=f"{label} - Hourly Usage", labels={"usage": "Liters"})
    st.plotly_chart(fig, use_container_width=True)

# Hourly Inflow Charts
st.subheader("💧 Hourly Inflow (Liters)")
for label, df in tank_dfs.items():
    inflow_hourly = df.groupby("hour")["inflow"].sum().reset_index()
    fig = px.bar(inflow_hourly, x="hour", y="inflow", title=f"{label} - Hourly Inflow", labels={"inflow": "Liters"})
    st.plotly_chart(fig, use_container_width=True)

# CSV Export
st.subheader("📤 Export Data")
for label, df in tank_dfs.items():
    st.download_button(f"Download {label} CSV", df.to_csv(index=False), file_name=f"{label.replace(' ', '_')}.csv")

# 🚨 Refill Recommendation
if refill_candidates:
    st.subheader("🚨 Refill Recommendation")
    for label, level, rate in refill_candidates:
        st.markdown(f"🔻 **{label}** is low (**{level:.2f} L**) and rapidly depleting (**{rate:.2f} L/s**) → Recommend refilling.")
else:
    st.success("✅ No refill recommendation needed at the moment.")


