import os
import sys
import time

from mtg_internal_etl import etl, sqlite_downloader, sqlite_init, migrate


def main():
    print("Starting MTG ETL Runner")

    # Get DB path from env or default
    db_path = os.environ.get("MTG_DB_PATH")
    if not db_path:
        data_dir = os.environ.get("MTG_DATA_DIR", "data")
        db_path = os.path.join(data_dir, "AllPrintings.sqlite")

    # Check for mode
    demo_mode = os.environ.get("MTG_DEMO_MODE", "").lower() == "true"
    test_mode = os.environ.get("MTG_TEST_MODE", "").lower() == "true"

    if demo_mode:
        print("⚠ DEMO MODE - Using sample translation data")
    elif test_mode:
        print("⚠ TEST MODE - Limited JSON data")

    mode = "demo" if demo_mode else ("test" if test_mode else "")

    interval_raw = os.environ.get("MTG_ETL_INTERVAL_MINUTES", "").strip()
    interval_minutes = int(interval_raw) if interval_raw.isdigit() else 0

    while True:
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
            etl.run_etl_once(test_mode=test_mode)

        except Exception as e:
            print(f"\n✗ ETL failed: {e}", file=sys.stderr)
            if interval_minutes <= 0:
                sys.exit(1)

        if interval_minutes <= 0:
            break

        print(f"\n⏳ Sleeping for {interval_minutes} minutes before next ETL run...")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
