import streamlit as st
from datetime import date

def format_countdown(deadline_date):
    """
    Calculates days remaining from today and returns a formatted string.
    """
    if not deadline_date or str(deadline_date).strip() in ("None", "null", ""):
        return "🟢 Rolling Deadline / Open"
        
    if isinstance(deadline_date, str):
        deadline_date = date.fromisoformat(deadline_date)
        
    today = date.today()
    delta_days = (deadline_date - today).days
    
    if delta_days < 0:
        return "❌ Expired"
    elif delta_days == 0:
        return "🔥 Closes today!"
    elif delta_days <= 14:
        return f"🔥 Closes in {delta_days} days"
    else:
        return f"📅 Closes in {delta_days} days"

def format_location(row: dict) -> str:
    """
    Renders the geography of a role as a short label: the city for Indian
    postings, or an explicit remote badge for roles based outside India.
    Scrapers concatenate every location field a board exposes, so the raw
    string is trimmed down to the parts worth showing.
    """
    location = (row.get('location') or '').strip()
    location_type = row.get('location_type')

    # Work-mode words carry no geographic information on their own.
    noise = {'remote', 'onsite', 'on-site', 'hybrid', 'in office', 'in-office'}
    parts = [part.strip() for part in location.split('|') if part.strip()]
    parts = [part for part in parts if part.lower() not in noise]

    if location_type == 'Remote':
        # "Remote - EMEA" should read as "Remote (outside India) - EMEA".
        trimmed = []
        for part in parts:
            if part.lower().startswith('remote'):
                part = part[len('remote'):].strip(' -:,/')
            if part:
                trimmed.append(part)
        detail = ' - '.join(dict.fromkeys(trimmed))
        return f"Remote (outside India) - {detail}" if detail else "Remote (outside India)"

    if not parts:
        return 'India'

    # Prefer the most explicit Indian description, e.g. "Bengaluru, Karnataka, India".
    named = [part for part in parts if 'india' in part.lower()]
    return max(named, key=len) if named else parts[0]

def render_opportunity_card(row: dict):
    """
    Renders a clean, styled Streamlit card for a given opportunity row.
    """
    with st.container(border=True):
        st.markdown(f"### **{row['role_title']}**")
        st.markdown(f"#### {row['company_name']}")
        
        # Domain and Type as badges/pills
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.caption(f"🏢 {row['domain']}")
        with col2:
            st.caption(f"🎓 {row['opportunity_type']}")
        with col3:
            flag = "🌐" if row.get('location_type') == 'Remote' else "🇮🇳"
            st.caption(f"{flag} {format_location(row)}")
            
        source = row.get('source')
        if source:
            st.caption(f"via {source}")

        st.divider()
        
        # Dates
        st.markdown(f"**{format_countdown(row['application_deadline'])}**")
        program_start = row.get('program_start_date')
        if program_start and str(program_start).strip() not in ("None", "null", ""):
            st.caption(f"🚀 Program Starts: {program_start}")
        
        # Apply button aligned at the bottom
        st.link_button("Apply Now ↗", url=row['apply_url'])

def render_empty_state(message: str):
    """
    Displays a friendly message when no listings match the selected filters.
    """
    st.info(message, icon="ℹ️")

def render_paginated_cards(opportunities, key: str, page_size: int = 24):
    """
    Renders opportunity cards in a two column grid, paginated. The India-first
    boards return hundreds of listings, so rendering them all at once would
    make the page unusable.
    """
    total = len(opportunities)
    if total == 0:
        render_empty_state("No roles match your filters.")
        return

    page_count = (total + page_size - 1) // page_size

    if page_count > 1:
        page = st.selectbox(
            f"Page (1 of {page_count})",
            list(range(1, page_count + 1)),
            key=f"{key}_page",
        )
    else:
        page = 1

    start = (page - 1) * page_size
    subset = opportunities[start:start + page_size]
    st.caption(f"Showing {start + 1}-{start + len(subset)} of {total} listings")

    cols = st.columns(2)
    for index, opportunity in enumerate(subset):
        with cols[index % 2]:
            render_opportunity_card(opportunity)
