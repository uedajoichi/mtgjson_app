import os
from . import sqlite_reader, upsert


def run_etl_once(test_mode: bool = False):
    """
    Perform ETL run: Extract foreign data from JSON/SQLite and load into foreign_data table.

    Args:
        test_mode: If True, limit JSON download to first 3 sets (for testing)
    """
    print("ETL: Extracting foreign data from MTGJSONs...")

    db_path = os.environ.get("MTG_DB_PATH")
    if not db_path:
        data_dir = os.environ.get("MTG_DATA_DIR", "data")
        db_path = os.path.join(data_dir, "AllPrintings.sqlite")

    # Check for test mode environment variable
    test_mode = test_mode or os.environ.get("MTG_TEST_MODE", "").lower() == "true"

    # Extract foreign data (tries JSON first, falls back to SQLite)
    if test_mode:
        print("⚠ Running in TEST MODE (limited data)")
        foreign_data_rows = sqlite_reader.extract_foreign_data_json_only(
            db_path, limit_sets=3
        )
    else:
        foreign_data_rows = sqlite_reader.extract_foreign_data(db_path)

    if foreign_data_rows:
        print(f"ETL: Loading {len(foreign_data_rows)} foreign data entries...")
        upsert.upsert_rows(foreign_data_rows)
        print("✓ ETL run completed successfully")
    else:
        print("⚠ No foreign data found to load")
