"""
Audio WebSocket Server — streams TTS audio to browser for auto-playback
Run: python audio_server.py
Opens: http://localhost:8080
"""
import asyncio
import json
import base64
import logging
import tempfile
import re
from aiohttp import web
import os
import aiohttp
from aiohttp import web
import aiohttp_cors

# Load .env so API keys (CEREBRAS_API_KEY, OPENROUTER_API_KEY, OLLAMA_URL, etc.)
# are visible to the persona/LLM-provider detection in /api/personas.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Global: connected browser clients
connected_clients = set()

# Load voice webhook URL from environment or file
def load_voice_webhook_url():
    # First try environment variable
    url = os.getenv("DISCORD_VOICE_WEBHOOK_URL")
    if url:
        return url
    # Then try reading from file written by bot
    try:
        with open("/tmp/discord_voice_webhook.txt", "r") as f:
            return f.read().strip()
    except:
        pass
    return None


VOICE_WEBHOOK_URL = load_voice_webhook_url()

logger = logging.getLogger("audio-server")

async def websocket_handler(request):
    """WebSocket endpoint for browser audio playback."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    connected_clients.add(ws)
    print(f"🎧 Browser connected. Total: {len(connected_clients)}")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
    except Exception as e:
        print(f"WS error: {e}")
    finally:
        connected_clients.discard(ws)
        print(f"🎧 Browser disconnected. Total: {len(connected_clients)}")
    
    return ws


async def broadcast_audio(audio_bytes: bytes, agent_name: str):
    """Send audio to all connected browsers."""
    if not connected_clients:
        return
    
    # Encode as base64 for JSON transport
    b64 = base64.b64encode(audio_bytes).decode()
    payload = json.dumps({
        "type": "audio",
        "agent": agent_name,
        "data": b64,
        "mime": "audio/mpeg"
    })
    
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_str(payload)
        except Exception:
            dead.append(ws)
    
    for ws in dead:
        connected_clients.discard(ws)


async def index_handler(request):
    """Entry page: landing con cards de salas."""
    return web.FileResponse("./entry_page.html")

async def chat_handler(request):
    """Sala de conversación (la GUI existente)."""
    return web.FileResponse("./audio_player.html")

async def health_handler(request):
    return web.json_response({"status": "ok", "clients": len(connected_clients)})

async def broadcast_audio_http(request):
    """HTTP endpoint for bot to send audio to browsers."""
    try:
        data = await request.json()
        audio_bytes = data.get("data", "")
        agent_name = data.get("agent", "Unknown")
        
        if not audio_bytes:
            return web.json_response({"error": "No audio data"}, status=400)
        
        # audio_bytes comes as base64 string from bot
        import base64
        audio_data = base64.b64decode(audio_bytes)
        
        await broadcast_audio(audio_data, agent_name)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def voice_text_handler(request):
    """HTTP endpoint for browser to send recognized speech text to Discord."""
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        
        if not text:
            return web.json_response({"error": "No text provided"}, status=400)
        
        if not VOICE_WEBHOOK_URL:
            return web.json_response({"error": "Voice webhook not configured"}, status=500)
        
        # Send to Discord via webhook
        async with aiohttp.ClientSession() as session:
            async with session.post(
                VOICE_WEBHOOK_URL,
                json={"content": f"🎤 **Vaclav (voice):** {text}"},
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status >= 400:
                    return web.json_response({"error": f"Discord webhook failed: {resp.status}"}, status=500)
        
        return web.json_response({"status": "ok", "text": text})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def invite_handler(request):
    """Generate a Discord invite link (requires DISCORD_BOT_TOKEN in env)."""
    import os
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    guild_id = os.getenv("GUILD_ID", "")
    channel_id = os.getenv("CHANNEL_ID", "")
    
    if not bot_token:
        return web.json_response({"error": "DISCORD_BOT_TOKEN not set"}, status=500)
    
    if not guild_id or not channel_id:
        return web.json_response({"error": "GUILD_ID or CHANNEL_ID not set"}, status=500)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create invite for the guild (server)
            url = f"https://discord.com/api/v10/guilds/{guild_id}/invites"
            headers = {
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "max_age": 86400,  # 24 hours
                "max_uses": 0,      # unlimited
                "temporary": False
            }
            
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    invite_link = f"https://discord.gg/{data['code']}"
                    return web.json_response({"invite_link": invite_link})
                else:
                    error_text = await resp.text()
                    return web.json_response({"error": f"Failed to create invite: {resp.status} - {error_text}"}, status=500)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ─── Personas API ──────────────────────────────────────────────────────────

def _detect_llm_providers():
    """Detect which LLM providers are available based on .env keys."""
    providers = [
        {"id": "router", "label": "Default router chain", "models": []},
    ]

    # Cerebras — check for real key (not placeholder)
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
    if cerebras_key and len(cerebras_key) > 20 and not cerebras_key.startswith("tu_"):
        providers.append({
            "id": "cerebras", "label": "Cerebras API",
            "models": ["gpt-oss-120b"],
        })

    # Groq — check for real key
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and len(groq_key) > 20 and not groq_key.startswith("tu_") and "..." not in groq_key:
        providers.append({
            "id": "groq", "label": "Groq API",
            "models": ["llama-3.1-8b-instant"],
        })

    # OpenRouter — check for real key
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key and len(openrouter_key) > 20 and not openrouter_key.startswith("tu_"):
        providers.append({
            "id": "openrouter", "label": "OpenRouter API",
            "models": ["meta-llama/llama-3.3-70b-instruct:free"],
        })

    # Ollama — always available if OLLAMA_URL is set
    ollama_url = os.getenv("OLLAMA_URL", "")
    if ollama_url:
        providers.append({
            "id": "ollama", "label": "Local (Ollama)",
            "models": ["qwen2.5:3b"],
        })

    return providers


async def personas_get_handler(request):
    """GET /api/personas — Return current personas + available LLM providers."""
    from state_manager import load_personas, get_default_personas
    try:
        personas = load_personas()
        defaults = get_default_personas()
        providers = _detect_llm_providers()
        
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
        elevenlabs_available = bool(elevenlabs_key) and not elevenlabs_key.startswith("your_") and len(elevenlabs_key) > 20
        from tts_providers import EDGE_VOICES

        return web.json_response({
            "agents": personas.get("agents", {}),
            "defaults": defaults.get("agents", {}),
            "llm_providers": providers,
            "voice_providers": [
                {"id":"edge","label":"Edge TTS (humano)","available":True,"voices":EDGE_VOICES},
                {"id":"elevenlabs","label":"ElevenLabs (personaje)","available":elevenlabs_available,"voices":[]},
            ],
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def personas_post_handler(request):
    """POST /api/personas — Update a single agent's config."""
    from state_manager import load_personas, save_personas, VALID_AGENTS
    try:
        body = await request.json()
        agent_name = body.get("agent")

        if not agent_name or agent_name not in VALID_AGENTS:
            return web.json_response(
                {"error": f"Invalid agent: {agent_name}. Must be one of {sorted(VALID_AGENTS)}"},
                status=400)

        personas = load_personas()
        agent_data = personas["agents"].setdefault(agent_name, {})

        # Update only provided fields
        for field in ("persona", "voice", "emoji", "llm_provider", "llm_model"):
            if field in body:
                agent_data[field] = body[field]

        save_personas(personas)
        return web.json_response({"status": "ok", "agent": agent_name})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def tts_preview_handler(request):
    """POST /api/tts-preview — Generate TTS audio for voice preview.

    Returns audio/mpeg binary. Does NOT touch Discord or broadcast to browsers.
    Used exclusively by the 🎲 Preview button in the Settings modal.
    """
    try:
        body = await request.json()
        text = body.get("text", "").strip()
        voice = body.get("voice", "en-US-GuyNeural")

        if not text:
            return web.json_response({"error": "No text provided"}, status=400)

        # Clean text for TTS
        clean_text = re.sub(r'[🟦🟩🟧🟪🦜]', '', text).strip()
        if not clean_text:
            return web.json_response({"error": "Text is empty after cleaning"}, status=400)

        from tts_providers import generate_tts
        audio_data = await generate_tts(clean_text, voice)
        if not audio_data:
            return web.json_response({"error": "TTS failed (both providers)"}, status=500)

        if not audio_data:
            return web.json_response({"error": "TTS produced no audio"}, status=500)

        return web.Response(
            body=audio_data,
            content_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        logger.error(f"TTS preview error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def session_export_handler(request):
    """POST /api/session-export — Save session markdown to Obsidian (or fallback)."""
    from pathlib import Path
    try:
        body = await request.json()
        markdown = body.get("markdown", "")
        filename = body.get("filename", "")

        if not markdown or not filename:
            return web.json_response({"error": "Missing markdown or filename"}, status=400)

        # Sanitize filename
        filename = filename.replace("/", "_").replace("\\", "_")
        if not filename.endswith(".md"):
            filename += ".md"

        # Primary: Obsidian vault
        obsidian_dir = Path.home() / "Documents" / "Obsidian-Vault" / "Discord-Bot" / "Sessions"
        # Fallback: ./SESSIONS/ in the repo
        fallback_dir = Path(__file__).parent / "SESSIONS"

        if obsidian_dir.exists() or obsidian_dir.parent.exists():
            target_dir = obsidian_dir
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = fallback_dir
            target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return web.json_response({
            "status": "ok",
            "path": str(target_path),
            "is_obsidian": str(target_dir) == str(obsidian_dir),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def sessions_list_handler(request):
    """GET /api/sessions?user_id=... — lista sesiones del user."""
    user_id = request.query.get("user_id", "")
    if not user_id:
        return web.json_response({"error": "user_id required"}, status=400)
    from state_manager import load_state, list_user_sessions
    state = load_state()
    sessions = list_user_sessions(state, user_id)
    return web.json_response({"user_id": user_id, "sessions": sessions})

async def sessions_create_handler(request):
    """POST /api/sessions {user_id, topic?} — crea nueva sesión."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        topic = body.get("topic", "Untitled")
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)
        from state_manager import load_state, save_state, create_user_session
        state = load_state()
        sess = create_user_session(state, user_id, topic)
        save_state(state)
        return web.json_response({"status": "ok", "session": sess})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def sessions_resume_handler(request):
    """POST /api/sessions/resume {user_id, session_id} — marca activa."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        session_id = body.get("session_id", "")
        if not user_id or not session_id:
            return web.json_response({"error": "user_id and session_id required"}, status=400)
        from state_manager import load_state, save_state, set_active_session
        state = load_state()
        if set_active_session(state, user_id, session_id):
            save_state(state)
            return web.json_response({"status": "ok", "active_session": session_id})
        return web.json_response({"error": f"Session {session_id} not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def session_save_obsidian_handler(request):
    """POST /api/session/save-obsidian {user_id, session_id} — exporta sesión a Obsidian."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        session_id = body.get("session_id", "")
        if not user_id or not session_id:
            return web.json_response({"error": "user_id and session_id required"}, status=400)
        
        from state_manager import load_state
        from pathlib import Path
        from datetime import datetime
        state = load_state()
        user = state.get("users", {}).get(user_id, {})
        session = next((s for s in user.get("sessions", []) if s.get("id") == session_id), None)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found for user {user_id}"}, status=404)
        
        # Construir markdown
        today = datetime.now().strftime("%Y-%m-%d")
        messages = session.get("messages", [])
        duration_min = max(1, len(messages) * 2)  # estimación
        vocab = user.get("casete_vocab", {}).get("known", [])
        
        md_lines = [
            "---",
            "type: krk9-session",
            "project: KRK-9",
            f"date: \"{today}\"",
            f"topic: \"{session.get('topic','Untitled')}\"",
            f"user: \"{user.get('name', user_id)}\"",
            f"session_id: \"{session_id}\"",
            f"messages: {len(messages)}",
            f"duration_min: {duration_min}",
            "tags: [proyecto/krk9, conversation]",
            "---",
            "",
            f"# KRK-9 — {today} · Sesión: {session.get('topic','Untitled')}",
            "",
            "## 📊 Resumen",
            f"- Participantes: {', '.join(set(m.get('author','?') for m in messages)) or '?'}",
            f"- Palabras aprendidas por Casete: {', '.join(vocab[:10]) or '(ninguna)'}",
            f"- Mensajes totales: {len(messages)}",
            "",
            "## 💬 Transcripción",
        ]
        for m in messages[:200]:  # cap a 200 msgs para no inflar el .md
            author = m.get("author", m.get("agent", "?"))
            content = m.get("content", "").replace("\n", " ")
            ts = m.get("ts", m.get("timestamp", ""))
            time_short = ts[11:16] if len(ts) > 16 else ""
            md_lines.append(f"**{author}** ({time_short}): {content}")
        
        if len(messages) > 200:
            md_lines.append(f"\n... ({len(messages) - 200} mensajes más)")
        
        md_lines.extend([
            "",
            "## 🔗 Enlaces",
            "- [[_KRK9-MOC|Índice KRK-9]]",
            "- [[2026-07-20-krk9-personality-editor-gui|Sesión previa]]",
            "",
        ])
        markdown = "\n".join(md_lines)
        
        # Escribir a Obsidian
        obsidian_dir = Path.home() / "Documents" / "Obsidian-Vault" / "Discord-Bot" / "Sessions"
        fallback_dir = Path(__file__).parent / "SESSIONS"
        if obsidian_dir.exists() or obsidian_dir.parent.exists():
            target_dir = obsidian_dir
        else:
            target_dir = fallback_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{today}-krk9-session-{session_id}.md"
        target_path = target_dir / filename
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return web.json_response({
            "status": "ok",
            "path": str(target_path),
            "is_obsidian": str(target_dir) == str(obsidian_dir),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def topics_list_handler(request):
    """GET /api/topics?user_id=... — TOPICS base + sugerencias cacheadas del user."""
    user_id = request.query.get("user_id", "")
    from state_manager import load_state
    state = load_state()
    from bot import TOPICS
    suggestions = []
    if user_id:
        suggestions = state.get("users", {}).get(user_id, {}).get("last_topic_suggestions", {}).get("topics", [])
    return web.json_response({
        "topics_base": TOPICS,
        "suggestions": suggestions,
    })

async def topic_set_handler(request):
    """POST /api/topic {user_id, topic} — fija tema custom."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        topic = body.get("topic", "")
        if not user_id or not topic:
            return web.json_response({"error": "user_id and topic required"}, status=400)
        from state_manager import load_state, save_state
        state = load_state()
        state["custom_topic"] = {"theme": topic, "hook": f"Let's talk about {topic}!"}
        save_state(state)
        return web.json_response({"status": "ok", "topic": topic})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def preferences_handler(request):
    """GET /api/preferences?user_id=... | POST {user_id, interests: [...]}"""
    from state_manager import load_state, save_state
    if request.method == "GET":
        user_id = request.query.get("user_id", "")
        if not user_id:
            return web.json_response({"error": "user_id required"}, status=400)
        state = load_state()
        interests = state.get("users", {}).get(user_id, {}).get("interests", [])
        return web.json_response({"user_id": user_id, "interests": interests})
    else:  # POST
        try:
            body = await request.json()
            user_id = body.get("user_id", "")
            interests = body.get("interests", [])
            if not user_id or not isinstance(interests, list):
                return web.json_response({"error": "user_id and interests list required"}, status=400)
            state = load_state()
            state.setdefault("users", {}).setdefault(user_id, {"name":"Unknown","interests":[],"casete_vocab":{},"sessions":[],"active_session":None})
            state["users"][user_id]["interests"] = [str(i).lower().strip() for i in interests if i]
            # Invalidar cache de sugerencias
            if "last_topic_suggestions" in state["users"][user_id]:
                del state["users"][user_id]["last_topic_suggestions"]
            save_state(state)
            return web.json_response({"status": "ok", "interests": state["users"][user_id]["interests"]})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

async def active_agents_get_handler(request):
    from state_manager import load_state
    state = load_state()
    active = state.get("active_agents", ["Alex", "Maya", "Jordan", "Sam", "Casete"])
    return web.json_response({"active_agents": active})


async def active_agents_post_handler(request):
    from state_manager import load_state, save_state
    try:
        body = await request.json()
        active = body.get("active_agents")
        if not isinstance(active, list):
            return web.json_response({"error": "active_agents must be a list"}, status=400)
        state = load_state()
        state["active_agents"] = [a for a in active if a in ["Alex", "Maya", "Jordan", "Sam", "Casete"]]
        save_state(state)
        return web.json_response({"status": "ok", "active_agents": state["active_agents"]})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ─── News Room API Handlers ─────────────────────────────────────────────────
async def news_briefing_handler(request):
    """GET /api/news/briefing?user_id=<uid> — último briefing (o genera si no hay de hoy)."""
    from datetime import datetime
    from state_manager import load_state
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    history = state.get("users", {}).get(uid, {}).get("news_history", [])
    today = datetime.now().strftime("%Y-%m-%d")
    if history and history[0]["date"].startswith(today):
        return web.json_response({"briefing": history[0]["markdown"], "cached": True})
    return web.json_response({"briefing": None, "cached": False, "message": "No hay briefing de hoy. Usa POST /api/news/refresh."})

async def news_refresh_handler(request):
    """POST /api/news/refresh {user_id} — genera briefing ahora."""
    try:
        body = await request.json()
        uid = body.get("user_id", "legacy_vaclav")
        from news_room import generate_briefing
        md = await generate_briefing(uid)
        return web.json_response({"status": "ok", "briefing": md})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ─── Assistant API Handlers ─────────────────────────────────────────────────
async def assistant_chat_handler(request):
    """POST /api/assistant/chat {user_id, message}"""
    try:
        body = await request.json()
        uid = body.get("user_id", "legacy_vaclav")
        message = (body.get("message") or "").strip()
        if not message:
            return web.json_response({"error": "message required"}, status=400)
        from krk9_assistant import assistant_reply
        reply = await assistant_reply(uid, message)
        return web.json_response({"reply": reply})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ─── Entry/Page Routes Handlers ─────────────────────────────────────────────
async def rooms_get_handler(request):
    """GET /api/rooms?user_id=<uid> — lista salas del usuario."""
    from state_manager import load_state, get_user_rooms
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    rooms = get_user_rooms(state, uid)
    return web.json_response({"user_id": uid, "rooms": rooms})

# ─── Server Setup ──────────────────────────────────────────────────────────
async def start_audio_server():
    """Start the aiohttp server."""
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        'http://localhost:8081': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
            allow_methods='*',
        ),
        'http://127.0.0.1:8081': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
            allow_methods='*',
        ),
    })
    
    # Serve static files (logo, custom CSS, etc.)
    app.router.add_static('/static/', path='./static', name='static', show_index=True)
    
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', index_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_get('/chat', chat_handler)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Add POST routes with CORS — existing
    audio_route = app.router.add_post('/api/audio', broadcast_audio_http)
    voice_route = app.router.add_post('/api/voice', voice_text_handler)
    invite_route = app.router.add_get('/api/invite', invite_handler)
    cors.add(audio_route)
    cors.add(voice_route)
    cors.add(invite_route)

    # Add NEW routes — Personas API
    personas_get_route = app.router.add_get('/api/personas', personas_get_handler)
    personas_post_route = app.router.add_post('/api/personas', personas_post_handler)
    tts_preview_route = app.router.add_post('/api/tts-preview', tts_preview_handler)
    session_export_route = app.router.add_post('/api/session-export', session_export_handler)
    cors.add(personas_get_route)
    cors.add(personas_post_route)
    cors.add(tts_preview_route)
    cors.add(session_export_route)
    
    # NEW ROUTES F10:
    s_list_route = app.router.add_get('/api/sessions', sessions_list_handler)
    s_create_route = app.router.add_post('/api/sessions', sessions_create_handler)
    s_res_route = app.router.add_post('/api/sessions/resume', sessions_resume_handler)
    s_save_route = app.router.add_post('/api/session/save-obsidian', session_save_obsidian_handler)
    t_list_route = app.router.add_get('/api/topics', topics_list_handler)
    t_set_route = app.router.add_post('/api/topic', topic_set_handler)
    p_get_route = app.router.add_get('/api/preferences', preferences_handler)
    p_post_route = app.router.add_post('/api/preferences', preferences_handler)
    a_get_route = app.router.add_get('/api/active-agents', active_agents_get_handler)
    a_post_route = app.router.add_post('/api/active-agents', active_agents_post_handler)
    
    cors.add(s_list_route)
    cors.add(s_create_route)
    cors.add(s_res_route)
    cors.add(s_save_route)
    cors.add(t_list_route)
    cors.add(t_set_route)
    cors.add(p_get_route)
    cors.add(p_post_route)
    cors.add(a_get_route)
    cors.add(a_post_route)

    # ─── News Room API ────────────────────────────────────────────────
    news_briefing_route = app.router.add_get('/api/news/briefing', news_briefing_handler)
    news_refresh_route = app.router.add_post('/api/news/refresh', news_refresh_handler)
    cors.add(news_briefing_route)
    cors.add(news_refresh_route)

    # ─── News Room GUI ────────────────────────
    from news_gui_routes import (
        news_gui_handler, news_config_get_handler, news_config_post_handler,
        news_config_validate_handler, news_config_reset_handler,
        news_test_fetch_handler,
    )
    gui_route = app.router.add_get('/news-config', news_gui_handler)
    config_get_route = app.router.add_get('/api/news/config', news_config_get_handler)
    config_post_route = app.router.add_post('/api/news/config', news_config_post_handler)
    config_validate_route = app.router.add_post('/api/news/config-validate', news_config_validate_handler)
    config_reset_route = app.router.add_post('/api/news/config-reset', news_config_reset_handler)
    test_fetch_route = app.router.add_post('/api/news/test-fetch', news_test_fetch_handler)
    cors.add(gui_route)
    cors.add(config_get_route)
    cors.add(config_post_route)
    cors.add(config_validate_route)
    cors.add(config_reset_route)
    cors.add(test_fetch_route)

    # ─── Assistant API ────────────────────────────────────────────────
    assistant_chat_route = app.router.add_post('/api/assistant/chat', assistant_chat_handler)
    cors.add(assistant_chat_route)

    # ─── Entry/Page Routes (nuevas páginas) ──────────────────────────
    assistant_route = app.router.add_get('/assistant', lambda r: web.FileResponse("./assistant_page.html"))
    news_route = app.router.add_get('/news', lambda r: web.FileResponse("./news_page.html"))
    rooms_route = app.router.add_get('/api/rooms', rooms_get_handler)
    cors.add(assistant_route)
    cors.add(news_route)
    cors.add(rooms_route)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()
    print("🎵 Audio server running at http://localhost:8081")
    print("   WebSocket: ws://localhost:8081/ws")
    print("   HTTP API:  http://localhost:8081/api/audio")
    print("   Voice API: http://localhost:8081/api/voice")
    print("   Personas:  http://localhost:8081/api/personas")
    print("   TTS Prev:  http://localhost:8081/api/tts-preview")
    return runner
# For direct import by bot.py
audio_server_runner = None

async def init_audio_server():
    """Called by bot.py - server runs externally, just verify it's up."""
    # Audio server runs as separate process; we just log that it's expected to be running
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8081/health', timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    logger.info("🔊 Audio server confirmed running at http://localhost:8081")
                else:
                    logger.warning("⚠️ Audio server responded but not healthy")
    except Exception as e:
        logger.warning(f"⚠️ Audio server not reachable at localhost:8081: {e}")
        logger.info("   Start it with: python audio_server.py")

async def send_audio_to_browsers(audio_bytes: bytes, agent_name: str):
    await broadcast_audio(audio_bytes, agent_name)


if __name__ == "__main__":
    async def main():
        runner = await start_audio_server()
        try:
            await asyncio.Event().wait()  # run forever
        finally:
            await runner.cleanup()
    
    asyncio.run(main())