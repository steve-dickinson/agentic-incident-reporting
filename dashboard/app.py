"""Streamlit dashboard for monitoring incident processing."""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Page config
st.set_page_config(
    page_title="Defra AI Agent Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00703C;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #00703C;
    }
    .priority-p1 {
        background-color: #ff4b4b;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .priority-p2 {
        background-color: #ffa500;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .priority-p3 {
        background-color: #ffb347;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .priority-p4 {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API Base URL - use 'api' service name when running in Docker
default_api_url = os.getenv("API_URL", "http://api:8000")
API_BASE_URL = st.sidebar.text_input("API Base URL", default_api_url)

# Refresh interval
refresh_interval = st.sidebar.slider("Auto-refresh (seconds)", 5, 60, 10)

# Auto-refresh using st.experimental_rerun with proper timing
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False)

# Header
st.markdown('<div class="main-header">🌍 Defra AI Agent Dashboard</div>', unsafe_allow_html=True)
st.markdown("Real-time monitoring of environmental incident processing")

# Fetch data from API
@st.cache_data(ttl=5)
def fetch_dashboard_data(api_url):
    """Fetch dashboard data from API."""
    try:
        response = requests.get(f"{api_url}/api/v1/dashboard/summary", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch dashboard data: {e}")
        return None

@st.cache_data(ttl=5)
def fetch_recent_incidents(api_url, limit=50):
    """Fetch recent incidents from API."""
    try:
        response = requests.get(f"{api_url}/api/v1/dashboard/incidents?limit={limit}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch incidents: {e}")
        return []

@st.cache_data(ttl=5)
def fetch_hourly_metrics(api_url, hours=24):
    """Fetch hourly metrics from API."""
    try:
        response = requests.get(f"{api_url}/api/v1/dashboard/metrics?hours={hours}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch metrics: {e}")
        return []

# Fetch all data
summary = fetch_dashboard_data(API_BASE_URL)
recent_incidents = fetch_recent_incidents(API_BASE_URL, 100)
hourly_metrics = fetch_hourly_metrics(API_BASE_URL, 24)

# Summary metrics
if summary:
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📊 Total Incidents (7d)",
            value=summary.get("total_incidents", 0),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🔴 Critical (P1)",
            value=summary.get("p1_incidents", 0),
            delta=None
        )
    
    with col3:
        st.metric(
            label="🟠 High (P2)",
            value=summary.get("p2_incidents", 0),
            delta=None
        )
    
    with col4:
        st.metric(
            label="✅ Completed",
            value=summary.get("completed", 0),
            delta=None
        )
    
    with col5:
        avg_ms = summary.get("avg_processing_ms", 0)
        avg_time = float(avg_ms) / 1000 if avg_ms else 0
        st.metric(
            label="⏱️ Avg Time",
            value=f"{avg_time:.1f}s",
            delta=None
        )

st.divider()

