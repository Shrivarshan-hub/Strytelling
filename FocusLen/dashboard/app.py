import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(page_title="Analysis", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("FocusLens Analysis")
st.markdown("Current session metrics")

DB_PATH = "../db/focuslens.db"
if not os.path.exists(DB_PATH):
    DB_PATH = "db/focuslens.db"

def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM focus_log", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = load_data()

if df.empty:
    st.info("No active session data. Start tracking to see live metrics.")
else:
    total_seconds = len(df)
    
    true_focus_time = len(df[df['overall_status'] == 'TRUE FOCUS'])
    distraction_time = len(df[df['overall_status'].isin(['DISTRACTION', 'FAKE STUDY'])])
    absent_time = len(df[df['overall_status'] == 'ABSENT'])
    
    focus_score = (true_focus_time / total_seconds) * 100 if total_seconds > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Focus Score", f"{focus_score:.1f}%")
    with col2:
        st.metric("Focus Time", f"{true_focus_time // 60}m {true_focus_time % 60}s")
    with col3:
        st.metric("Distraction Time", f"{distraction_time // 60}m {distraction_time % 60}s")
    with col4:
        st.metric("Absence Time", f"{absent_time // 60}m {absent_time % 60}s")

    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Time Breakdown")
        status_counts = df['overall_status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Seconds']
        
        color_map = {
            'TRUE FOCUS': '#10b981',
            'DISTRACTION': '#ef4444',
            'FAKE STUDY': '#f59e0b',
            'ABSENT': '#9ca3af',
            'DROWSY': '#8b5cf6',
            'NEUTRAL FOCUS': '#3b82f6'
        }
        fig1 = px.pie(status_counts, values='Seconds', names='Status', hole=0.4, color='Status', color_discrete_map=color_map)
        st.plotly_chart(fig1, width='stretch')

    with col2:
        st.subheader("Applications")
        app_counts = df['app_name'].value_counts().head(8).reset_index()
        app_counts.columns = ['App', 'Active Seconds']
        fig2 = px.bar(app_counts, x='App', y='Active Seconds', color='App')
        st.plotly_chart(fig2, width='stretch')

    st.divider()
    
    colA, colB = st.columns([8, 2])
    with colA:
        st.subheader("History Log")
        st.dataframe(df.tail(15).sort_values("timestamp", ascending=False), width='stretch')
    with colB:
        if st.button("Refresh"):
            st.rerun()
