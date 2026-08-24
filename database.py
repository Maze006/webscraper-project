import sqlite3

DATABASE_NAME = 'opportunities.db'

def get_db_connection():
    """
    Returns a connection to the SQLite database with row_factory set to sqlite3.Row.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database by creating the opportunities table if it doesn't exist,
    then migrates any pre-existing table to the geography-aware schema.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            role_title TEXT NOT NULL,
            opportunity_type TEXT CHECK(opportunity_type IN ('Internship', 'Fellowship')) NOT NULL,
            domain TEXT CHECK(domain IN ('Tech', 'Finance', 'Quant', 'Research Lab')) NOT NULL,
            status TEXT CHECK(status IN ('CURRENT', 'UPCOMING')) NOT NULL,
            application_deadline DATE,
            program_start_date DATE,
            location TEXT,
            location_type TEXT CHECK(location_type IN ('India', 'Remote')) NOT NULL DEFAULT 'India',
            source TEXT NOT NULL DEFAULT 'ATS',
            apply_url TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

    migrate_db()

def migrate_db():
    """
    Adds the location and source columns to a legacy table and drops every row that predates
    the geography gate (India-only, or remote when the role is outside India).
    Rows without a proven location cannot be trusted, so they are removed and
    will be repopulated on the next ingestion run.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    existing = {row['name'] for row in cursor.execute("PRAGMA table_info(opportunities)")}

    added = []
    if 'location' not in existing:
        cursor.execute("ALTER TABLE opportunities ADD COLUMN location TEXT")
        added.append('location')
    if 'location_type' not in existing:
        cursor.execute("ALTER TABLE opportunities ADD COLUMN location_type TEXT")
        added.append('location_type')
    if 'source' not in existing:
        cursor.execute("ALTER TABLE opportunities ADD COLUMN source TEXT NOT NULL DEFAULT 'ATS'")
        added.append('source')

    # Purge anything that does not satisfy the geography gate.
    cursor.execute(
        "DELETE FROM opportunities WHERE location_type IS NULL OR location_type NOT IN ('India', 'Remote')"
    )
    purged = cursor.rowcount

    conn.commit()
    conn.close()

    if added:
        print(f"[MIGRATION] Added columns: {', '.join(added)}")
    if purged:
        print(f"[MIGRATION] Removed {purged} rows that fail the India/remote gate.")

    return added, purged

if __name__ == '__main__':
    init_db()
    print(f"Database '{DATABASE_NAME}' initialized successfully.")
