import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH: Optional[str] = None
_CONN: Optional[sqlite3.Connection] = None


def _get_db_path() -> str:
    """Get SQLite database path from env or default."""
    db_path = os.environ.get("MTG_DB_PATH")
    if db_path:
        return db_path
    data_dir = os.environ.get("MTG_DATA_DIR", "data")
    return os.path.join(data_dir, "AllPrintings.sqlite")


def get_db_path() -> str:
    """Return the resolved SQLite database path without opening a connection."""
    return _get_db_path()


def _get_connection() -> sqlite3.Connection:
    """Get or create DB connection (cached)."""
    global _CONN, _DB_PATH
    path = _get_db_path()
    if _CONN is None or _DB_PATH != path:
        db_path_obj = Path(path)
        if not db_path_obj.exists():
            raise FileNotFoundError(
                f"AllPrintings.sqlite not found at {path}; "
                f"run ETL or set MTG_DB_PATH"
            )
        _CONN = sqlite3.connect(path, check_same_thread=False, timeout=10)
        _CONN.row_factory = sqlite3.Row
        _CONN.isolation_level = None  # Autocommit mode
        _DB_PATH = path
    return _CONN


def fetch_all_printings(dest: str) -> str:
    """Deprecated: kept for backward compatibility. Use SQLite via client instead."""
    import warnings

    warnings.warn("fetch_all_printings is deprecated; use SQLite", DeprecationWarning)
    return dest


def get_card_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Return first matching card by substring search (case-insensitive) from SQLite."""
    try:
        conn = _get_connection()
        c = conn.cursor()

        query = "%{}%".format(name.strip())
        c.execute(
            "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT 1", (query,)
        )
        row = c.fetchone()

        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Error querying card: {e}")
        return None


def find_cards(name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return all matching cards by substring search (case-insensitive)."""
    try:
        conn = _get_connection()
        c = conn.cursor()

        query = "%{}%".format(name.strip())
        c.execute(
            "SELECT * FROM cards WHERE name LIKE ? COLLATE NOCASE LIMIT ?",
            (query, limit),
        )
        rows = c.fetchall()

        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error querying cards: {e}")
        return []


def get_sets() -> List[Dict[str, Any]]:
    """Return list of all sets (if available in DB)."""
    try:
        conn = _get_connection()
        c = conn.cursor()

        # Try different potential set table names
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%set%'"
        )
        set_tables = c.fetchall()

        if set_tables:
            table_name = set_tables[0][0]
            c.execute(f"SELECT * FROM {table_name}")
            return [dict(row) for row in c.fetchall()]

        return []
    except Exception as e:
        print(f"Error fetching sets: {e}")
        return []


def count_cards() -> int:
    """Return total number of cards in the database."""
    try:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM cards")
        row = c.fetchone()
        return row[0] if row else 0
    except Exception as e:
        print(f"Error counting cards: {e}")
        return 0


