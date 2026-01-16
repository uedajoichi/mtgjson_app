import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import os


def upsert_rows(rows):
    """Upsert foreign data rows into the database."""
    if not rows:
        print("No rows to upsert")
        return

    db_path = os.environ.get("MTG_DB_PATH", "data/AllPrintings.sqlite")
    path_obj = Path(db_path)

    if not path_obj.exists():
        print(f"Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Insert or replace foreign data
        upserted_count = 0
        skipped_count = 0

        for row in rows:
            try:
                # Check if foreign_data table exists
                c.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='foreign_data'"
                )
                if not c.fetchone()[0]:
                    print("⚠ foreign_data table doesn't exist. Skipping upsert.")
                    break

                c.execute(
                    """
                    INSERT OR REPLACE INTO foreign_data 
                    (card_uuid, language, name, face_name, text, flavor_text, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("card_uuid"),
                        row.get("language"),
                        row.get("name"),
                        row.get("face_name"),
                        row.get("text"),
                        row.get("flavor_text"),
                        row.get("type"),
                    ),
                )
                upserted_count += 1
            except sqlite3.IntegrityError as e:
                # Foreign key constraint might fail if card doesn't exist
                skipped_count += 1
                print(f"Skipped row for {row.get('card_uuid')}: {e}")
            except Exception as e:
                print(f"Error upserting row: {e}")
                skipped_count += 1

        conn.commit()
        conn.close()

        print(f"✓ Upserted {upserted_count} rows")
        if skipped_count > 0:
            print(f"⚠ Skipped {skipped_count} rows due to errors")

    except Exception as e:
        print(f"Error in upsert_rows: {e}")
