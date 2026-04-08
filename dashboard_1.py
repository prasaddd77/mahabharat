import streamlit as st

import os

import glob

import re

import json

import pandas as pd

import plotly.express as px

import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---

st.set_page_config(page_title="AI-Powered SRE Analysis & Autonomous Remediation Dashboard", page_icon="🛡️", layout="wide")

# Custom CSS

st.markdown("""
<style>

    /* Top Metric Containers */

    div[data-testid="metric-container"] {

        background-color: #1E1E2E;

        border: 1px solid #333344;

        padding: 5% 5% 5% 10%;

        border-radius: 10px;

        box-shadow: 0 4px 6px rgba(0,0,0,0.1);

    }

    /* Sleek Vertical Action Cards */

    .action-card {

        flex: 1; /* Makes them stretch evenly */

        min-width: 200px;

        background-color: #262730;

        border-radius: 8px;

        overflow: hidden;

        box-shadow: 0 6px 12px rgba(0,0,0,0.2);

        display: flex;

        flex-direction: column;

    }

    /* Enlarged Bottleneck Card on the right */

    .bottleneck-card {

        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);

        border: 1px solid #38BDF8;

        border-radius: 10px;

        overflow: hidden;

        box-shadow: 0 8px 16px rgba(0,0,0,0.4);

        display: flex;

        flex-direction: column;

        transform: scale(1.02); /* Makes it slightly larger and pop out */

    }

    /* Top Banner of the Cards */

    .card-banner {

        height: 85px;

        display: flex;

        align-items: center;

        justify-content: center;

        font-size: 34px;

    }

    /* Content Area */

    .card-content {

        padding: 20px;

        color: #FAFAFA;

        flex-grow: 1;

    }

    .card-title {

        font-size: 15px;

        font-weight: 700;

        margin-bottom: 12px;

        text-transform: uppercase;

        letter-spacing: 0.5px;

    }
</style>

""", unsafe_allow_html=True)

REPORTS_DIR = "sre_reports"

# --- DATA EXTRACTION LOGIC ---

@st.cache_data(ttl=5)

def load_all_reports():

    os.makedirs(REPORTS_DIR, exist_ok=True)

    report_files = sorted(glob.glob(f"{REPORTS_DIR}/*.txt"), reverse=True)

    data = []

    for file in report_files:

        with open(file, "r", encoding="utf-8") as f:

            content = f.read()

            basename = os.path.basename(file).replace(".txt", "")

            parts = basename.split("_", 2)

            timestamp = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]} {parts[1][:2]}:{parts[1][2:4]}" if len(parts) >= 2 else "Unknown"

            job_name = parts[2] if len(parts) == 3 else basename

            metrics = {}

            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)

            if json_match:

                try:

                    metrics = json.loads(json_match.group(1))

                except json.JSONDecodeError:

                    pass
            disk_info = {"quota": 0, "used": 0, "free": 0, "percent": 0}
            # Added -? to allow negative numbers to be parsed correctly
            disk_match = re.search(r'Quota = (-?[\d.]+)MB, Used = (-?[\d.]+)MB, Free = (-?[\d.]+)MB\. Currently (-?[\d.]+)% full', content)
            if disk_match:
                disk_info = {
                    "quota": float(disk_match.group(1)),
                    "used": float(disk_match.group(2)),
                    "free": float(disk_match.group(3)),
                    "percent": float(disk_match.group(4))
                }
                

            predicted_footprint = 0

            footprint_match = re.search(r'expected disk footprint .* is (\d+)MB', content)

            if footprint_match:

                predicted_footprint = int(footprint_match.group(1))

            detailed_actions = re.findall(r'\[>\] MCP Server Result:\s*\[Autonomous Action\]\s*(.+)', content)

            data.append({

                "Filename": basename,

                "Job": job_name,

                "Timestamp": timestamp,

                "Health Score": metrics.get("health_score", 0),

                "Hours Reclaimed": metrics.get("reclaimed_hours", 0.0),

                "Compute Saved ($)": metrics.get("saved_compute_costs_usd", 0.0),

                "Actions": metrics.get("autonomous_actions_taken", "None"),

                "Detailed Actions": detailed_actions,

                "Bottleneck": metrics.get("bottleneck_insight", "N/A"),

                "Raw Output": content,

                "Disk Info": disk_info,

                "Predicted Footprint": predicted_footprint

            })

    return pd.DataFrame(data), report_files

