import hashlib
import os
from pathlib import Path
from typing import Tuple, Optional
from urllib.request import urlopen
from urllib.error import URLError

from . import state

MTGJSON_SQLITE_URL = "https://mtgjson.com/api/v5/AllPrintings.sqlite"


def _compute_file_hash(path: str) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
    except Exception as e:
        print(f"Error computing hash: {e}")
        return ""
    return sha256.hexdigest()


def check_remote_metadata() -> Optional[Tuple[int, str]]:
    """
    Check remote file metadata (size, Last-Modified).
    Returns: (file_size, last_modified) or None if check fails.
    """
    try:
        req = urlopen(MTGJSON_SQLITE_URL)
        content_length = int(req.headers.get("content-length", 0))
        last_modified = req.headers.get("last-modified", "")
        req.close()
        return (content_length, last_modified)
    except URLError as e:
        print(f"Error checking remote metadata: {e}")
        return None


def has_update(dest: str) -> bool:
    """
    Check if remote file has changed compared to local state.
    Returns True if update available, False if no change.
    """
    local_state = state.load_state()
    remote_meta = check_remote_metadata()

    if remote_meta is None:
        print("⚠ Cannot check remote metadata, proceeding with update")
        return True

    remote_size, remote_modified = remote_meta
    local_size = local_state.get("file_size")
    local_modified = local_state.get("last_sync")

    # Size changed → update needed
    if remote_size > 0 and local_size != remote_size:
        print(f"Size change detected: {local_size} → {remote_size} bytes")
        return True

    # Last-Modified changed → update needed
    if remote_modified and local_modified and remote_modified != local_modified:
        print(f"Modification time changed: {local_modified} → {remote_modified}")
        return True

    # No change
    print(f"✓ No changes detected (size: {local_size}, modified: {local_modified})")
    return False


def download_sqlite(dest: str) -> str:
    """
    Download AllPrintings.sqlite with change detection.
    - If no changes, returns existing path and discards temp file
    - If changes, downloads and updates state
    Returns: path to AllPrintings.sqlite
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if update is needed
    if dest_path.exists():
        print(f"Local SQLite exists at {dest}")
        if not has_update(dest):
            print("✓ No update needed")
            return str(dest_path)
        print("Update available, re-downloading...")

    # Download to temporary file
    temp_path = dest_path.with_suffix(".tmp")
    print(f"\nDownloading AllPrintings.sqlite from {MTGJSON_SQLITE_URL}...")

    try:
        with urlopen(MTGJSON_SQLITE_URL) as r:
            total_size = int(r.headers.get("content-length", 0)) / (1024 * 1024)
            print(f"Expected size: {total_size:.1f} MB")

            with open(temp_path, "wb") as f:
                downloaded = 0
                while True:
                    chunk = r.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (10 * 1024 * 1024) == 0:
                        print(f"  Downloaded {downloaded / (1024 * 1024):.1f} MB...")

        # Verify download
        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise Exception("Downloaded file is empty")

        # Move temp to final location
        if dest_path.exists():
            dest_path.unlink()
        temp_path.rename(dest_path)

        # Compute hash and update state
        file_size = dest_path.stat().st_size
        file_hash = _compute_file_hash(str(dest_path))
        state.update_sync_state(file_hash, file_size)

        print(f"✓ Downloaded to {dest}")
        print(f"  Size: {file_size / (1024 * 1024):.1f} MB")
        print(f"  Hash: {file_hash[:16]}...")

        return str(dest_path)

    except Exception as e:
        print(f"✗ Download failed: {e}")
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
        raise
