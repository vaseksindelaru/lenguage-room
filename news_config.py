"""News Room GUI: configuration editor and management endpoints."""
import json, logging
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger("news_config")
MODULE_DIR = Path(__file__).parent

# ─── Default configuration schema ────────────────────────────────────────────
DEFAULT_NEWS_CONFIG = {
    "version": 1,
    "scheduling": {
        "update_hour": 4,
        "frequency": "daily",       # daily | hourly | manual
        "timezone": "local",
        "cooldown_minutes": 60,
        "max_retries": 3,
        "retry_delay_seconds": 10,
    },
    "sources": [
        {"id": "hn",   "name": "Hacker News", "type": "rss", "url": "https://hnrss.org/frontpage",
         "enabled": True,  "max_items_per_source": 5,
         "keywords_filter": "", "exclude_keywords": "", "language": "en"},
        {"id": "arstechnica-ai", "name": "Ars Technica AI", "type": "rss",
         "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
         "enabled": True,  "max_items_per_source": 5,
         "keywords_filter": "", "exclude_keywords": "", "language": "en"},
        {"id": "bbc-news", "name": "BBC News", "type": "rss",
         "url": "https://feeds.bbci.co.uk/news/rss.xml",
         "enabled": True,  "max_items_per_source": 5,
         "keywords_filter": "", "exclude_keywords": "", "language": "en"},
        {"id": "nyt-world", "name": "NYT World", "type": "rss",
         "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
         "enabled": True,  "max_items_per_source": 5,
         "keywords_filter": "", "exclude_keywords": "", "language": "en"},
    ],
    "agent": {
        "llm_model": "z-ai/glm-5.1",
        "llm_provider": "openrouter",
        "system_prompt": (
            "Eres el agente de recolección de noticias de KRK-9. "
            "Tu tarea es recopilar noticias en inglés de las fuentes indicadas, "
            "filtrar las más relevantes y generar un briefing matutino para Vaclav. "
            "El briefing debe ser en ESPAÑOL, con tono eficiente y cálido. "
            "Usa EXACTAMENTE esta estructura markdown:\n"
            "## 📰 Top News\n(para cada noticia: título en negrita — fuente, una frase de por qué importa)\n"
            "## ✅ Suggested Tasks\n(3 checkboxes accionables)\n"
            "## 🗣️ Vocabulary\n(5 palabras/expresiones nuevas con definición breve)\n"
            "## 💬 Discussion Questions\n(3 preguntas abiertas para practicar)\n\n"
            "Noticias de hoy:"
        ),
        "temperature": 0.6,
        "max_tokens": 2000,
        "summarize_style": "markdown_sections",
        "target_language": "es",
        "source_language": "en",
    },
    "output": {
        "max_briefing_items": 6,
        "sections": ["top_news", "suggested_tasks", "vocabulary", "discussion_questions", "sources_links"],
        "include_article_snippets": True,
        "max_snippet_length": 200,
        "include_original_links": True,
    },
    "caching": {
        "cache_hours": 24,
        "history_days": 30,
        "max_history_entries": 30,
        "persist_to_obsidian": True,
        "obsidian_folder": "KRK9/Briefings",
    },
    "notifications": {
        "notify_on_briefing_ready": True,
        "notify_discord_channel": "",
        "notify_via_tts": False,
        "tts_voice": "en-US-AndrewNeural",
        "error_notification": True,
    },
    "agentic": {
        "autonomous_mode": False,
        "agent_depth": "medium",      # shallow | medium | deep
        "auto_discovery": False,
        "dedup_strategy": "title",    # title | link | hash
        "max_source_age_hours": 48,
    },
    "credentials": {
        "newsapi_key": "",
        "guardian_api_key": "",
        "openweather_api_key": "",
        "google_ai_studio_key": "",
    },
    "debug": {
        "dry_run": False,
        "log_level": "INFO",
        "test_mode": False,
    },
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_news_config(state, uid):
    """Devuelve la config de noticias del usuario (o defaults)."""
    user = state.get("users", {}).get(uid, {})
    saved = user.get("news_config")
    if saved and isinstance(saved, dict):
        out = json.loads(json.dumps(DEFAULT_NEWS_CONFIG))  # deep copy
        out.update(saved)
        return out
    return json.loads(json.dumps(DEFAULT_NEWS_CONFIG))

def save_news_config(state, uid, new_config):
    """Guarda la config en memoria (persistencia via save_state externa)."""
    user = state.setdefault("users", {}).setdefault(uid, {})
    user["news_config"] = new_config
    return True

def validate_news_config(config):
    """Valida la config. Lanza ValueError si algo está mal."""
    if not isinstance(config, dict):
        raise ValueError("Config must be a dict")
    sched = config.get("scheduling", {})
    h = sched.get("update_hour", 4)
    if not (0 <= h <= 23):
        raise ValueError(f"update_hour must be 0-23, got {h}")
    if sched.get("frequency") not in ("daily", "hourly", "manual"):
        raise ValueError(f"Invalid frequency: {sched.get('frequency')}")
    sources = config.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    seen_ids = set()
    for s in sources:
        sid = s.get("id", "")
        if sid in seen_ids:
            raise ValueError(f"Duplicate source id: {sid}")
        seen_ids.add(sid)
        if not s.get("url", "").startswith(("http://", "https://")):
            raise ValueError(f"Source {sid}: invalid URL")
    return True
