import os
import sys

from mtg_internal_etl import etl, sqlite_downloader, sqlite_init, migrate


def main():
    print("Starting MTG ETL Runner")

    # Get DB path from env or default
    db_path = os.environ.get("MTG_DB_PATH", "data/AllPrintings.sqlite")

    try:
        # Download SQLite if needed
        print(f"\n[1/4] Downloading SQLite to {db_path}...")
        sqlite_downloader.download_sqlite(db_path)

        # Initialize and verify DB
        print(f"\n[2/4] Verifying and initializing DB...")
        sqlite_init.verify_and_init(db_path)

        # Run database migrations
        print(f"\n[3/4] Running database migrations...")
        migrate.run_migrations(db_path)

        print("\n✓ ETL setup complete. DB ready at:", db_path)

        # Run ETL logic
        print("\n[4/4] Running ETL (extracting foreign data)...")
        etl.run_etl_once()

    except Exception as e:
        print(f"\n✗ ETL failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
