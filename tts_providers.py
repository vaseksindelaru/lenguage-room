"""
TTS providers for KRK-9.
Soporta dos providers:
  - edge   : edge_tts (Microsoft, gratis, sin API key, voces humanas)
  - elevenlabs : ElevenLabs API REST (requiere ELEVENLABS_API_KEY)

Diseño:
  - generate_tts(voice) acepta str (Edge) o dict (ElevenLabs)
  - Si ElevenLabs falla (no key, timeout, error API), fallback automático a Edge
  - Sin estado global; las funciones son async puras
"""
import os
import re
import logging
from typing import Optional, Union
import httpx
import edge_tts

logger = logging.getLogger("tts")

# Voces Edge válidas (catálogo estático, verificar disponibilidad si hay errores)
EDGE_VOICES = [
    "en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural",
    "en-US-DavisNeural", "en-US-JaneNeural",
    "en-GB-RyanNeural", "en-GB-SoniaNeural",
    "en-US-AndrewNeural", "en-US-TonyNeural",   # ← fallback Casete (nasales/distintas)
    "en-US-ChristopherNeural", "en-US-LibbyNeural",
    "es-ES-AlvaroNeural", "es-ES-ElviraNeural",  # para otros usos futuros
]

# Emojis que el TTS no sabe pronunciar — los eliminamos antes de sintetizar
_EMOJI_PATTERN = re.compile(r'[🟦🟩🟧🟪🦜🔊🎤🎧🤖👻🎭🦊🐱🐺🦁🐯🦄🌟🔥💡🎯🚀🎪🎨🎼🎷🎸🎺📚🟦🟩🟧🟪]+')

def _clean_text(text: str) -> str:
    cleaned = _EMOJI_PATTERN.sub('', text).strip()
    return cleaned

async def generate_tts(text: str, voice) -> Optional[bytes]:
    """Dispatch según el tipo de voice.
    
    Args:
        text: texto a sintetizar (puede tener emojis — se limpian)
        voice: str (Edge voice name) o dict {"provider":"elevenlabs","voice_id":"...","model":"...","fallback":"..."}
    
    Returns:
        bytes audio/mpeg, o None si ambos providers fallan
    """
    cleaned = _clean_text(text)
    if not cleaned:
        return None
    
    if isinstance(voice, dict) and voice.get("provider") == "elevenlabs":
        return await _generate_tts_elevenlabs(cleaned, voice)
    return await _generate_tts_edge(cleaned, voice)

async def _generate_tts_edge(text: str, voice: str) -> Optional[bytes]:
    """Edge TTS (código actual, sin cambios funcionales)."""
    if voice not in EDGE_VOICES:
        logger.warning(f"⚠️ Edge voice '{voice}' no está en el catálogo, intento igualmente")
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        if not audio_data:
            logger.error(f"❌ Edge TTS sin audio para voz {voice}")
            return None
        return audio_data
    except Exception as e:
        logger.error(f"❌ Edge TTS error (voice={voice}): {e}")
        return None

async def _generate_tts_elevenlabs(text: str, voice_config: dict) -> Optional[bytes]:
    """ElevenLabs TTS via REST API. Fallback automático a Edge si falla."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    fallback_voice = voice_config.get("fallback", "en-US-AndrewNeural")
    
    # Detectar placeholder o key inválida
    if not api_key or api_key.startswith("your_") or len(api_key) < 20:
        logger.warning("⚠️ ELEVENLABS_API_KEY not set or placeholder → Edge fallback")
        return await _generate_tts_edge(text, fallback_voice)
    
    voice_id = voice_config.get("voice_id", "")
    if not voice_id or voice_id == "placeholder_set_in_env_or_default_fallback":
        logger.warning(f"⚠️ ElevenLabs voice_id es placeholder ('{voice_id}') → Edge fallback")
        return await _generate_tts_edge(text, fallback_voice)
    
    model = voice_config.get("model", "eleven_flash_v2_5")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": model,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                },
            )
            resp.raise_for_status()
            if not resp.content:
                logger.error("❌ ElevenLabs devolvió respuesta vacía → Edge fallback")
                return await _generate_tts_edge(text, fallback_voice)
            logger.info(f"🦜 ElevenLabs TTS ok ({len(resp.content)} bytes, voice={voice_id})")
            return resp.content
    except httpx.TimeoutException:
        logger.warning(f"⚠️ ElevenLabs timeout → Edge fallback")
        return await _generate_tts_edge(text, fallback_voice)
    except httpx.HTTPStatusError as e:
        logger.warning(f"⚠️ ElevenLabs HTTP {e.response.status_code} → Edge fallback")
        return await _generate_tts_edge(text, fallback_voice)
    except Exception as e:
        logger.warning(f"⚠️ ElevenLabs error ({type(e).__name__}: {e}) → Edge fallback")
        return await _generate_tts_edge(text, fallback_voice)