df_reports, raw_files = load_all_reports()

# --- DASHBOARD HEADER ---

st.title("🛡️ AI-Powered SRE Analysis & Autonomous Remediation Dashboard")

st.markdown("Autonomous self-healing and predictive resource orchestration for enterprise CI/CD.")

st_autorefresh = st.toggle("Live Monitoring Mode (Auto-Refresh)", value=True)

if st_autorefresh:

    import time

    time.sleep(10)

    st.rerun()

if df_reports.empty:

    st.success("🟢 Cluster is healthy. Watchdog is monitoring...")

    st.stop()

# --- GLOBAL ROI METRICS ---

st.subheader("Value Realization & Platform Health Index")

global_col1, global_col2, global_col3 = st.columns(3)

global_col1.metric("Total Hours Reclaimed", f"{df_reports['Hours Reclaimed'].sum():.1f} hrs", "Developer Time Saved")

global_col2.metric("Interventions", f"{len(df_reports)}", "Incidents Prevented")

global_col3.metric("Avg Cluster Health", f"{df_reports['Health Score'].mean():.0f}/100", "System Stability")

st.divider()

# --- TABS FOR ORGANIZATION ---

tab1, tab2 = st.tabs(["🔴 Live Intervention Feed", "📈 Historical Analytics"])

