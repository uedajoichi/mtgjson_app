import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


def get_state_path() -> Path:
    """Get or create state file path."""
    data_dir = os.environ.get("MTG_DATA_DIR", "data")
    state_path = Path(data_dir) / "sync_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    return state_path


def load_state() -> Dict[str, Any]:
    """Load sync state (last sync time, file hash, size, etc.)."""
    state_path = get_state_path()
    if not state_path.exists():
        return {"last_sync": None, "file_hash": None, "file_size": None}

    try:
        with open(state_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load state: {e}")
        return {"last_sync": None, "file_hash": None, "file_size": None}


def save_state(state: Dict[str, Any]) -> None:
    """Save sync state to JSON file."""
    state_path = get_state_path()
    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        print(f"✓ State saved to {state_path}")
    except Exception as e:
        print(f"Error saving state: {e}")


def update_sync_state(file_hash: str, file_size: int) -> None:
    """Update sync state with new hash, size, and timestamp."""
    state = load_state()
    state.update(
        {
            "last_sync": datetime.utcnow().isoformat(),
            "file_hash": file_hash,
            "file_size": file_size,
        }
    )
    save_state(state)
