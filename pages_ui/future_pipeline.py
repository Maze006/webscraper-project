import streamlit as st
import sys
import os

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query_engine import get_opportunities
from ui_components import render_paginated_cards

def render_future_page(domain_filter=None, type_filter=None, location_filter=None,
                       source_filter=None):
    st.header("⏳ Future Opportunity Pipeline")
    st.caption("India-based internships, plus fully remote roles from outside India.")
    
    tabs = st.tabs(["In 1 Month", "In 3 Months", "In 6 Months", "In 1 Year"])
    buckets = ['1_MONTH', '3_MONTHS', '6_MONTHS', '1_YEAR']
    
    for i, tab in enumerate(tabs):
        with tab:
            time_bucket = buckets[i]
            opportunities = get_opportunities(time_bucket, domain_filter, type_filter,
                                              location_filter, source_filter)
            render_paginated_cards(opportunities, key=f"future_{time_bucket}")
