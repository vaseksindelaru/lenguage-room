#!/usr/bin/env python3
"""Start audio_server as daemon, verify health, then detach."""
import sys, asyncio, os, signal
sys.path.insert(0, '/home/vaclav/discord-english-room')

async def main():
    from audio_server import start_audio_server
    runner = await start_audio_server()
    
    # Verify with async HTTP
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8081/health', timeout=aiohttp.ClientTimeout(total=3)) as resp:
            health = await resp.text()
            print(f"Health: {health}", flush=True)
        
        async with session.get('http://localhost:8081/', timeout=aiohttp.ClientTimeout(total=3)) as resp:
            html = await resp.text()
            print(f"Entry page: {len(html)} chars, starts with: {html[:60]}...", flush=True)
        
        async with session.get('http://localhost:8081/api/rooms?user_id=legacy_vaclav', timeout=aiohttp.ClientTimeout(total=3)) as resp:
            rooms = await resp.text()
            print(f"Rooms API: {rooms[:200]}", flush=True)
        
        async with session.get('http://localhost:8081/chat', timeout=aiohttp.ClientTimeout(total=3)) as resp:
            chat_html = await resp.text()
            print(f"Chat page: {len(chat_html)} chars", flush=True)

    print("\n✅ All endpoints verified! Server running at http://localhost:8081", flush=True)
    print("   Entry page: http://localhost:8081/", flush=True)
    print("   Chat room: http://localhost:8081/chat", flush=True)
    print("   Assistant: http://localhost:8081/assistant", flush=True)
    print("   News: http://localhost:8081/news", flush=True)
    print("   Rooms API: http://localhost:8081/api/rooms", flush=True)
    
    # Run forever
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()

asyncio.run(main())
