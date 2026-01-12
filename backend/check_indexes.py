"""
Database Index Checker & Creator
Run: python check_indexes.py
"""

import pymysql
from urllib.parse import urlparse, unquote

# Parse DATABASE_URL from .env
DATABASE_URL = "mysql+aiomysql://mansilh1_nuno:wcDR%25QY0BGYt@mansilhas.pt:3306/mansilh1_eleiloes"

# Parse the URL
url = DATABASE_URL.replace("mysql+aiomysql://", "mysql://")
parsed = urlparse(url)

config = {
    "host": parsed.hostname,
    "port": parsed.port or 3306,
    "user": parsed.username,
    "password": unquote(parsed.password),  # Decode %25 -> %
    "database": parsed.path.lstrip("/"),
}

# Expected indexes
EXPECTED_INDEXES = {
    "events": [
        ("idx_events_active", ["terminado", "cancelado", "data_fim"]),
        ("idx_events_tipo", ["tipo_id"]),
        ("idx_events_distrito", ["distrito"]),
    ],
    "price_history": [
        ("idx_price_history_ref_time", ["reference", "recorded_at"]),
    ],
    "refresh_logs": [
        ("idx_refresh_logs_state", ["state", "created_at"]),
    ],
}

# SQL to create indexes
CREATE_STATEMENTS = [
    "CREATE INDEX idx_events_active ON events(terminado, cancelado, data_fim)",
    "CREATE INDEX idx_events_tipo ON events(tipo_id)",
    "CREATE INDEX idx_events_distrito ON events(distrito)",
    "CREATE INDEX idx_price_history_ref_time ON price_history(reference, recorded_at DESC)",
    "CREATE INDEX idx_refresh_logs_state ON refresh_logs(state, created_at)",
]


def main():
    print("=" * 50)
    print("Database Index Checker")
    print("=" * 50)
    print(f"Host: {config['host']}")
    print(f"Database: {config['database']}")
    print()

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        # Get all custom indexes
        cursor.execute("""
            SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s
            AND INDEX_NAME LIKE 'idx_%%'
            GROUP BY TABLE_NAME, INDEX_NAME
            ORDER BY TABLE_NAME, INDEX_NAME
        """, (config['database'],))

        existing = {(row[0], row[1]): row[2].split(',') for row in cursor.fetchall()}

        print("Current idx_* indexes:")
        print("-" * 50)

        if existing:
            for (table, idx_name), columns in existing.items():
                print(f"  {table}.{idx_name}: ({', '.join(columns)})")
        else:
            print("  (none found)")

        print()
        print("Expected indexes:")
        print("-" * 50)

        missing = []
        for table, indexes in EXPECTED_INDEXES.items():
            for idx_name, columns in indexes:
                status = "OK" if (table, idx_name) in existing else "MISSING"
                icon = "✓" if status == "OK" else "✗"
                print(f"  {icon} {table}.{idx_name}: ({', '.join(columns)}) - {status}")
                if status == "MISSING":
                    missing.append(idx_name)

        print()

        if missing:
            print(f"Missing {len(missing)} indexes!")
            response = input("Create missing indexes? (y/n): ").strip().lower()

            if response == 'y':
                print()
                print("Creating indexes...")
                for stmt in CREATE_STATEMENTS:
                    idx_name = stmt.split()[2]  # Extract index name
                    if idx_name in missing:
                        try:
                            print(f"  Creating {idx_name}...", end=" ")
                            cursor.execute(stmt)
                            conn.commit()
                            print("OK")
                        except Exception as e:
                            print(f"ERROR: {e}")

                print()
                print("Done! Run this script again to verify.")
        else:
            print("All indexes are present!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
