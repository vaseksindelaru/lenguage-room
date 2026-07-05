"""
State persistence for English Practice Bot.
Stores session state in ~/.english-bot/state.json
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

STATE_DIR = Path.home() / ".english-bot"
STATE_PATH = STATE_DIR / "state.json"
MAX_HISTORY = 50

DEFAULT_STATE = {
    "conversation_history": [],
    "current_topic_index": 0,
    "custom_topic": None,
    "topic_locked": True,
    "user_config": {"tts_speed": 1.0, "voices": {}},
    "last_session": None,
    "paused": False,
}


def ensure_state_dir() -> None:
    """Create state directory if it doesn't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict[str, Any]:
    """Load state from JSON file. Returns default if not found or corrupted."""
    ensure_state_dir()
    
    if not STATE_PATH.exists():
        return DEFAULT_STATE.copy()
    
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # Ensure all keys exist (backward compatibility)
        for key, value in DEFAULT_STATE.items():
            if key not in state:
                state[key] = value
        
        # Trim history if too long
        if len(state.get("conversation_history", [])) > MAX_HISTORY:
            state["conversation_history"] = state["conversation_history"][-MAX_HISTORY:]
        
        return state
    except (json.JSONDecodeError, OSError):
        # Corrupted or unreadable - return default
        return DEFAULT_STATE.copy()


def save_state(state: Dict[str, Any]) -> None:
    """Save state to JSON file atomically."""
    ensure_state_dir()
    
    # Trim history before saving
    if len(state.get("conversation_history", [])) > MAX_HISTORY:
        state["conversation_history"] = state["conversation_history"][-MAX_HISTORY:]
    
    # Update last_session timestamp
    state["last_session"] = datetime.now().isoformat()
    
    # Atomic write: write to temp then rename
    temp_path = STATE_PATH.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        temp_path.replace(STATE_PATH)
    except OSError:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


def reset_state() -> Dict[str, Any]:
    """Reset to default state."""
    state = DEFAULT_STATE.copy()
    save_state(state)
    return state


def get_welcome_message(state: Dict[str, Any], topics: Optional[list] = None) -> str:
    """Generate welcome back message from state."""
    if topics is None:
        from bot import TOPICS as topics

    last_session = state.get("last_session")
    topic_idx = state.get("current_topic_index", 0)
    topic_name = topics[topic_idx]["theme"] if 0 <= topic_idx < len(topics) else "Unknown"
    
    if last_session:
        try:
            dt = datetime.fromisoformat(last_session)
            last_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            last_str = "recently"
    else:
        last_str = "first time"
    
    paused_str = " (paused)" if state.get("paused") else ""
    
    return f"Welcome back! Last session: {last_str}. Topic: {topic_name}{paused_str}. Resuming..."