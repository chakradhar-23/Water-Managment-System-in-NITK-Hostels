import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import timedelta
from io import StringIO
import requests

TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

st.set_page_config(page_title="NITK Water Dashboard", layout="wide")
st.title("💧 Smart Water Management Dashboard for NITK Hostels")

def fetch_data(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    df = pd.read_csv(url)
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df = df[["created_at", "liters"]]
    df["smoothed"] = df["liters"].rolling(window=50, min_periods=1).mean()
    return df

def interactive_time_series(df_dict, column="smoothed"):
    df_all = pd.DataFrame()
    for tank, df in df_dict.items():
        temp = df[["created_at", column]].copy()
        temp["Tank"] = tank
        df_all = pd.concat([df_all, temp])
    fig = px.line(df_all, x="created_at", y=column, color="Tank", title="Water Level Trends (Smoothed)",
                  labels={"created_at": "Time", column: "Liters"}, height=500)
    st.plotly_chart(fig, use_container_width=True)

tank_data = {}
for name, info in TANKS.items():
    st.subheader(f"📦 {name}")
    df = fetch_data(info["channel_id"], info["api_key"], info["capacity"])
    tank_data[name] = df

    latest_level = df["liters"].iloc[-1]
    percentage = (latest_level / info["capacity"]) * 100
    st.metric(label="Current Water Level", value=f"{latest_level:.2f} L", delta=f"{percentage:.1f}%")

    df["hour"] = df["created_at"].dt.floor("H")
    df["diff"] = df["smoothed"].diff()
    hourly = df.groupby("hour")["diff"].sum().reset_index()
    hourly["usage"] = -hourly["diff"].clip(upper=0)

    st.markdown("**Hourly Usage Trend**")
    fig2 = px.bar(hourly, x="hour", y="usage", labels={"hour": "Hour", "usage": "Usage (L)"},
                  title="Hourly Water Usage", height=400)
    fig2.update_layout(xaxis=dict(tickformat="%d %b %H:%M"))
    st.plotly_chart(fig2, use_container_width=True)

    df["date"] = df["created_at"].dt.date
    daily_usage = df.groupby("date")["diff"].sum()
    avg_daily = -daily_usage.clip(upper=0).mean()
    st.info(f"📅 Average Daily Usage: **{avg_daily:.2f} L/day**")

    if not hourly.empty:
        peak_row = hourly.loc[hourly["usage"].idxmax()]
        st.success(f"⏰ Peak Usage Hour: {peak_row['hour']} — {peak_row['usage']:.2f} L")

    last_45 = df.tail(45)
    if len(last_45) > 1:
        time_diff = (last_45["created_at"].iloc[-1] - last_45["created_at"].iloc[0]).total_seconds()
        level_diff = last_45["smoothed"].iloc[-1] - last_45["smoothed"].iloc[0]
        rate = -level_diff / time_diff if time_diff > 0 else 0
        high_usage = rate > 0.05
        low_level = latest_level < 0.3 * info["capacity"]
        refill = high_usage and low_level
        if refill:
            st.error(f"🚨 Refill Recommended (Recent Rate: {rate:.3f} L/s)")
        else:
            st.success("✅ No Immediate Refill Required")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name=f"{name.replace(' ', '_')}_data.csv")

st.header("📊 Multi-Tank Water Level Comparison")
interactive_time_series(tank_data)


