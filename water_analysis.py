import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import timedelta
import io

# ---- Configuration ----
TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

st.set_page_config(page_title="Water Monitoring Dashboard", layout="wide")
st.title("💧 NITK Hostel Water Monitoring Dashboard")

# ---- Data Loader ----
@st.cache_data(show_spinner=True)
def fetch_tank_data(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    response = requests.get(url)
    df = pd.read_csv(io.StringIO(response.text))
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df["rolling_liters"] = df["liters"].rolling(window=50, min_periods=1).mean()
    return df.sort_values("created_at")

# ---- Load & Process All Tanks ----
tank_data = {}
for name, info in TANKS.items():
    tank_data[name] = fetch_tank_data(info["channel_id"], info["api_key"], info["capacity"])

# ---- Combined Smoothed Water Level Plot ----
st.subheader("📊 Smoothed Water Level Comparison")
fig, ax = plt.subplots(figsize=(12, 5))
for name, df in tank_data.items():
    ax.plot(df["created_at"], df["rolling_liters"], label=name)
ax.set_title("Water Level Trend (Smoothed)")
ax.set_xlabel("Time")
ax.set_ylabel("Liters")
ax.legend()
ax.grid()
st.pyplot(fig)

# ---- Per Tank Analytics ----
st.header("📈 Tank-wise Analysis")
for tank_name, df in tank_data.items():
    st.subheader(tank_name)

    # Calculate differences
    df["diff"] = df["rolling_liters"].diff()
    df["hour"] = df["created_at"].dt.floor("h")
    df["date"] = df["created_at"].dt.date
    df["usage"] = df["diff"].apply(lambda x: -x if x < 0 else 0)

    # Daily Usage
    daily_usage = df.groupby("date")["usage"].sum()
    avg_daily = daily_usage.mean()

    # Hourly Usage
    hourly_usage = df.groupby("hour")["usage"].sum()
    peak_hour = hourly_usage.idxmax()
    peak_val = hourly_usage.max()

    # 👉 Summary
    st.markdown(f"**🔺 Average Daily Usage:** {avg_daily:.2f} Liters/day")
    st.markdown(f"**⏰ Peak Usage Hour:** {peak_hour} — {peak_val:.2f} Liters")

    # 👉 Plot Daily Usage
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_usage.index, daily_usage.values, marker="o", color="green")
    ax1.set_title("Daily Usage")
    ax1.set_ylabel("Liters")
    ax1.set_xlabel("Date")
    ax1.grid(True)
    st.pyplot(fig1)

    # 👉 Plot Hourly Usage (Bar)
    fig2, ax2 = plt.subplots()
    ax2.bar(hourly_usage.index.astype(str), hourly_usage.values, color="tomato")
    ax2.set_title("Hourly Usage")
    ax2.set_ylabel("Liters")
    ax2.set_xlabel("Hour")
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(True)
    st.pyplot(fig2)

# Optional: Add anomaly detection or refill suggestion if needed

