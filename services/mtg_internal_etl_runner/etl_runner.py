import os
import sys

from mtg_internal_etl import etl, sqlite_downloader, sqlite_init


def main():
    print("Starting MTG ETL Runner")

    # Get DB path from env or default
    db_path = os.environ.get("MTG_DB_PATH", "data/AllPrintings.sqlite")

    try:
        # Download SQLite if needed
        print(f"\n[1/2] Downloading SQLite to {db_path}...")
        sqlite_downloader.download_sqlite(db_path)

        # Initialize and verify DB
        print(f"\n[2/2] Verifying and initializing DB...")
        sqlite_init.verify_and_init(db_path)

        print("\n✓ ETL setup complete. DB ready at:", db_path)

        # Run ETL logic (stub for now)
        print("\nRunning ETL (placeholder)...")
        etl.run_etl_once()

    except Exception as e:
        print(f"\n✗ ETL failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
