"""
One-shot ingestion: wipes the table, rebuilds the schema and repopulates it
from every source. Use scheduler.py --run-now for an incremental refresh that
keeps existing rows.
"""

import requests

from database import get_db_connection, init_db
from classifier import classify_location, is_safe_url
from sources import collect_all, summarise

def run():
    print("--- Wiping table & rebuilding schema ---")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS opportunities")
    conn.commit()
    conn.close()

    init_db()
    print("[SUCCESS] Schema recreated in 'opportunities.db'.")

    all_roles = collect_all()

    if not all_roles:
        print("No roles found across any source.")
        return

    unsafe = [r for r in all_roles if not is_safe_url(r.get('apply_url'))]
    if unsafe:
        print(f"[SECURITY] Dropped {len(unsafe)} listings with a non-http(s) apply link.")
    all_roles = [r for r in all_roles if is_safe_url(r.get('apply_url'))]

    # Final geography gate: India, or fully remote when the role is outside India.
    rejected = [r for r in all_roles if classify_location(r.get('location')) is None]
    if rejected:
        print(f"[FILTER] Dropped {len(rejected)} roles failing the India/remote gate.")
    all_roles = [r for r in all_roles if classify_location(r.get('location')) is not None]

    print("--- Persisting to database ---")
    conn = get_db_connection()
    cursor = conn.cursor()
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

    inserted = 0
    for opp in all_roles:
        try:
            cursor.execute(upsert_sql, (
                opp['company_name'], opp['role_title'], opp['opportunity_type'],
                opp['domain'], opp['status'], opp['application_deadline'],
                opp['program_start_date'], opp.get('location'),
                opp['location_type'], opp.get('source', 'ATS'), opp['apply_url']
            ))
            inserted += 1
        except Exception as e:
            print(f"Failed to insert {opp['apply_url']}: {e}")

    conn.commit()
    conn.close()

    print(f"[SUCCESS] Stored {inserted} verified internship/fellowship roles.")

    by_source, by_location, by_domain = summarise(all_roles)

    print("\nBy source:")
    for name, count in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f" - {name}: {count}")

    print("\nBy domain:")
    for name, count in sorted(by_domain.items(), key=lambda kv: -kv[1]):
        print(f" - {name}: {count}")

    print("\nBy geography:")
    print(f" - Based in India: {by_location.get('India', 0)}")
    print(f" - Remote outside India: {by_location.get('Remote', 0)}")

    hr_keywords = ["recruiter", "recruiting", "talent", "sourcer", "senior", "lead",
                   "staff", "director", "vp", "manager"]
    leaked = [r for r in all_roles if any(kw in r['role_title'].lower() for kw in hr_keywords)]
    if leaked:
        print(f"\n[WARNING] {len(leaked)} senior/HR roles leaked through the gate:")
        for r in leaked[:10]:
            print(f"  !! {r['role_title']} at {r['company_name']}")
    else:
        print("\n[VERIFIED] Zero senior/recruiting roles stored.")

    print("\nSample listings:")
    for role in all_roles[:6]:
        print(f"  - [{role.get('source')}] {role['role_title'][:44]} at {role['company_name'][:24]} "
              f"({role['domain']} | {role['location_type']}: {role['location'][:32]})")

if __name__ == '__main__':
    run()
