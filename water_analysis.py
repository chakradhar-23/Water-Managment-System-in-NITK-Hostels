import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO
from datetime import timedelta

# --- Tank Configurations ---
TANKS = {
    "MT3 - Tank 1": {"channel_id": "2873578", "api_key": "B1K9WJO8D63PL7U6", "capacity": 10000},
    "MT2 - Tank 2": {"channel_id": "2741662", "api_key": "PL7GA8VEEUFJGA3Y", "capacity": 15000},
    "MT1 - Tank 3": {"channel_id": "2668039", "api_key": "IVBGOGRTY7B3ZLUQ", "capacity": 10000},
}

# --- Fetch & preprocess ---
@st.cache_data
def fetch_and_process(channel_id, api_key, capacity):
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.csv?api_key={api_key}&results=10000"
    df = pd.read_csv(StringIO(requests.get(url).text))
    df["created_at"] = pd.to_datetime(df["created_at"]) + timedelta(hours=5, minutes=30)
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce").fillna(0)
    df["liters"] = (df["field1"] / 100) * capacity
    df["liters"] = df["liters"].clip(0, capacity)
    df["smoothed"] = df["liters"].rolling(window=50, min_periods=1).mean()
    df["diff"] = df["smoothed"].diff()
    df["hour"] = df["created_at"].dt.floor("H")
    return df

# --- Streamlit Setup ---
st.set_page_config(layout="wide")
st.title("🚰 Interactive Water Monitoring Dashboard - NITK Hostels")

# --- Combined Water Level Plot ---
st.subheader("📊 Smoothed Water Levels - All Tanks (Interactive)")

fig = go.Figure()
for name, config in TANKS.items():
    df = fetch_and_process(config["channel_id"], config["api_key"], config["capacity"])
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["smoothed"], mode='lines', name=name))

fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Water Level (Liters)",
    title="Combined Tank Water Levels (Smoothed)",
    hovermode="x unified",
    height=500
)
st.plotly_chart(fig, use_container_width=True)

# --- Hourly Usage Plot for Each Tank ---
st.subheader("⏱️ Hourly Usage per Tank (Interactive Bar Graphs)")

for name, config in TANKS.items():
    df = fetch_and_process(config["channel_id"], config["api_key"], config["capacity"])
    hourly = df.groupby("hour")["diff"].sum().reset_index()
    hourly["usage_liters"] = -hourly["diff"].clip(upper=0)

    st.markdown(f"### 🔻 {name}")
    fig_bar = px.bar(
        hourly, x="hour", y="usage_liters",
        labels={"hour": "Hour", "usage_liters": "Liters Used"},
        title=f"{name} - Hourly Usage (L)",
    )
    fig_bar.update_layout(
        xaxis=dict(
            tickformat="%H:%M\n%d %b",
            title="Hour of Day"
        ),
        yaxis_title="Liters Used",
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig_bar, use_container_width=True)

