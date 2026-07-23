"""
Asistente KRK-9: chat REST con contexto de briefing + historial.
"""
import logging
from datetime import datetime

logger = logging.getLogger("krk9_assistant")

SYSTEM = (
    "You are KRK-9, Vaclav's personal assistant inside his English practice app. "
    "You know his news briefing, his English practice sessions, and his vocabulary progress. "
    "Be concise (max 3 sentences unless asked for detail), warm, and practical. "
    "If he asks about the news, use the briefing context provided. "
    "If he asks to do something you cannot do, say so plainly."
)

async def assistant_reply(uid: str, message: str) -> str:
    from state_manager import load_state, get_assistant_config
    from bot import call_openrouter

    state = load_state()
    cfg = get_assistant_config(state, uid)
    if not cfg.get("enabled", True):
        return "(Assistant disabled in settings)"

    user = state.get("users", {}).get(uid, {})
    briefing = user.get("news_history", [{}])[0].get("markdown", "(no briefing yet)")[:1200]
    sessions = user.get("sessions", [])
    last_session = sessions[-1]["topic"] if sessions else "(none)"

    context = (f"Latest briefing (may be old):\n{briefing}\n\n"
               f"Last practice session topic: {last_session}")

    try:
        reply = await call_openrouter(
            [{"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER MESSAGE: {message}"}],
            system=SYSTEM,
            temperature=0.7,
        )
        return reply or "(empty reply)"
    except Exception as e:
        logger.error(f"❌ assistant_reply: {e}")
        return "Sorry, my brain is not available right now. Try again in a moment."