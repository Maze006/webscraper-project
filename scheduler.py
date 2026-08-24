import os
import argparse
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from database import get_db_connection, init_db
from sources import collect_all, summarise
from classifier import classify_location

def upsert_opportunities(opportunities_list):
    """
    Inserts new opportunities into the database, or updates existing ones based on apply_url.
    Returns the number of rows inserted and updated.
    """
    if not opportunities_list:
        return 0, 0

    # Final geography gate: only India-based roles, or remote roles outside India.
    dropped = [o for o in opportunities_list if classify_location(o.get('location')) is None]
    if dropped:
        print(f"[FILTER] Dropped {len(dropped)} roles failing the India/remote gate.")
    opportunities_list = [
        o for o in opportunities_list if classify_location(o.get('location')) is not None
    ]
    if not opportunities_list:
        return 0, 0

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all existing apply_urls to differentiate between Insert and Update for logging
    cursor.execute("SELECT apply_url FROM opportunities")
    existing_urls = {row['apply_url'] for row in cursor.fetchall()}
    
    inserted = 0
    updated = 0
    
    # SQLite UPSERT Syntax (requires SQLite 3.24.0+)
    upsert_sql = '''
        INSERT INTO opportunities (
            company_name, role_title, opportunity_type, domain, 
            status, application_deadline, program_start_date,
            location, location_type, source, apply_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(apply_url) DO UPDATE SET
            company_name=excluded.company_name,
            role_title=excluded.role_title,
            opportunity_type=excluded.opportunity_type,
            domain=excluded.domain,
            status=excluded.status,
            application_deadline=excluded.application_deadline,
            program_start_date=excluded.program_start_date,
            location=excluded.location,
            location_type=excluded.location_type,
            source=excluded.source
    '''
    
    for opp in opportunities_list:
        url = opp['apply_url']
        if url in existing_urls:
            updated += 1
        else:
            inserted += 1
            
        cursor.execute(upsert_sql, (
            opp['company_name'], opp['role_title'], opp['opportunity_type'], 
            opp['domain'], opp['status'], opp['application_deadline'], 
            opp['program_start_date'], opp.get('location'),
            opp['location_type'], opp.get('source', 'ATS'), url
        ))
        
    conn.commit()
    conn.close()
    
    return inserted, updated

def run_ingestion_pipeline():
    """
    Master job that aggregates opportunities from every source and persists them.
    """
    print(f"\n[{datetime.now().isoformat()}] Starting automated ingestion pipeline...")

    all_opportunities = collect_all()

    print("\n--- Saving to Database ---")
    init_db()
    inserted, updated = upsert_opportunities(all_opportunities)

    by_source, by_location, by_domain = summarise(all_opportunities)
    print(f"Ingestion complete! Inserted: {inserted}, Updated: {updated}.")
    print(f"Geography: {by_location.get('India', 0)} based in India, "
          f"{by_location.get('Remote', 0)} remote outside India.")
    print("By source: " + ", ".join(f"{k}={v}" for k, v in sorted(by_source.items())))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ingestion Pipeline Scheduler")
    parser.add_argument('--run-now', action='store_true', help="Run the pipeline immediately and exit")
    args = parser.parse_args()
    
    if args.run_now:
        run_ingestion_pipeline()
    else:
        scheduler = BlockingScheduler()
        # Schedule the job to run every 12 hours
        scheduler.add_job(run_ingestion_pipeline, 'interval', hours=12)
        print("Scheduler started. Pipeline will run every 12 hours. Press Ctrl+C to exit.")
        
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("Scheduler gracefully stopped.")
