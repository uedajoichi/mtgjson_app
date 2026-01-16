"""
Database migration utilities for adding foreign_data table to existing AllPrintings.sqlite
"""

import sqlite3
from pathlib import Path
from typing import Callable, Optional


def create_migration(
    name: str, migrate_fn: Callable[[sqlite3.Connection], None]
) -> Callable:
    """Decorator to create a named migration."""

    def wrapper(db_path: str) -> bool:
        """Execute a migration on the database."""
        path_obj = Path(db_path)
        if not path_obj.exists():
            print(f"Database not found at {db_path}")
            return False

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Check if migration has already been applied
            c.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sqlite_migrations'"
            )
            has_migrations_table = c.fetchone()[0]

            if not has_migrations_table:
                # Create migrations tracking table
                c.execute(
                    """
                    CREATE TABLE sqlite_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()

            # Check if this migration has been applied
            c.execute("SELECT COUNT(*) FROM sqlite_migrations WHERE name = ?", (name,))
            already_applied = c.fetchone()[0] > 0

            if already_applied:
                print(f"✓ Migration '{name}' already applied")
                conn.close()
                return True

            # Run the migration
            print(f"Running migration: {name}...")
            migrate_fn(conn)

            # Record the migration
            c.execute("INSERT INTO sqlite_migrations (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()

            print(f"✓ Migration '{name}' completed successfully")
            return True

        except Exception as e:
            print(f"✗ Migration '{name}' failed: {e}")
            return False

    wrapper.__name__ = f"migrate_{name}"
    return wrapper


def migrate_add_foreign_data_table(conn: sqlite3.Connection) -> None:
    """Migration: Add foreign_data table to existing AllPrintings.sqlite."""
    c = conn.cursor()

    # Check if table already exists
    c.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='foreign_data'"
    )
    if c.fetchone()[0] > 0:
        print("  foreign_data table already exists")
        return

    print("  Creating foreign_data table...")
    c.execute(
        """
        CREATE TABLE foreign_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_uuid TEXT NOT NULL,
            language TEXT NOT NULL,
            name TEXT,
            face_name TEXT,
            text TEXT,
            flavor_text TEXT,
            type TEXT,
            UNIQUE(card_uuid, language),
            FOREIGN KEY(card_uuid) REFERENCES cards(uuid)
        )
        """
    )

    print("  Creating indices...")
    c.execute("CREATE INDEX idx_foreign_data_card_uuid ON foreign_data(card_uuid)")
    c.execute("CREATE INDEX idx_foreign_data_language ON foreign_data(language)")
    c.execute("CREATE INDEX idx_foreign_data_name ON foreign_data(name COLLATE NOCASE)")

    conn.commit()
    print("  ✓ foreign_data table created with indices")


# Create the migration function
migrate_foreign_data = create_migration(
    "add_foreign_data_table", migrate_add_foreign_data_table
)


def run_migrations(db_path: str) -> bool:
    """Run all pending migrations."""
    print(f"Running migrations on {db_path}...")

    migrations = [
        ("add_foreign_data_table", migrate_foreign_data),
    ]

    all_success = True
    for name, migrate_fn in migrations:
        if not migrate_fn(db_path):
            all_success = False

    if all_success:
        print("✓ All migrations completed successfully")
    else:
        print("✗ Some migrations failed")

    return all_success
