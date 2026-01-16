import os
from . import sqlite_reader, upsert


def run_etl_once():
    """
    Perform ETL run: Extract foreign data from SQLite and load into foreign_data table.
    """
    print("ETL: Extracting foreign data from AllPrintings.sqlite...")

    db_path = os.environ.get("MTG_DB_PATH", "data/AllPrintings.sqlite")

    # Extract foreign data from the main SQLite database
    foreign_data_rows = sqlite_reader.extract_foreign_data(db_path)

    if foreign_data_rows:
        print(f"ETL: Loading {len(foreign_data_rows)} foreign data entries...")
        upsert.upsert_rows(foreign_data_rows)
        print("✓ ETL run completed successfully")
    else:
        print("⚠ No foreign data found to load")
