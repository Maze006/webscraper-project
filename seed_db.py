import random
from datetime import date, timedelta
from database import get_db_connection, init_db
from classifier import classify_location

def seed_database():
    """
    Seeds the opportunities database with realistic mock data based on specified date buckets.
    """
    today = date.today()
    
    # Requirements mapping:
    # 6 rows 'CURRENT': status 'CURRENT', application_deadline >= today
    # 5 rows '1_MONTH': status 'UPCOMING', application_deadline 10-28 days out
    # 5 rows '3_MONTHS': status 'UPCOMING', application_deadline 40-80 days out
    # 5 rows '6_MONTHS': status 'UPCOMING', application_deadline 100-160 days out
    # 4 rows '1_YEAR': status 'UPCOMING', application_deadline 200-300+ days out
    
    buckets = [
        {'status': 'CURRENT', 'min_days': 0, 'max_days': 15, 'count': 6},
        {'status': 'UPCOMING', 'min_days': 10, 'max_days': 28, 'count': 5},
        {'status': 'UPCOMING', 'min_days': 40, 'max_days': 80, 'count': 5},
        {'status': 'UPCOMING', 'min_days': 100, 'max_days': 160, 'count': 5},
        {'status': 'UPCOMING', 'min_days': 200, 'max_days': 350, 'count': 4},
    ]
    
    companies = {
        'Tech': ['Google', 'Meta', 'Apple', 'Microsoft', 'Amazon', 'Netflix'],
        'Finance': ['Goldman Sachs', 'JPMorgan', 'Morgan Stanley', 'BlackRock'],
        'Quant': ['Jane Street', 'Two Sigma', 'Citadel', 'Hudson River Trading'],
        'Research Lab': ['DeepMind', 'OpenAI', 'CERN', 'Fermilab', 'MIT Media Lab', 'Allen Institute']
    }
    
    roles = {
        'Internship': [
            'Software Engineering Intern', 'Data Science Intern', 
            'Quantitative Analyst Intern', 'Research Intern', 'Product Management Intern'
        ],
        'Fellowship': [
            'AI Research Fellow', 'Postdoctoral Fellow', 
            'Quant Research Fellow', 'Visiting Fellow', 'Engineering Fellowship'
        ]
    }
    
    # Mock geographies: Indian offices, plus remote-only roles outside India.
    locations = [
        'Bengaluru, India', 'Hyderabad, India', 'Pune, India', 'Gurugram, India',
        'Mumbai, India', 'Chennai, India', 'Noida, India',
        'Remote - Global', 'Remote - EMEA', 'Remote - Americas',
    ]

    domains = list(companies.keys())
    opportunity_types = list(roles.keys())
    
    mock_opportunities = []
    
    for bucket in buckets:
        for _ in range(bucket['count']):
            domain = random.choice(domains)
            company_name = random.choice(companies[domain])
            opportunity_type = random.choice(opportunity_types)
            role_title = random.choice(roles[opportunity_type])
            
            # Calculate deadline dynamically
            days_out = random.randint(bucket['min_days'], bucket['max_days'])
            application_deadline = today + timedelta(days=days_out)
            
            # Program start typically happens some time after the deadline
            start_days_out = random.randint(60, 180)
            program_start_date = application_deadline + timedelta(days=start_days_out)
            
            apply_url = f"https://www.{company_name.lower().replace(' ', '')}.com/careers/{random.randint(1000,99999)}"
            
            location = random.choice(locations)
            location_type = classify_location(location)

            mock_opportunities.append((
                company_name,
                role_title,
                opportunity_type,
                domain,
                bucket['status'],
                application_deadline.isoformat(),
                program_start_date.isoformat(),
                location,
                location_type,
                apply_url
            ))
            
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing rows to make the script idempotent
    cursor.execute("DELETE FROM opportunities")
    
    # Insert new mock rows
    insert_sql = '''
        INSERT INTO opportunities (
            company_name, role_title, opportunity_type, domain, 
            status, application_deadline, program_start_date,
            location, location_type, apply_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    cursor.executemany(insert_sql, mock_opportunities)
    
    conn.commit()
    inserted_count = len(mock_opportunities)
    conn.close()
    
    print(f"Successfully cleared and seeded {inserted_count} mock opportunities into the database.")

if __name__ == '__main__':
    seed_database()
