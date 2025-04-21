import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
from io import StringIO
from datetime import timedelta

# --- Tank Configurations ---
TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

# --- Fetch and preprocess ---
@st.cache_data
def fetch_and_process(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    df = pd.read_csv(StringIO(requests.get(url).text))
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df["liters"] = df["liters"].clip(0, capacity)
    df["smoothed"] = df["liters"].rolling(window=100, min_periods=1).mean()
    df["diff"] = df["smoothed"].diff()
    df["hour"] = df["created_at"].dt.floor("h")
    return df

# --- Streamlit Setup ---
st.set_page_config(layout="wide")
st.title("🚰 Combined Water Monitoring Dashboard - NITK Hostels")

# --- Water Level Plot (All Tanks) ---
fig1, ax1 = plt.subplots(figsize=(14, 5))
for name, config in TANKS.items():
    df = fetch_and_process(config["channel_id"], config["api_key"], config["capacity"])
    ax1.plot(df["created_at"], df["smoothed"], label=name)
ax1.set_title("📊 Smoothed Water Levels (All Tanks)")
ax1.set_xlabel("Time")
ax1.set_ylabel("Water Level (Liters)")
ax1.xaxis.set_major_locator(mdates.HourLocator(byhour=[3, 6, 12, 15, 18, 21]))
ax1.xaxis.set_minor_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax1.xaxis.set_minor_formatter(mdates.DateFormatter('\n%d %b'))
ax1.grid(True)
ax1.legend()
fig1.autofmt_xdate()
st.pyplot(fig1)

# --- Hourly Usage Plots (One by One) ---
st.subheader("⏱️ Hourly Usage per Tank")

for name, config in TANKS.items():
    df = fetch_and_process(config["channel_id"], config["api_key"], config["capacity"])
    hourly = df.groupby("hour")["diff"].sum().reset_index()
    hourly["usage_liters"] = -hourly["diff"].clip(upper=0)

    st.markdown(f"### 🔻 {name}")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(hourly["hour"], hourly["usage_liters"], color='crimson')
    ax.set_title(f"{name} - Hourly Water Usage")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Liters Used")
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[3, 6, 12, 15, 18, 21]))
    ax.xaxis.set_minor_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('\n%d %b'))
    ax.grid(True)
    fig.autofmt_xdate()
    st.pyplot(fig)
