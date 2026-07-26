"""News Room: briefing matutino por usuario (RSS + LLM resumen)."""
import logging
import os
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("news_room")

def _get_google_ai_key() -> str:
    """Returns the Google AI Studio API key from env or .env."""
    return os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")

async def _call_google_ai(prompt: str, system: str = "", temperature: float = 0.6, max_tokens: int = 2000) -> str | None:
    """Calls Google AI Studio API via generativeai. Returns text or None."""
    api_key = _get_google_ai_key()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        messages = []
        if system:
            messages.append({"role": "user", "parts": [system + "\n\n" + prompt]})
        else:
            messages.append({"role": "user", "parts": [prompt]})
        response = model.generate_content(
            messages,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text
    except Exception as e:
        logger.error(f"❌ Google AI Studio briefing falló: {e}")
        return None

async def fetch_rss_items(sources: List[Dict], max_per_source: int = 5) -> List[Dict]:
    """Descarga items de fuentes RSS habilitadas."""
    import feedparser
    items = []
    for src in sources:
        if not src.get("enabled", True) or src.get("type") != "rss":
            continue
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:max_per_source]:
                items.append({
                    "title": entry.get("title", "(sin título)"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:400],
                    "source": src.get("name", src["id"]),
                })
            logger.info(f"📰 {src['name']}: {min(len(feed.entries), max_per_source)} items")
        except Exception as e:
            logger.warning(f"⚠️ RSS {src.get('name')} falló: {e}")
    return items

def build_briefing_prompt(items: List[Dict], max_items: int, agent_cfg: Dict = None) -> str:
    if agent_cfg is None:
        agent_cfg = {}
    llm_model = agent_cfg.get("llm_model", "z-ai/glm-5.1")
    target_language = agent_cfg.get("target_language", "es")
    system_prompt = agent_cfg.get("system_prompt", "")

    lines = [f"{i+1}. [{it['source']}] {it['title']}\n   {it['summary'][:200]}\n   {it['link']}"
             for i, it in enumerate(items[:max_items])]
    return (
        f"{system_prompt}\n"
        "Noticias de hoy:\n" + "\n\n".join(lines)
    )

async def generate_briefing(uid: str) -> str:
    """Genera y guarda el briefing del usuario. Devuelve el markdown."""
    from state_manager import load_state, save_state, get_news_config
    from bot import call_openrouter

    state = load_state()
    cfg = get_news_config(state, uid)
    sources = cfg.get("sources", [])
    max_items = cfg.get("output", {}).get("max_briefing_items", 6)
    items = await fetch_rss_items(sources, 5)

    if not items:
        md = f"# ☕ Briefing {datetime.now():%Y-%m-%d}\n\n⚠️ No se pudieron descargar noticias hoy."
    else:
        agent_cfg = cfg.get("agent", {})
        prompt = build_briefing_prompt(items, max_items, agent_cfg)
        temperature = agent_cfg.get("temperature", 0.6)
        body = None
        try:
            body = await call_openrouter(
                [{"role": "user", "content": prompt}],
                system=agent_cfg.get("system_prompt",
                    "You are the news briefing agent for KRK-9. "
                    "Output ONLY markdown, no preamble."),
                temperature=temperature,
                max_tokens=agent_cfg.get("max_tokens", 2000),
            )
        except Exception as e:
            logger.warning(f"⚠️ OpenRouter briefing falló: {e}, intentando Google AI Studio...")
        if body is None:
            body = await _call_google_ai(
                prompt,
                system=agent_cfg.get("system_prompt",
                    "You are the news briefing agent for KRK-9. "
                    "Output ONLY markdown, no preamble."),
                temperature=temperature,
            )
        if body is None:
            logger.error("❌ Ambos LLM fallaron")
            body = "(LLM no disponible — lista cruda)\n" + "\n".join(f"- {i['title']} ({i['source']})" for i in items)

        md = (f"---\ntype: krk9-news-briefing\ndate: \"{datetime.now():%Y-%m-%d}\"\n"
              f"user: \"{uid}\"\n---\n\n# ☕ Morning Briefing — {datetime.now():%Y-%m-%d}\n\n{body}\n")

    # Guardar en state
    user = state.setdefault("users", {}).setdefault(uid, {})
    user.setdefault("news_history", []).insert(0, {"date": datetime.now().isoformat(), "markdown": md})
    user["news_history"] = user["news_history"][:30]     # conservar 30
    # Marcar que hoy ya corrió
    for r in user.get("rooms", []):
        if r.get("type") == "news":
            r.setdefault("config", {})["last_run_date"] = f"{datetime.now():%Y-%m-%d}"
    save_state(state)
    logger.info(f"📰 Briefing generado para {uid} ({len(md)} chars)")
    return md

if __name__ == "__main__":
    import asyncio, sys
    uid = sys.argv[1] if len(sys.argv) > 1 else "legacy_vaclav"
    print(asyncio.run(generate_briefing(uid))[:1500])