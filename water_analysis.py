import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import timedelta

# --- Tank Configuration ---
TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

# --- Data Fetching Function ---
def fetch_tank_data(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    df = pd.read_csv(url)
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df = df[["created_at", "liters"]].sort_values("created_at")
    df["rolling_liters"] = df["liters"].rolling(window=50, min_periods=1).mean()
    return df

# --- Streamlit Layout ---
st.set_page_config(layout="wide", page_title="NITK Water Dashboard")
st.title("💧 NITK Hostel Water Monitoring Dashboard")

# --- Sidebar: Tank Selector ---
selected_tank = st.sidebar.selectbox("Select Tank", list(TANKS.keys()))
tank_info = TANKS[selected_tank]
df = fetch_tank_data(tank_info["channel_id"], tank_info["api_key"], tank_info["capacity"])

# --- Display Current Level ---
latest_level = df["liters"].iloc[-1]
percentage = (latest_level / tank_info["capacity"]) * 100
st.metric(label=f"Current Water Level in {selected_tank}", value=f"{latest_level:.2f} L", delta=f"{percentage:.1f}%")

# --- Plot Water Levels (Raw + Smoothed) ---
st.subheader("📊 Water Level Over Time")
fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.plot(df["created_at"], df["liters"], label="Raw", alpha=0.4)
ax1.plot(df["created_at"], df["rolling_liters"], label="Smoothed", color="red")
ax1.set_xlabel("Time")
ax1.set_ylabel("Liters")
ax1.set_title("Water Level (Raw vs Smoothed)")
ax1.legend()
ax1.grid()
st.pyplot(fig1)

# --- Calculate Hourly Usage ---
df["diff"] = df["rolling_liters"].diff()
df["hour"] = df["created_at"].dt.floor("H")
hourly_usage = df.groupby("hour")["diff"].sum().reset_index()
hourly_usage["usage_liters"] = -hourly_usage["diff"].clip(upper=0)

# --- Peak Usage Hour ---
peak_row = hourly_usage.loc[hourly_usage["usage_liters"].idxmax()]
peak_hour = peak_row["hour"]
peak_val = peak_row["usage_liters"]

# --- Average Daily Usage ---
df["date"] = df["created_at"].dt.date
daily_usage = df.groupby("date")["diff"].sum()
average_daily_usage = -daily_usage.clip(upper=0).mean()

# --- Display Peak + Daily Metrics ---
st.subheader("📌 Usage Summary")
st.markdown(f"""
- **Peak Usage Hour:** 🕒 {peak_hour} — 🔻 {peak_val:.2f} Liters
- **Average Daily Usage:** 📆 {average_daily_usage:.2f} Liters/day
""")

# --- Hourly Usage Plot ---
st.subheader("⏱️ Hourly Usage Trend")
fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.plot(hourly_usage["hour"], hourly_usage["usage_liters"], marker='o', color='crimson')
ax2.set_xlabel("Hour")
ax2.set_ylabel("Liters Used")
ax2.set_title("Hourly Water Usage (Smoothed)")
ax2.grid()
st.pyplot(fig2)

# --- Raw Data Toggle ---
if st.checkbox("📄 Show Raw Data Table"):
    st.write(df.tail(30))
