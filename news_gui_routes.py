"""Routes for news room GUI: serve page + config API."""
import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("news_routes")

MODULE_DIR = Path(__file__).parent
GUI_HTML = MODULE_DIR / "news_config_gui.html"

async def news_gui_handler(request):
    """GET /news-config — serve the full News Room GUI."""
    from aiohttp import web
    if GUI_HTML.exists():
        return web.FileResponse(str(GUI_HTML))
    return web.json_response({"error": "GUI file not found"}, status=404)

async def news_config_get_handler(request):
    """GET /api/news/config?user_id=<uid> — return user's news config."""
    from aiohttp import web
    from state_manager import load_state, get_news_config
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    cfg = get_news_config(state, uid)
    # Find last run
    user = state.get("users", {}).get(uid, {})
    last_run = None
    for r in user.get("rooms", []):
        if r.get("type") == "news":
            last_run = r.get("config", {}).get("last_run_date")
    return web.json_response({
        "config": cfg,
        "last_run": last_run,
        "version": cfg.get("version", 1),
    })

async def news_config_post_handler(request):
    """POST /api/news/config — save user's news config."""
    from aiohttp import web
    from state_manager import load_state, save_state, save_news_config
    from news_config import validate_news_config
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    uid = body.get("user_id", "legacy_vaclav")
    config = body.get("config")
    if not config:
        return web.json_response({"error": "Missing config"}, status=400)

    # Validate
    try:
        validate_news_config(config)
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)

    state = load_state()
    save_news_config(state, uid, config)
    save_state(state)

    logger.info(f"📰 News config saved for {uid}")
    return web.json_response({"ok": True, "version": config.get("version", 1)})

async def news_config_validate_handler(request):
    """POST /api/news/config-validate — validate config without saving."""
    from aiohttp import web
    from news_config import validate_news_config
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    config = body.get("config")
    if not config:
        return web.json_response({"error": "Missing config"}, status=400)

    try:
        validate_news_config(config)
        return web.json_response({"valid": True})
    except ValueError as e:
        return web.json_response({"valid": False, "error": str(e)}, status=400)

async def news_config_reset_handler(request):
    """POST /api/news/config-reset — reset to defaults."""
    from aiohttp import web
    from state_manager import load_state, save_state, save_news_config
    from news_config import DEFAULT_NEWS_CONFIG
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    uid = body.get("user_id", "legacy_vaclav")
    state = load_state()
    save_news_config(state, uid, json.loads(json.dumps(DEFAULT_NEWS_CONFIG)))
    save_state(state)
    return web.json_response({"ok": True})

async def news_test_fetch_handler(request):
    """POST /api/news/test-fetch — test source connectivity."""
    from aiohttp import web
    from state_manager import load_state, get_news_config
    from news_room import fetch_rss_items
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    uid = body.get("user_id", "legacy_vaclav")
    state = load_state()
    cfg = get_news_config(state, uid)
    sources = [s for s in cfg.get("sources", []) if s.get("enabled")]

    items = await fetch_rss_items(sources, max_per_source=3)
    return web.json_response({
        "ok": True,
        "items_count": len(items),
        "sources_ok": len(sources),
        "sources_total": len(cfg.get("sources", [])),
    })

async def news_models_handler(request):
    """GET /api/news/models?provider=<name> — return models for a provider."""
    from aiohttp import web
    from news_config import LLM_MODELS_BY_PROVIDER
    provider = request.query.get("provider", "openrouter")
    models = LLM_MODELS_BY_PROVIDER.get(provider, [])
    return web.json_response({"provider": provider, "models": models})

async def news_refresh_handler(request):
    """POST /api/news/refresh — generate briefing now."""
    from aiohttp import web
    from state_manager import load_state, get_news_config
    from news_room import generate_briefing
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    uid = body.get("user_id", "legacy_vaclav")
    md = await generate_briefing(uid)
    return web.json_response({"ok": True, "briefing": md})

async def news_briefing_handler(request):
    """GET /api/news/briefing?user_id=<uid> — get latest briefing (existing)."""
    from aiohttp import web
    from state_manager import load_state
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    history = state.get("users", {}).get(uid, {}).get("news_history", [])
    today = datetime.now().strftime("%Y-%m-%d")
    if history and history[0]["date"].startswith(today):
        return web.json_response({"briefing": history[0]["markdown"], "cached": True})
    return web.json_response({
        "briefing": None, "cached": False,
        "message": "No briefing of today. Use POST /api/news/refresh."
    })

def register_news_routes(app):
    """Register all news room routes on the app."""
    app.router.add_get('/news-config', news_gui_handler)
    app.router.add_get('/api/news/config', news_config_get_handler)
    app.router.add_post('/api/news/config', news_config_post_handler)
    app.router.add_post('/api/news/config-validate', news_config_validate_handler)
    app.router.add_post('/api/news/config-reset', news_config_reset_handler)
    app.router.add_post('/api/news/test-fetch', news_test_fetch_handler)
    app.router.add_get('/api/news/models', news_models_handler)
    app.router.add_post('/api/news/refresh', news_refresh_handler)
    app.router.add_get('/api/news/briefing', news_briefing_handler)