def find_cards_by_language(
    name: str, language: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Return all matching cards by foreign name in specified language (case-insensitive)."""
    try:
        conn = _get_connection()
        c = conn.cursor()

        query = "%{}%".format(name.strip())
        c.execute(
            """
            SELECT fd.card_uuid, fd.name, fd.language, fd.face_name, fd.text, fd.flavor_text, fd.type,
                   c.name as english_name, c.uuid
            FROM foreign_data fd
            LEFT JOIN cards c ON fd.card_uuid = c.uuid
            WHERE fd.name LIKE ? COLLATE NOCASE AND fd.language = ?
            LIMIT ?
            """,
            (query, language, limit),
        )
        rows = c.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error querying cards by language: {e}")
        return []


def get_card_with_translations(card_uuid: str) -> Optional[Dict[str, Any]]:
    """Return a card with all its foreign translations."""
    try:
        conn = _get_connection()
        c = conn.cursor()

        # Get base card
        c.execute("SELECT * FROM cards WHERE uuid = ? LIMIT 1", (card_uuid,))
        card_row = c.fetchone()
        if not card_row:
            return None

        card_dict = dict(card_row)

        # Get foreign data for this card
        c.execute(
            """
            SELECT language, name, face_name, text, flavor_text, type
            FROM foreign_data
            WHERE card_uuid = ?
            ORDER BY language
            """,
            (card_uuid,),
        )
        translations = c.fetchall()
        card_dict["foreign_data"] = [dict(row) for row in translations]

        return card_dict
    except Exception as e:
        print(f"Error fetching card with translations: {e}")
        return None


def search_cards_advanced(
    name: Optional[str] = None,
    colors: Optional[List[str]] = None,
    card_type: Optional[str] = None,
    mana_cost: Optional[str] = None,
    set_code: Optional[str] = None,
    rarity: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Advanced card search with multiple filters (AND logic).

    Args:
        name: Card name (substring, case-insensitive)
        colors: List of colors (e.g., ['W', 'U', 'B', 'R', 'G'])
        card_type: Card type substring (e.g., 'Creature', 'Sorcery')
        mana_cost: Mana cost substring (e.g., '{0}', '{1}{B}')
        set_code: Set code (e.g., 'LEA', '2ED')
        rarity: Rarity (e.g., 'Common', 'Rare', 'Mythic Rare')
        limit: Max results to return

    Returns:
        List of matching card dicts
    """
    try:
        conn = _get_connection()
        c = conn.cursor()

        # Build WHERE clause dynamically
        where_parts = []
        params = []

        if name:
            where_parts.append("name LIKE ? COLLATE NOCASE")
            params.append(f"%{name.strip()}%")

        if colors:
            # Match cards containing ANY of the specified colors
            # Assuming 'colors' column exists (might be JSON or comma-separated)
            color_conditions = " OR ".join(["colors LIKE ?" for _ in colors])
            where_parts.append(f"({color_conditions})")
            params.extend([f"%{c}%" for c in colors])

        if card_type:
            where_parts.append("type LIKE ? COLLATE NOCASE")
            params.append(f"%{card_type.strip()}%")

        if mana_cost:
            where_parts.append("manaCost LIKE ? COLLATE NOCASE")
            params.append(f"%{mana_cost.strip()}%")

        if set_code:
            where_parts.append("setCode = ? COLLATE NOCASE")
            params.append(set_code.strip())

        if rarity:
            where_parts.append("rarity LIKE ? COLLATE NOCASE")
            params.append(f"%{rarity.strip()}%")

        # Build final query
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = f"SELECT * FROM cards WHERE {where_clause} LIMIT ?"
        params.append(limit)

        c.execute(query, params)
        rows = c.fetchall()

        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error in advanced search: {e}")
        return []


def get_card_by_set_and_number(
    set_code: str, card_number: str
) -> Optional[Dict[str, Any]]:
    """
    Get a card by set code and card number.

    Args:
        set_code: Set code (e.g., 'LEA', '2ED', 'M21')
        card_number: Card number in set (e.g., '1', '42a')

    Returns:
        Card dict with foreign_data if available, or None if not found
    """
    try:
        conn = _get_connection()
        c = conn.cursor()

        # Query the cards table with setCode and number
        c.execute(
            "SELECT * FROM cards WHERE setCode = ? COLLATE NOCASE AND number = ? COLLATE NOCASE LIMIT 1",
            (set_code.strip(), card_number.strip()),
        )
        card_row = c.fetchone()

        if not card_row:
            return None

        card_dict = dict(card_row)

        # Get foreign translations if the foreign_data table exists
        try:
            c.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='foreign_data'"
            )
            has_foreign_table = c.fetchone()[0] > 0

            if has_foreign_table:
                c.execute(
                    """
                    SELECT language, name, face_name, text, flavor_text, type
                    FROM foreign_data
                    WHERE card_uuid = ?
                    ORDER BY language
                    """,
                    (card_dict.get("uuid"),),
                )
                translations = c.fetchall()
                card_dict["foreign_data"] = [dict(row) for row in translations]
        except Exception as e:
            print(f"Warning: Failed to fetch foreign_data: {e}")
            card_dict["foreign_data"] = []

        return card_dict
    except Exception as e:
        print(f"Error querying card by set and number: {e}")
        return None
