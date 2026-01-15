import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH: Optional[str] = None
_CONN: Optional[sqlite3.Connection] = None


def _get_db_path() -> str:
    """Get SQLite database path from env or default."""
    return os.environ.get("MTG_DB_PATH", "data/AllPrintings.sqlite")


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
        _CONN = sqlite3.connect(path, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
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
