"""
Audio WebSocket Server — streams TTS audio to browser for auto-playback
Run: python audio_server.py
Opens: http://localhost:8080
"""
import asyncio
import json
import base64
import logging
from aiohttp import web
import os
import aiohttp
from aiohttp import web
import aiohttp_cors

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


async def start_audio_server():
    """Start the aiohttp server."""
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "http://localhost:8081": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        ),
        "http://127.0.0.1:8081": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        ),
    }
    
    # Serve static files (logo, custom CSS, etc.)
    app.router.add_static('/static/', path='./static', name='static', show_index=True)
    
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', index_handler)
    app.router.add_get('/health', health_handler)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Add POST routes with CORS
    audio_route = app.router.add_post('/api/audio', broadcast_audio_http)
    voice_route = app.router.add_post('/api/voice', voice_text_handler)
    invite_route = app.router.add_get('/api/invite', invite_handler)
    cors.add(audio_route)
    cors.add(voice_route)
    cors.add(invite_route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()
    print("🎵 Audio server running at http://localhost:8081")
    print("   WebSocket: ws://localhost:8081/ws")
    print("   HTTP API:  http://localhost:8081/api/audio")
    print("   Voice API: http://localhost:8081/api/voice")
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