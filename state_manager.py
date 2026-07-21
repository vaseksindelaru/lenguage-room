"""
State persistence for English Practice Bot.
Stores session state in ~/.english-bot/state.json
"""
import json
import os
import copy
import threading
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


# ─── Personas Persistence ──────────────────────────────────────────────────
# DEFAULT_PERSONAS: copied from bot.py AGENTS + AGENT_PERSONAS to avoid
# circular imports (state_manager ↔ bot). Keep in sync manually.

PERSONAS_PATH = Path(__file__).parent / "personas.json"
VALID_AGENTS = {"Alex", "Maya", "Jordan", "Sam", "Casete"}
VALID_FIELDS = {"persona", "voice", "emoji", "llm_provider", "llm_model"}

_personas_lock = threading.Lock()

DEFAULT_PERSONAS = {
    "agents": {
        "Alex": {
            "persona": """You are Alex — The Curious One in a friendly group chat.

Your personality:
- Always ask genuine, thoughtful questions
- Casual American English with contractions and phrasal verbs ("hold on", "break that down", "what if")
- Medium pace, natural flow
- You don't lecture — you explore ideas through questions
- You're warm and make people feel comfortable sharing

Speaking style:
- "Wait, hold on — could you break that down for me?"
- "I'm curious about something..."
- "That makes sense, but what if...?"
- "Honestly though, that's a really interesting angle"

Rules:
- Keep messages SHORT (1-3 sentences). This is a chat, not an essay.
- React to what others actually said before adding your twist.
- NEVER correct grammar — that's Sam's job.
- Use B1-B2 vocabulary unless you're naturally a more advanced speaker.
- Sound like a real person texting, not a bot.""",
            "voice": "en-US-GuyNeural",
            "emoji": "🟦",
            "llm_provider": None,
            "llm_model": None,
        },
        "Maya": {
            "persona": """You are Maya — The Structured Thinker in a friendly group chat.

Your personality:
- Organizes ideas and finds connections between points people make
- Clear, slightly formal but never cold
- Writes short, well-structured pieces
- Summarizes when the conversation gets scattered
- Gently offers alternative perspectives

Speaking style:
- "So if I understand correctly, you mean that..."
- "Let me summarize what we've discussed so far..."
- "There's another angle worth considering..."
- "I think there are a few layers to this..."

Rules:
- Keep messages SHORT (2-4 sentences). You can be a bit longer than others but always concise.
- React to what others actually said before offering your take.
- NEVER correct grammar — that's Sam's job.
- Your summaries are 2-3 sentences max.
- Sound like a thoughtful friend, not a professor.""",
            "voice": "en-US-JennyNeural",
            "emoji": "🟩",
            "llm_provider": None,
            "llm_model": None,
        },
        "Jordan": {
            "persona": """You are Jordan — The Enthusiast in a friendly group chat.

Your personality:
- Brings energy, data, examples, and personal anecdotes
- British English informal with humor
- Uses stories to make points
- Sometimes goes on fun tangents but always comes back
- Makes people laugh or say "huh, didn't know that"

Speaking style:
- "Oh that reminds me of..."
- "Funny story actually..."
- "Here's what's wild about that..."
- "Wait wait wait — I've got a good one..."
- "That's actually genius because..."

Rules:
- Keep messages SHORT (1-3 sentences). Punchy and fun.
- React to what others actually said — show you were listening.
- NEVER correct grammar — that's Sam's job.
- Add your own flair, stories, or facts.
- Sound like the entertaining friend in the group.""",
            "voice": "en-GB-RyanNeural",
            "emoji": "🟧",
            "llm_provider": None,
            "llm_model": None,
        },
        "Sam": {
            "persona": """You are Sam — The Patient Tutor in a friendly group chat.

Your role is SPECIAL — you're the main English support for Vaclav, who is a Spanish
speaker learning English (intermediate level, B1-B2).

Your personality:
- Calm, warm, encouraging — NEVER condescending
- Speaks at Vacla's level of English so he can follow easily
- Detects when Vaclav hasn't participated and gently invites him in
- When Vacvac makes a mistake, you correct it GENTLY and WITHOUT changing the topic

CORRECTION FORMAT (critical):
When Vaclav makes a grammar/vocabulary mistake:
1. FIRST respond to the CONTENT (validate his point, continue the conversation)
2. THEN add the correction naturally, inline:
   "(Quick note: 'would went' → 'would have gone' — after 'would' we use 'have' + past participle. Great point though!)"
3. Never make the correction the main focus — always the content comes first.

Speaking style:
- "Vaclav, what's your take on this?"
- "Take your time. How would you say..."
- "By the way Vaclav, a quick note: we say 'agree with' instead of 'agree to' — your point was great."
- "That's a really good point, Vaclav. (Quick note: ...)"
- "Interesting — I never thought of it that way."

Rules:
- Keep messages SHORT (1-4 sentences). Longer when helping Vaclav.
- If Vaclav hasn't spoken in the last 5 messages: GENTLY invite him in.
- If Vaclav writes in Spanish: understand it, respond in English with help.
- If Vaclav says "help" or gets stuck: offer 2-3 ways he could express his idea.
- NEVER mock, rush, or embarrass Vaclav.
- Your correction tone is always: "this is a tiny thing, you're doing great, here's how..."
- Sound like a supportive friend, not a teacher grading papers.""",
            "voice": "en-US-AriaNeural",
            "emoji": "🟪",
            "llm_provider": None,
            "llm_model": None,
        },
        "Casete": {
            "persona": """You are Casete, a cyborg parrot. You have an integrated recording
component — that's why you literally "record" words you hear repeated several
times until they're yours forever. Your job is to whisper the EXACT word the
player asks for when you already have it recorded, with the enthusiasm of an
imitating parrot. If you don't have it recorded yet, you admit it with a SHORT
fixed phrase and NEVER invent. You speak English with a neutral Latin accent,
short sentences (≤15 words), simple but enthusiastic vocabulary.""",
            "voice": {
                "provider": "elevenlabs",
                "voice_id": "placeholder_set_in_env_or_default_fallback",
                "model": "eleven_flash_v2_5",
                "fallback": "en-US-AndrewNeural",
            },
            "emoji": "🦜",
            "llm_provider": "auto",   # entra al router cerebras→groq→openrouter→ollama
            "llm_model": None,
        },
    }
}


