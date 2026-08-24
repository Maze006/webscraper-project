"""
# To run this app, execute the following command in your terminal:
# streamlit run streamlit_app.py
"""

import streamlit as st
from pages_ui.current_openings import render_current_page
from pages_ui.future_pipeline import render_future_page
from query_engine import get_available_sources
from theme import apply_glass_theme

# Configure default page layout
st.set_page_config(page_title="Discovery Platform", layout="wide", initial_sidebar_state="expanded")

# Inject Hardware-Accelerated Glassmorphism Theme
apply_glass_theme("assets/background.mp4")

# --- Initialize Session State for Filters ---
if 'selected_type' not in st.session_state:
    st.session_state.selected_type = 'All'
if 'selected_domain' not in st.session_state:
    st.session_state.selected_domain = 'All'
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = 'All'
if 'selected_source' not in st.session_state:
    st.session_state.selected_source = 'All'

def reset_filters():
    """Callback to reset all filters to their default 'All' state."""
    st.session_state.selected_type = 'All'
    st.session_state.selected_domain = 'All'
    st.session_state.selected_location = 'All'
    st.session_state.selected_source = 'All'

# --- Sidebar ---
st.sidebar.header("🔍 Filter Opportunities")

# Use selectboxes linked to session state keys
st.sidebar.selectbox("Opportunity Type", ["All", "Internship", "Fellowship"], key='selected_type')
st.sidebar.selectbox("Domain", ["All", "Tech", "Finance", "Quant", "Research Lab"], key='selected_domain')

# Every listing is either based in India or fully remote from outside India.
LOCATION_CHOICES = {
    "All": None,
    "In India": "India",
    "Remote (outside India)": "Remote",
}
st.sidebar.selectbox("Location", list(LOCATION_CHOICES.keys()), key='selected_location')
st.sidebar.selectbox("Source", ["All"] + get_available_sources(), key='selected_source')
st.sidebar.caption("Showing internships in India, plus remote-only roles based outside India.")

# Reset button uses the callback
st.sidebar.button("Reset Filters", on_click=reset_filters)

# Map UI 'All' choices to None for the backend query_engine
active_type = None if st.session_state.selected_type == "All" else st.session_state.selected_type
active_domain = None if st.session_state.selected_domain == "All" else st.session_state.selected_domain
active_location = LOCATION_CHOICES.get(st.session_state.selected_location)
active_source = None if st.session_state.selected_source == "All" else st.session_state.selected_source

# --- Page Wrappers ---
# We wrap the underlying render functions to automatically pass the active sidebar filters down
def current_openings_page():
    render_current_page(domain_filter=active_domain, type_filter=active_type,
                        location_filter=active_location, source_filter=active_source)

def future_pipeline_page():
    render_future_page(domain_filter=active_domain, type_filter=active_type,
                       location_filter=active_location, source_filter=active_source)

# --- Navigation & Routing using Streamlit's new Page API ---
page_1 = st.Page(
    current_openings_page,
    title="Currently Open",
    icon="🟢",
    default=True
)

page_2 = st.Page(
    future_pipeline_page,
    title="Future Pipeline",
    icon="⏳"
)

# Initialize navigation and run
pg = st.navigation([page_1, page_2])
pg.run()
