"""Simple test to verify Streamlit and API connectivity."""

import streamlit as st
import requests
import os

st.title("🧪 Dashboard Test Page")

# Test API connectivity
api_url = os.getenv("API_URL", "http://api:8000")
st.write(f"**API URL:** {api_url}")

st.write("---")
st.subheader("API Tests")

# Test 1: Health check
try:
    response = requests.get(f"{api_url}/health", timeout=5)
    st.success(f"✅ Health check: {response.status_code}")
    st.json(response.json())
except Exception as e:
    st.error(f"❌ Health check failed: {e}")

# Test 2: Dashboard summary
try:
    response = requests.get(f"{api_url}/api/v1/dashboard/summary", timeout=5)
    st.success(f"✅ Dashboard summary: {response.status_code}")
    data = response.json()
    st.json(data)
    
    # Show metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Incidents", data.get("total_incidents", 0))
    with col2:
        st.metric("P2 High", data.get("p2_incidents", 0))
    with col3:
        st.metric("P4 Low", data.get("p4_incidents", 0))
        
except Exception as e:
    st.error(f"❌ Dashboard summary failed: {e}")

# Test 3: Recent incidents
try:
    response = requests.get(f"{api_url}/api/v1/dashboard/incidents?limit=10", timeout=5)
    st.success(f"✅ Recent incidents: {response.status_code}")
    incidents = response.json()
    st.write(f"Found {len(incidents)} incidents")
    
    if incidents:
        import pandas as pd
        df = pd.DataFrame(incidents)
        st.dataframe(df)
    
except Exception as e:
    st.error(f"❌ Recent incidents failed: {e}")
