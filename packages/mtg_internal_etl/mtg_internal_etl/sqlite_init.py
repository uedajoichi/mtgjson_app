import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def verify_and_init(db_path: str) -> None:
    """Verify SQLite has required tables. Create indices if missing."""
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check main tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5")
    tables = c.fetchall()
    print(f"Found {len(tables)} tables in DB")

    # Typically MTGJSON sqlite has 'cards' table
    c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cards'")
    has_cards = c.fetchone()[0]
    if has_cards:
        print("✓ Cards table exists")

        # Add index on name if missing
        c.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_cards_name'"
        )
        has_idx = c.fetchone()[0]
        if not has_idx:
            print("Creating index on cards(name)...")
            c.execute("CREATE INDEX idx_cards_name ON cards(name COLLATE NOCASE)")
            conn.commit()
            print("✓ Index created")
        else:
            print("✓ Index already exists")
    else:
        print("⚠ Cards table not found (expected: LEA, 2ED, etc. as sets)")

    conn.close()
