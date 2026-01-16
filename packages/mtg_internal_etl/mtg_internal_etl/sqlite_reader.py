import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional


def read_sqlite(path: str) -> List[Dict[str, Any]]:
    """Read all cards from SQLite database."""
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


def _resolve_demo_uuids(
    db_path: str, rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Resolve demo rows to real card UUIDs based on English card names."""
    path_obj = Path(db_path)
    if not path_obj.exists():
        return rows

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    english_names = sorted(
        {row.get("english_name") for row in rows if row.get("english_name")}
    )
    name_to_uuid = {}
    for name in english_names:
        c.execute("SELECT uuid FROM cards WHERE name = ? LIMIT 1", (name,))
        row = c.fetchone()
        if row:
            name_to_uuid[name] = row[0]

    resolved_rows = []
    for row in rows:
        english_name = row.get("english_name")
        if english_name and english_name in name_to_uuid:
            new_row = dict(row)
            new_row["card_uuid"] = name_to_uuid[english_name]
            resolved_rows.append(new_row)
        elif english_name:
            # Skip demo rows that cannot be linked to a real card UUID.
            continue
        else:
            resolved_rows.append(row)

    conn.close()
    return resolved_rows


def _get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in c.fetchall()]


def _get_foreign_data_table(conn: sqlite3.Connection) -> Optional[str]:
    c = conn.cursor()
    candidates = [
        "cardForeignData",
        "card_foreign_data",
        "foreignData",
    ]
    for table in candidates:
        c.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if c.fetchone()[0]:
            return table
    return None


def _extract_foreign_data_from_db(db_path: str) -> List[Dict[str, Any]]:
    path_obj = Path(db_path)
    if not path_obj.exists():
        print(f"SQLite not found at {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    table = _get_foreign_data_table(conn)
    if not table:
        conn.close()
        print("⚠ No foreign data table found in SQLite")
        return []

    columns = _get_table_columns(conn, table)
    column_lookup = {name.lower(): name for name in columns}

    def pick_column(*options: str) -> Optional[str]:
        for option in options:
            key = option.lower()
            if key in column_lookup:
                return column_lookup[key]
        return None

    card_uuid_col = pick_column("card_uuid", "carduuid", "cardUuid", "uuid")
    language_col = pick_column("language")
    name_col = pick_column("name")
    face_name_col = pick_column("face_name", "faceName")
    text_col = pick_column("text")
    flavor_text_col = pick_column("flavor_text", "flavorText")
    type_col = pick_column("type")

    if not card_uuid_col or not language_col or not name_col:
        conn.close()
        print("⚠ Foreign data table missing required columns (uuid/language/name)")
        return []

    c = conn.cursor()
    c.execute(f"SELECT * FROM {table}")
    rows = c.fetchall()

    foreign_rows = []
    for row in rows:
        foreign_rows.append(
            {
                "card_uuid": row[card_uuid_col],
                "language": row[language_col],
                "name": row[name_col],
                "face_name": row[face_name_col] if face_name_col else None,
                "text": row[text_col] if text_col else None,
                "flavor_text": row[flavor_text_col] if flavor_text_col else None,
                "type": row[type_col] if type_col else None,
            }
        )

    conn.close()
    print(f"✓ Extracted {len(foreign_rows)} foreign data rows from {table}")
    return foreign_rows


def extract_foreign_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract foreign data using MTGJSON SQLite tables.
    """
    foreign_rows = _extract_foreign_data_from_db(db_path)
    if foreign_rows:
        return foreign_rows

    use_demo = os.environ.get("MTG_USE_DEMO_FOREIGN_DATA", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not use_demo:
        return []

    print(
        "⚠ Falling back to demo translation data (set MTG_USE_DEMO_FOREIGN_DATA=0 to disable)"
    )
    from . import demo_data

    demo_rows = demo_data.get_demo_foreign_data()
    return _resolve_demo_uuids(db_path, demo_rows)


def extract_foreign_data_json_only(
    db_path: str, limit_sets: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Extract foreign data from SQLite when JSON sources are unavailable.
    limit_sets parameter is ignored (kept for API consistency).
    """
    foreign_rows = _extract_foreign_data_from_db(db_path)
    if foreign_rows:
        return foreign_rows

    use_demo = os.environ.get("MTG_USE_DEMO_FOREIGN_DATA", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not use_demo:
        return []

    print("⚠ Using demo translation data (test/development mode)")
    from . import demo_data

    demo_rows = demo_data.get_demo_foreign_data()
    return _resolve_demo_uuids(db_path, demo_rows)
