import streamlit as st
import sys
import os

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query_engine import get_opportunities
from ui_components import render_paginated_cards

def render_current_page(domain_filter=None, type_filter=None, location_filter=None,
                        source_filter=None):
    st.header("🟢 Currently Open Opportunities")
    st.caption("India-based internships, plus fully remote roles from outside India.")
    
    opportunities = get_opportunities('CURRENT', domain_filter, type_filter, location_filter,
                                      source_filter)
    
    st.markdown(f"**Total active openings: {len(opportunities)}**")
    st.divider()

    render_paginated_cards(opportunities, key='current')
