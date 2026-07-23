"""News Room: briefing matutino por usuario (RSS + LLM resumen)."""
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("news_room")

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

def build_briefing_prompt(items: List[Dict], max_items: int) -> str:
    lines = [f"{i+1}. [{it['source']}] {it['title']}\n   {it['summary'][:200]}\n   {it['link']}"
             for i, it in enumerate(items[:max_items])]
    return (
        "Eres la secretaria ejecutiva de Vaclav. Genera su briefing matutino en INGLÉS, "
        "tono eficiente y cálido, EXACTAMENTE estas secciones markdown:\n"
        "## 📰 Top News\n(para cada noticia: **título en negrita** — fuente, y UNA frase de por qué importa)\n"
        "## ✅ Suggested Tasks\n(3 checkboxes accionables relacionadas con las noticias)\n\n"
        "Noticias de hoy:\n" + "\n\n".join(lines)
    )

async def generate_briefing(uid: str) -> str:
    """Genera y guarda el briefing del usuario. Devuelve el markdown."""
    from state_manager import load_state, save_state, get_news_config
    from bot import call_openrouter

    state = load_state()
    cfg = get_news_config(state, uid)
    items = await fetch_rss_items(cfg.get("sources", []), 5)

    if not items:
        md = f"# ☕ Briefing {datetime.now():%Y-%m-%d}\n\n⚠️ No se pudieron descargar noticias hoy."
    else:
        prompt = build_briefing_prompt(items, cfg.get("max_items", 6))
        try:
            body = await call_openrouter(
                [{"role": "user", "content": prompt}],
                system="You are a precise executive secretary. Output ONLY markdown, no preamble.",
                temperature=0.6,
            )
        except Exception as e:
            logger.error(f"❌ LLM briefing falló: {e}")
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