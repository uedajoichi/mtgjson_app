import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional


def read_sqlite(path: str) -> List[Dict[str, Any]]:
    """Read all cards with foreign data from SQLite database."""
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"SQLite not found at {path}")
        return []

    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Check if cards table exists
        c.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cards'"
        )
        has_cards = c.fetchone()[0]
        if not has_cards:
            print("⚠ Cards table not found in SQLite")
            return []

        # Read all cards with their foreign data
        c.execute(
            """
            SELECT DISTINCT c.uuid, c.name, c.* FROM cards c
            LIMIT 100
            """
        )

        cards_data = []
        for row in c.fetchall():
            card_dict = dict(row)
            cards_data.append(card_dict)

        print(f"✓ Read {len(cards_data)} cards from SQLite")
        conn.close()
        return cards_data

    except Exception as e:
        print(f"Error reading SQLite: {e}")
        return []


def extract_foreign_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract foreign data from AllPrintings.sqlite.
    MTGSQLite stores foreign translations in the cards table as JSON or in separate columns.
    This function extracts and normalizes foreign data.
    """
    path_obj = Path(db_path)
    if not path_obj.exists():
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Check if cards table exists and has foreign data
        c.execute("PRAGMA table_info(cards)")
        columns = [col[1] for col in c.fetchall()]

        foreign_data_entries = []

        if "foreignData" in columns:
            # MTGSQLite stores foreignData as JSON string
            c.execute(
                """
                SELECT uuid, foreignData FROM cards 
                WHERE foreignData IS NOT NULL AND foreignData != ''
                """
            )

            import json

            for row in c.fetchall():
                card_uuid = row["uuid"]
                try:
                    foreign_list = json.loads(row["foreignData"])
                    if isinstance(foreign_list, list):
                        for fd in foreign_list:
                            foreign_data_entries.append(
                                {
                                    "card_uuid": card_uuid,
                                    "language": fd.get("language", "Unknown"),
                                    "name": fd.get("name"),
                                    "face_name": fd.get("faceName"),
                                    "text": fd.get("text"),
                                    "flavor_text": fd.get("flavorText"),
                                    "type": fd.get("type"),
                                }
                            )
                except json.JSONDecodeError:
                    pass

        conn.close()

        if foreign_data_entries:
            print(f"✓ Extracted {len(foreign_data_entries)} foreign data entries")
        else:
            print("⚠ No foreign data found in cards table")

        return foreign_data_entries

    except Exception as e:
        print(f"Error extracting foreign data: {e}")
        return []
