"""
Streamlit dashboard for real-time visualization of sensor readings from Firebase,
using streamlit-autorefresh for synchronized updates and clear threshold labels.
Now with Plotly charts and limited to showing only the 10 most recent readings.
"""
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone

# ─── Configuration ─────────────────────────────────────────────────────────
DB_URL         = "https://embedded-systems-project-dbf9b-default-rtdb.europe-west1.firebasedatabase.app"
READ_URL       = f"{DB_URL}/readings.json"
TEMP_THRESHOLD = 30
HUM_THRESHOLD  = 75
LDR_THRESHOLD  = 10
MAX_DISPLAY_RECORDS = 15  # Only show this many most recent readings

# ─── Page Setup ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Env Monitor", layout="wide")
st.title("📊 Real-Time Environmental Monitor")

# ─── Auto-refresh every 3 seconds ──────────────────────────────────────────
_ = st_autorefresh(interval=3000, key="data_refresh")

# ─── Fetch Data ────────────────────────────────────────────────────────────
def fetch_data():
    resp = requests.get(READ_URL)
    resp.raise_for_status()
    data = resp.json() or {}
    df = pd.DataFrame.from_dict(data, orient="index")
    if not df.empty:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.sort_values("datetime", inplace=True)
        # Keep only the most recent records
        df = df.tail(MAX_DISPLAY_RECORDS)
    return df

# ─── Load Data ─────────────────────────────────────────────────────────────
df = fetch_data()
if df.empty:
    st.warning("No data available. Check if your sensor is connected?")
else:
    latest_time = df["datetime"].max()
    st.caption(f"Showing {len(df)} most recent readings (of {MAX_DISPLAY_RECORDS} max)")

    def build_chart(field, label, threshold, color):
        fig = go.Figure()
        
        # Add main line trace
        fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df[field],
            mode='lines',
            line=dict(color=color),
            name=label,
            hovertemplate='Time: %{x}<br>' + f'{label}: %{{y}}<extra></extra>'
        ))
        
        # Add threshold line
        fig.add_hline(
            y=threshold,
            line=dict(color=color, dash='dash'),
            annotation_text=f'Threshold: {threshold}',
            annotation_position="top right",
            annotation_font=dict(color=color, size=12)
        )
        
        # Update layout
        fig.update_layout(
            title=label,
            xaxis_title='Time',
            yaxis_title=label,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode='x unified'
        )
        
        return fig

    # Build and render charts
    temp_chart = build_chart('temp', 'Temperature (°C)', TEMP_THRESHOLD, 'red')
    hum_chart  = build_chart('hum',  'Humidity (%)', HUM_THRESHOLD, 'blue')
    ldr_chart  = build_chart('ldr',  'Light (%)', LDR_THRESHOLD, 'green')

    cols = st.columns(3)
    cols[0].plotly_chart(temp_chart, use_container_width=True)
    cols[1].plotly_chart(hum_chart,  use_container_width=True)
    cols[2].plotly_chart(ldr_chart,  use_container_width=True)

    # Alerts Section (only checks latest reading)
    st.markdown("---")
    st.subheader("⚠️ Alerts")
    latest = df.iloc[-1]
    alerts = []
    if latest.temp > TEMP_THRESHOLD:
        alerts.append(f"🌡️ Temperature high: {latest.temp}°C")
    if latest.hum > HUM_THRESHOLD:
        alerts.append(f"💧 Humidity high: {latest.hum}%")
    if latest.ldr < LDR_THRESHOLD:
        alerts.append(f"🔦 Light low: {latest.ldr}%")
    if alerts:
        for msg in alerts:
            st.error(msg)
    else:
        st.success("All readings are within normal thresholds.")

    # Footer timestamp
    st.markdown(f"*Last updated: {datetime.now(timezone.utc).isoformat()} UTC*")