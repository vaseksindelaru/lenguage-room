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
    """Serve the HTML player page."""
    return web.FileResponse('./audio_player.html')


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
        return web.json_response({
            "agents": personas.get("agents", {}),
            "defaults": defaults.get("agents", {}),
            "llm_providers": providers,
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
        voice = body.get("voice", "en-US-GuyNeural").strip()

        if not text:
            return web.json_response({"error": "No text provided"}, status=400)

        # Import edge_tts (same lib used by bot.py)
        import edge_tts

        # Clean text for TTS
        clean_text = re.sub(r'[🟦🟩🟧🟪]', '', text).strip()
        if not clean_text:
            return web.json_response({"error": "Text is empty after cleaning"}, status=400)

        communicate = edge_tts.Communicate(clean_text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

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