with tab1:

    col_nav, col_details = st.columns([1, 3])

    with col_nav:

        st.subheader("Incident History")

        selected_file = st.radio("Select Intervention:", df_reports["Filename"].tolist())

    with col_details:

        run_data = df_reports[df_reports["Filename"] == selected_file].iloc[0]

        # --- NEW HEADER LAYOUT WITH DYNAMIC HEALTH SCORE BADGE ---

        h_col1, h_col2 = st.columns([3, 1])

        with h_col1:

            st.subheader(f"Incident: {run_data['Job']}")

            st.caption(f"Detected and resolved at: {run_data['Timestamp']}")

        with h_col2:

            health_score = int(run_data.get('Health Score', 0))

            # Determine badge color dynamically

            if health_score >= 80:

                score_color = "#00CC96" # Green

            elif health_score >= 50:

                score_color = "#F59E0B" # Orange

            else:

                score_color = "#F43F5E" # Red

            # INCREASED SIZES HERE: Padding, Fonts, and Min-Width

            st.markdown(f"""
<div style="text-align: right; padding-top: 5px;">
<div style="display: inline-block; text-align: center; background-color: #262730; border: 1px solid {score_color}; border-radius: 8px; padding: 12px 28px; min-width: 140px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
<div style="font-size: 13px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Pipeline Health</div>
<div style="font-size: 36px; font-weight: bold; color: {score_color}; line-height: 1;">{health_score}<span style="font-size: 16px; color: #64748B; margin-left: 2px;">/100</span></div>
</div>
</div>

            """, unsafe_allow_html=True)

        # 1. UI WIDGET: Disk Space Visualization

        if run_data["Disk Info"]["quota"] > 0:

            st.markdown("### 💾 Predictive Infrastructure Audit")

            disk = run_data["Disk Info"]

            d_col1, d_col2 = st.columns([2, 1])

            with d_col1:

                fig = go.Figure(go.Indicator(

                    mode = "gauge+number",

                    value = disk["percent"],

                    title = {'text': f"Agent Disk Utilization (Quota: {disk['quota']}MB)"},

                    gauge = {

                        'axis': {'range': [None, 100]},

                        'bar': {'color': "#FF4B4B" if disk["percent"] > 80 else "#00CC96"},

                        'steps': [

                            {'range': [0, 60], 'color': "rgba(0, 204, 150, 0.2)"},

                            {'range': [60, 85], 'color': "rgba(255, 161, 90, 0.2)"},

                            {'range': [85, 100], 'color': "rgba(255, 75, 75, 0.2)"}],

                    }

                ))

                fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))

                st.plotly_chart(fig, use_container_width=True)

            with d_col2:

                st.metric("Current Free Space", f"{disk['free']} MB")

                st.metric("AI Predicted Footprint", f"{run_data['Predicted Footprint']} MB")

                if run_data['Predicted Footprint'] > disk['free']:

                    st.error("⚠️ AI Detected Deficit: Pre-emptive cleaning required!")

                else:

                    st.success("✅ Capacity sufficient. Pipeline cleared for dispatch.")

        # 2. UI WIDGET: Actions & Bottlenecks (SIDE-BY-SIDE NO-INDENT HTML)

        st.markdown("### 🤖 SRE Autonomous Execution & Insights")

        detailed_actions = run_data.get("Detailed Actions", [])

        basic_actions = run_data["Actions"]

        banner_colors = ["#00CC96", "#F43F5E", "#F59E0B", "#8B5CF6"]

        # No indentation formatting below to prevent Streamlit from turning them into Markdown code blocks

        html = '<div style="display: flex; gap: 24px; align-items: stretch; flex-wrap: wrap; margin-bottom: 24px;">'

        # --- LEFT SIDE: Remediation Steps ---

        html += '<div style="display: flex; flex: 2.5; gap: 16px; flex-wrap: wrap; min-width: 50%;">'

        if detailed_actions:

            for i, d_action in enumerate(detailed_actions):

                bg = banner_colors[i % len(banner_colors)]

                html += f'<div class="action-card"><div class="card-banner" style="background-color: {bg};">🛠️</div><div class="card-content"><div class="card-title" style="color: {bg};">Remediation Step {i+1}</div><div style="line-height: 1.5; font-size: 14px;">{d_action}</div></div></div>'

        else:

            if isinstance(basic_actions, str):

                basic_actions = [a.strip() for a in basic_actions.replace("[", "").replace("]", "").replace("'", "").split(",")]

            for i, action in enumerate(basic_actions):

                if action and action.lower() not in ["none", "null"]:

                    bg = banner_colors[i % len(banner_colors)]

                    html += f'<div class="action-card"><div class="card-banner" style="background-color: {bg};">🛠️</div><div class="card-content"><div class="card-title" style="color: {bg};">Remediation Step {i+1}</div><div style="line-height: 1.5; font-size: 14px;">Executed: <b>{action}</b></div></div></div>'

                elif action.lower() in ["none", "null"]:

                    html += '<div class="action-card"><div class="card-banner" style="background-color: #64748B;">ℹ️</div><div class="card-content"><div class="card-title" style="color: #94A3B8;">No Action</div><div style="line-height: 1.5; font-size: 14px;">No infrastructure actions required. Passed safely to developers.</div></div></div>'

        html += '</div>' # Close Remediation Section

        # --- RIGHT SIDE: Bottleneck Discovery (Slightly larger flex-basis) ---

        html += f'<div class="bottleneck-card" style="flex: 1.2; min-width: 300px;"><div class="card-banner" style="background-color: #0284C7; font-size: 40px;">💡</div><div class="card-content"><div class="card-title" style="color: #38BDF8;">AI Bottleneck Discovery</div><div style="line-height: 1.6; font-size: 14.5px;">{run_data["Bottleneck"]}</div></div></div>'

        html += '</div>' # Close Main Flex Container

        st.markdown(html, unsafe_allow_html=True)

        # 3. Raw Logs

        with st.expander("View Raw AI Reasoning & MCP Execution Trace"):

            st.code(run_data["Raw Output"], language="log")

# ==========================================

# TAB 2: HISTORICAL ANALYTICS

# ==========================================

with tab2:

    st.subheader("Predictive Analytics & SRE Performance")

    chart_df = df_reports.sort_values("Timestamp")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        st.markdown("**Developer Hours Reclaimed by Pipeline**")

        fig_hours = px.bar(chart_df, x="Job", y="Hours Reclaimed", color="Job",

                           labels={"Hours Reclaimed": "Hours Saved"},

                           template="plotly_dark")

        fig_hours.update_layout(showlegend=False)

        st.plotly_chart(fig_hours, use_container_width=True)

    with chart_col2:

        st.markdown("**Cluster Health Score Timeline**")

        fig_health = px.line(chart_df, x="Timestamp", y="Health Score", markers=True,

                             labels={"Health Score": "Health Score (0-100)"},

                             template="plotly_dark")

        fig_health.update_traces(line_color="#00CC96")

        fig_health.update_yaxes(range=[0, 105])

        st.plotly_chart(fig_health, use_container_width=True)
