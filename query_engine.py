from datetime import date
from database import get_db_connection
from classifier import classify_horizon

def get_available_sources():
    """Returns the distinct sources currently present in the database."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DISTINCT source FROM opportunities "
        "WHERE location_type IN ('India', 'Remote') ORDER BY source"
    ).fetchall()
    conn.close()
    return [row['source'] for row in rows if row['source']]

def get_opportunities(time_bucket: str, domain_filter: str = None, type_filter: str = None,
                      location_filter: str = None, source_filter: str = None):
    """
    Retrieves opportunities from the database filtered by domain, type and
    location, and then buckets them by time_bucket using classify_horizon.

    Only roles based in India, or fully remote roles outside India, are ever
    returned. Pass location_filter='India' or 'Remote', and source_filter with
    a value from get_available_sources(), to narrow further.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hard geography guard, independent of what the scrapers wrote.
    query = "SELECT * FROM opportunities WHERE location_type IN ('India', 'Remote')"
    params = []

    if location_filter:
        query += " AND location_type = ?"
        params.append(location_filter)

    if source_filter:
        query += " AND source = ?"
        params.append(source_filter)
    
    if domain_filter:
        query += " AND domain = ?"
        params.append(domain_filter)
        
    if type_filter:
        query += " AND opportunity_type = ?"
        params.append(type_filter)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        deadline_val = row['application_deadline']
        if deadline_val and str(deadline_val).strip() not in ("None", "null", ""):
            deadline_date = date.fromisoformat(str(deadline_val))
            horizon = classify_horizon(deadline_date, row['status'])
        else:
            # If no deadline is provided, default to CURRENT if status is CURRENT, else 1_MONTH
            horizon = 'CURRENT' if row['status'] == 'CURRENT' else '1_MONTH'
        if horizon == time_bucket:
            results.append(dict(row))
            
    return results

if __name__ == '__main__':
    print("Running Phase 1 Verification Tests...\n")
    
    # Test 1: All CURRENT Quant Internships
    print("--- Test 1: All CURRENT Quant Internships ---")
    current_quant = get_opportunities('CURRENT', domain_filter='Quant', type_filter='Internship')
    if not current_quant:
        print("No matches found (expected if randomness didn't generate this exact combo)")
    for opp in current_quant:
        print(f"- {opp['company_name']}: {opp['role_title']} (Deadline: {opp['application_deadline']})")
        
    # Test 2: All 3_MONTHS Fellowships (across any domain)
    print("\n--- Test 2: All 3_MONTHS Fellowships ---")
    three_month_fellowships = get_opportunities('3_MONTHS', type_filter='Fellowship')
    if not three_month_fellowships:
        print("No matches found (expected if randomness didn't generate this exact combo)")
    for opp in three_month_fellowships:
        print(f"- {opp['company_name']}: {opp['role_title']} in {opp['domain']} (Deadline: {opp['application_deadline']})")
        
    # Test 3: All 6_MONTHS Tech roles (Internship or Fellowship)
    print("\n--- Test 3: All 6_MONTHS Tech roles ---")
    six_month_tech = get_opportunities('6_MONTHS', domain_filter='Tech')
    if not six_month_tech:
        print("No matches found (expected if randomness didn't generate this exact combo)")
    for opp in six_month_tech:
        print(f"- {opp['company_name']}: {opp['role_title']} ({opp['opportunity_type']}, Deadline: {opp['application_deadline']})")
    
    print("\nVerification complete.")
