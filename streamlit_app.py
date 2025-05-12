"""
Streamlit dashboard for real-time visualization of sensor readings from Firebase,
with elapsed-time counter in HH:MM:SS format.
"""
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone

# ─── Configuration ─────────────────────────────────────────────────────────
DB_URL              = "https://embedded-systems-project-dbf9b-default-rtdb.europe-west1.firebasedatabase.app"
READ_URL            = f"{DB_URL}/readings.json"
TEMP_THRESHOLD      = 30
HUM_THRESHOLD       = 75
LDR_THRESHOLD       = 10
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
        # Ensure numeric time (ms), convert to timedelta and formatted string
        df["time"] = pd.to_numeric(df["time"], downcast="integer")
        df["elapsed"] = pd.to_timedelta(df["time"], unit="ms")
        df["time_str"] = df["elapsed"].apply(lambda td: str(td).split(".")[0])
        df.sort_values("time", inplace=True)
        df = df.tail(MAX_DISPLAY_RECORDS)
    return df

# ─── Load Data ─────────────────────────────────────────────────────────────
df = fetch_data()
if df.empty:
    st.warning("No data available. Check if your sensor is connected?")
else:
    # Caption and last reading time
    st.caption(
        f"Showing {len(df)} most recent readings (of {MAX_DISPLAY_RECORDS} max)" +
        f" • Last reading @ {df['time_str'].iloc[-1]}"
    )

    def build_chart(field, label, threshold, color):
        fig = go.Figure()
        # Main line trace using HH:MM:SS strings
        fig.add_trace(go.Scatter(
            x=df["time_str"],
            y=df[field],
            mode='lines',
            line=dict(color=color),
            name=label,
            hovertemplate='Time: %{x}<br>' + f'{label}: %{{y}}<extra></extra>'
        ))
        # Threshold line
        fig.add_hline(
            y=threshold,
            line=dict(color=color, dash='dash'),
            annotation_text=f'Threshold: {threshold}',
            annotation_position="top right",
            annotation_font=dict(color=color, size=12)
        )
        # Layout updates
        fig.update_layout(
            title=label,
            xaxis_title='Elapsed Time (HH:MM:SS)',
            yaxis_title=label,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode='x unified'
        )
        return fig

    # Render charts in columns
    temp_chart = build_chart('temp', 'Temperature (°C)', TEMP_THRESHOLD, 'red')
    hum_chart  = build_chart('hum',  'Humidity (%)', HUM_THRESHOLD, 'blue')
    ldr_chart  = build_chart('ldr',  'Light (%)', LDR_THRESHOLD, 'green')
    cols = st.columns(3)
    cols[0].plotly_chart(temp_chart, use_container_width=True)
    cols[1].plotly_chart(hum_chart,  use_container_width=True)
    cols[2].plotly_chart(ldr_chart,  use_container_width=True)

    # Alerts Section
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