# Charts row
if hourly_metrics:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Incidents Over Time (24h)")
        
        df_metrics = pd.DataFrame(hourly_metrics)
        if not df_metrics.empty and 'hour' in df_metrics.columns:
            df_metrics['hour'] = pd.to_datetime(df_metrics['hour'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_metrics['hour'],
                y=df_metrics['total'],
                mode='lines+markers',
                name='Total',
                line=dict(color='#00703C', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=df_metrics['hour'],
                y=df_metrics.get('p1', 0),
                mode='lines+markers',
                name='P1 Critical',
                line=dict(color='#ff4b4b', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=df_metrics['hour'],
                y=df_metrics.get('p2', 0),
                mode='lines+markers',
                name='P2 High',
                line=dict(color='#ffa500', width=2)
            ))
            
            fig.update_layout(
                xaxis_title="Hour",
                yaxis_title="Count",
                hovermode='x unified',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Processing Time Trend")
        
        if not df_metrics.empty and 'avg_time_ms' in df_metrics.columns:
            df_metrics['avg_time_s'] = df_metrics['avg_time_ms'] / 1000
            
            fig = px.bar(
                df_metrics,
                x='hour',
                y='avg_time_s',
                labels={'avg_time_s': 'Avg Time (s)', 'hour': 'Hour'},
                color='avg_time_s',
                color_continuous_scale='Greens'
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# Priority distribution
if summary:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Priority Distribution")
        
        priority_data = {
            'Priority': ['P1 Critical', 'P2 High', 'P3 Medium', 'P4 Low'],
            'Count': [
                summary.get('p1_incidents', 0),
                summary.get('p2_incidents', 0),
                summary.get('p3_incidents', 0),
                summary.get('p4_incidents', 0)
            ],
            'Color': ['#ff4b4b', '#ffa500', '#ffb347', '#4CAF50']
        }
        df_priority = pd.DataFrame(priority_data)
        
        fig = px.pie(
            df_priority,
            values='Count',
            names='Priority',
            color='Priority',
            color_discrete_map={
                'P1 Critical': '#ff4b4b',
                'P2 High': '#ffa500',
                'P3 Medium': '#ffb347',
                'P4 Low': '#4CAF50'
            },
            hole=0.4
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Status Overview")
        
        status_data = {
            'Status': ['Completed', 'Failed', 'Processing'],
            'Count': [
                summary.get('completed', 0),
                summary.get('failed', 0),
                summary.get('total_incidents', 0) - summary.get('completed', 0) - summary.get('failed', 0)
            ]
        }
        df_status = pd.DataFrame(status_data)
        
        fig = px.bar(
            df_status,
            x='Status',
            y='Count',
            color='Status',
            color_discrete_map={
                'Completed': '#4CAF50',
                'Failed': '#ff4b4b',
                'Processing': '#ffa500'
            }
        )
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# Recent incidents table
st.subheader("📋 Recent Incidents")

if recent_incidents:
    df_incidents = pd.DataFrame(recent_incidents)
    
    # Format the dataframe
    if not df_incidents.empty:
        # Convert timestamps
        if 'created_at' in df_incidents.columns:
            df_incidents['created_at'] = pd.to_datetime(df_incidents['created_at'])
            df_incidents['time_ago'] = df_incidents['created_at'].apply(
                lambda x: f"{int((datetime.now() - x.replace(tzinfo=None)).total_seconds() / 60)}m ago"
            )
        
        # Format processing time
        if 'processing_time_ms' in df_incidents.columns:
            df_incidents['processing_time'] = df_incidents['processing_time_ms'].apply(
                lambda x: f"{float(x)/1000:.2f}s" if pd.notna(x) and x else "N/A"
            )
        
        # Select and rename columns for display
        display_cols = {
            'incident_id': 'Incident ID',
            'incident_type': 'Type',
            'location': 'Location',
            'severity': 'Severity',
            'priority': 'Priority',
            'status': 'Status',
            'processing_time': 'Time',
            'time_ago': 'Created',
            'completed_steps': 'Steps ✓',
            'failed_steps': 'Steps ✗'
        }
        
        available_cols = [col for col in display_cols.keys() if col in df_incidents.columns]
        df_display = df_incidents[available_cols].rename(columns=display_cols)
        
        # Add filtering
        col1, col2, col3 = st.columns(3)
        
        with col1:
            priority_filter = st.multiselect(
                "Filter by Priority",
                options=['P1', 'P2', 'P3', 'P4'],
                default=[]
            )
        
        with col2:
            type_filter = st.multiselect(
                "Filter by Type",
                options=df_incidents['incident_type'].unique().tolist() if 'incident_type' in df_incidents.columns else [],
                default=[]
            )
        
        with col3:
            status_filter = st.multiselect(
                "Filter by Status",
                options=df_incidents['status'].unique().tolist() if 'status' in df_incidents.columns else [],
                default=[]
            )
        
        # Apply filters
        if priority_filter and 'priority' in df_incidents.columns:
            df_incidents = df_incidents[df_incidents['priority'].isin(priority_filter)]
            df_display = df_display[df_display['Priority'].isin(priority_filter)]
        
        if type_filter and 'incident_type' in df_incidents.columns:
            df_incidents = df_incidents[df_incidents['incident_type'].isin(type_filter)]
            df_display = df_display[df_display['Type'].isin(type_filter)]
        
        if status_filter and 'status' in df_incidents.columns:
            df_incidents = df_incidents[df_incidents['status'].isin(status_filter)]
            df_display = df_display[df_display['Status'].isin(status_filter)]
        
        # Display table
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Incident detail expander
        st.subheader("🔍 Incident Details")
        incident_ids = df_incidents['incident_id'].tolist() if 'incident_id' in df_incidents.columns else []
        
        if incident_ids:
            selected_incident = st.selectbox("Select incident to view details", incident_ids)
            
            if selected_incident:
                try:
                    response = requests.get(f"{API_BASE_URL}/api/v1/dashboard/incidents/{selected_incident}/logs", timeout=5)
                    if response.status_code == 200:
                        logs = response.json()
                        
                        if logs:
                            st.write("**Execution Steps:**")
                            for log in logs:
                                status_emoji = "✅" if log['status'] == 'completed' else "❌" if log['status'] == 'failed' else "🔄"
                                duration = f"{log.get('duration_ms', 0)}ms" if log.get('duration_ms') else "N/A"
                                
                                with st.expander(f"{status_emoji} Step {log['step_order']}: {log['step_name']} ({duration})"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write("**Status:**", log['status'])
                                        st.write("**Duration:**", duration)
                                        if log.get('error_message'):
                                            st.error(f"**Error:** {log['error_message']}")
                                    
                                    with col2:
                                        if log.get('input_data'):
                                            st.write("**Input:**")
                                            st.json(log['input_data'])
                                        
                                        if log.get('output_data'):
                                            st.write("**Output:**")
                                            st.json(log['output_data'])
                        else:
                            st.info("No execution logs found for this incident")
                    else:
                        st.warning(f"Could not fetch logs: {response.status_code}")
                except Exception as e:
                    st.error(f"Error fetching incident logs: {e}")
else:
    st.info("No recent incidents found")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {refresh_interval}s")