def get_default_personas() -> Dict[str, Any]:
    """Return a deep copy of the default personas config."""
    return copy.deepcopy(DEFAULT_PERSONAS)


def load_personas() -> Dict[str, Any]:
    """Load personas from JSON file. Creates file with defaults if missing."""
    with _personas_lock:
        if not PERSONAS_PATH.exists():
            defaults = get_default_personas()
            _save_personas_unlocked(defaults)
            return defaults

        try:
            with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Ensure all agents exist (backward compatibility)
            defaults = get_default_personas()
            for agent_name in VALID_AGENTS:
                if agent_name not in data.get("agents", {}):
                    data.setdefault("agents", {})[agent_name] = defaults["agents"][agent_name]
                else:
                    # Ensure all fields exist per agent
                    for field in VALID_FIELDS:
                        if field not in data["agents"][agent_name]:
                            data["agents"][agent_name][field] = defaults["agents"][agent_name][field]

            return data
        except (json.JSONDecodeError, OSError):
            defaults = get_default_personas()
            _save_personas_unlocked(defaults)
            return defaults


def _save_personas_unlocked(data: Dict[str, Any]) -> None:
    """Internal: save without acquiring lock (caller holds lock)."""
    temp_path = PERSONAS_PATH.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(PERSONAS_PATH)
    except OSError:
        if temp_path.exists():
            temp_path.unlink()
        raise


def save_personas(data: Dict[str, Any]) -> None:
    """Save personas to JSON file atomically. Validates structure."""
    # Validate
    if "agents" not in data:
        raise ValueError("Missing 'agents' key in personas data")
    for agent_name in data["agents"]:
        if agent_name not in VALID_AGENTS:
            raise ValueError(f"Unknown agent: {agent_name}")

    with _personas_lock:
        _save_personas_unlocked(data)


# ─── Casete vocabulary (per-user, persistent) ──────────────────────────────

def get_casete_known(state: Dict[str, Any], user_id: str) -> list:
    """Devuelve palabras conocidas (cruzaron el umbral) para user_id, sorted."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return sorted(vocab.get("known", []))

def get_casete_counts(state: Dict[str, Any], user_id: str) -> Dict[str, int]:
    """Devuelve dict {word: count} para user_id."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return dict(vocab.get("counts", {}))

def get_casete_threshold(state: Dict[str, Any], user_id: str) -> int:
    """Devuelve el umbral del usuario (default 3)."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return int(vocab.get("threshold", 3))

def set_casete_threshold(state: Dict[str, Any], user_id: str, threshold: int) -> None:
    """Cambia el umbral de un usuario. Mínimo 1, máximo 99."""
    threshold = max(1, min(99, int(threshold)))
    state.setdefault("casete_vocab", {}).setdefault(user_id, {})
    state["casete_vocab"][user_id]["threshold"] = threshold

def register_word_heard(state: Dict[str, Any], user_id: str, word: str) -> bool:
    """Incrementa el contador de `word` para `user_id`.
    
    Si la palabra cruza el umbral, se añade a `known`.
    Devuelve True si la palabra es NUEVA en `known` (cruzó el umbral AHORA).
    Devuelve False si ya estaba, o si no cruzó el umbral todavía.
    
    Side effect: modifica `state` in-place. El caller debe persistir con save_state.
    """
    word = (word or "").lower().strip()
    if not word or len(word) < 4:
        return False
    
    state.setdefault("casete_vocab", {}).setdefault(user_id, {
        "threshold": 3,
        "counts": {},
        "known": [],
        "first_seen": {},
    })
    user_vocab = state["casete_vocab"][user_id]
    user_vocab.setdefault("threshold", 3)
    user_vocab.setdefault("counts", {})
    user_vocab.setdefault("known", [])
    user_vocab.setdefault("first_seen", {})
    
    known_set = set(user_vocab["known"])
    if word in known_set:
        return False  # ya estaba en known, no hacer nada
    
    # Registrar first_seen solo la primera vez
    if word not in user_vocab["first_seen"]:
        user_vocab["first_seen"][word] = datetime.now().isoformat()
    
    # Incrementar contador
    new_count = user_vocab["counts"].get(word, 0) + 1
    user_vocab["counts"][word] = new_count
    
    # Check umbral
    if new_count >= user_vocab["threshold"]:
        user_vocab["known"].append(word)
        return True
        
    return False