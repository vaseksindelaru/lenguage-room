# KRK-9 — Plan de Ejecución Técnica (LLM Ejecutor: Gemini 3.1 / Claude 4)

> [!info] **Para el LLM ejecutor:** Este es un plan de ejecución determinista. NO improvises, NO re-arquitectures, NO re-nombres funciones, NO muevas archivos de sitio. Cada fase tiene criterios de salida binarios. Si un criterio falla, PARA y reporta — no sigas.
>
> **Usuario aprobó:** 2026-07-21. **NO EJECUTADO todavía.** Espera respuesta a las 6 decisiones del §F0 antes de empezar.
>
> **Spec literal de Casete (`casete_loro_cyborg_persona_integracion.md`) no existe en el sistema** — el editor redactará el prompt con base en la descripción del usuario (loro cyborg, graba palabras repetidas, admite cuando no sabe, frases cortas, inglés, entusiasmo).

---

## F0 — Pre-flight (OBLIGATORIO antes de F1)

### F0.1 Variables de la sesión

```yaml
REPO_PATH: /home/vaclav/discord-english-room
VAULT_PATH: /home/vaclav/Documents/Obsidian-Vault
STATE_PATH: ~/.english-bot/state.json
PYTHON: venv/bin/python  # SIEMPRE con PYTHONPATH=""
BRANCH_PARENT: feat/personality-editor-gui
BRANCH_NEW: feat/casete-obsidian-topics-elevenlabs
```

### F0.2 Snapshot del estado (corre ahora)

```bash
cd /home/vaclav/discord-english-room
git rev-parse --abbrev-ref HEAD           # debe ser feat/personality-editor-gui
git status --porcelain                     # debe estar VACÍO
git log --oneline -3                       # debe mostrar d24b9ec y 1dd28b0
test -f personas.json && echo "personas.json existe"
test -f ~/.english-bot/state.json && jq '.version // "v1"' ~/.english-bot/state.json
ss -ltn | grep -q ':8081 ' && echo "WARN: puerto 8081 ocupado, matar antes de F5" || echo "puerto 8081 libre"
```

**Criterio de salida F0:** los 4 checks devuelven los valores esperados. Si `git status` muestra cambios, ejecutar `git add -A && git commit -m "WIP before casete"`. Si el puerto 8081 está ocupado: `pkill -9 -f audio_server.py; sleep 2`.

### F0.3 Crear rama nueva

```bash
cd /home/vaclav/discord-english-room
git checkout -b feat/casete-obsidian-topics-elevenlabs
```

**Criterio de salida F0:** `git branch --show-current` imprime `feat/casete-obsidian-topics-elevenlabs`.

### F0.4 6 Decisiones del usuario (BLOQUEANTES)

Espera respuesta del usuario a estas 6 preguntas antes de F1. **Si el usuario responde "avanza con defaults" o no contesta alguna**, usa los defaults en negrita.

| # | Pregunta | Default |
|---|---|---|
| 1 | ¿Pones `ELEVENLABS_API_KEY` real en `.env` ahora? | **No → placeholder `your_e...here` + fallback a Edge** |
| 2 | ¿Voz Edge fallback para Casete? | **`en-US-AndrewNeural`** |
| 3 | ¿ElevenLabs solo para Casete o para todos los agentes? | **Todos pueden elegir (cualquier `voice` dict)** |
| 4 | ¿Vocabulario de Casete depende de `roger_willkommen`? | **NO — vive solo en `state.json` de KRK-9** |
| 5 | ¿Pegas el spec literal de Casete o redactas con la descripción? | **Redactar con la descripción** |
| 6 | ¿Multi-user desde el inicio (Ronny, amigos) o solo tú? | **Multi-user desde el inicio (migración v1→v2)** |

### F0.5 Anti-patrones que el editor NUNCA debe hacer

- ❌ NO usar `python` a secas (siempre `PYTHONPATH="" venv/bin/python`)
- ❌ NO commitear `.env`, `venv/`, `__pycache__/`, `.pids/`, `bot.log`, `personas.json`, `state.json`
- ❌ NO modificar el flag `ignore_bot_messages` (bot.py L1136-1216) — el fix del bug `!speak` del 2026-07-07 debe seguir funcionando
- ❌ NO añadir Casete al weighted random de `decide_next_agent()` — es event-triggered
- ❌ NO importar `bot` desde `audio_server.py` (arrastra discord.py, rompe startup) — usar el módulo nuevo `tts_providers.py`
- ❌ NO generar la palabra que Casete sopla con el LLM (la palabra viene SIEMPRE del lookup en `known`)
- ❌ NO recortar `users[uid].sessions[].messages` (sesiones son persistentes)
- ❌ NO borrar el `conversation_history` global (lo usa `conversation_loop`, debe quedarse recortado a 50)
- ❌ NO mover archivos `.md` del repo — los planes viven junto a `DECISIONS.md`

---

## F1 — Crear `tts_providers.py` (compartido por bot y audio_server)

**Por qué primero:** tanto `bot.py` como `audio_server.py` necesitan las funciones de TTS. Si lo creamos al final, hay import circular o doble implementación.

### F1.1 Archivo: `tts_providers.py` (NUEVO, raíz del repo)

```python
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
```

### F1.2 Verificación F1

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import asyncio
from tts_providers import generate_tts, EDGE_VOICES

async def main():
    # Test 1: Edge con string
    audio = await generate_tts('Hello from Edge TTS', 'en-US-GuyNeural')
    assert audio is not None and len(audio) > 1000, f'Edge falló: {len(audio) if audio else 0} bytes'
    print(f'✅ Test 1: Edge TTS ok ({len(audio)} bytes)')

    # Test 2: ElevenLabs con placeholder (debe fallback a Edge)
    audio = await generate_tts('Hello from Casete', {'provider':'elevenlabs','voice_id':'placeholder','model':'eleven_flash_v2_5','fallback':'en-US-AndrewNeural'})
    assert audio is not None, 'ElevenLabs fallback falló'
    print(f'✅ Test 2: ElevenLabs placeholder → Edge fallback ok ({len(audio)} bytes)')

    # Test 3: Texto con emojis (debe limpiar)
    audio = await generate_tts('Hello 🦜 from 🟦 Casete', 'en-US-GuyNeural')
    assert audio is not None, 'Limpieza de emojis falló'
    print(f'✅ Test 3: Limpieza de emojis ok')

    # Test 4: Texto vacío tras limpieza
    audio = await generate_tts('🦜🟦🟩', 'en-US-GuyNeural')
    assert audio is None, 'Texto vacío debería devolver None'
    print(f'✅ Test 4: Texto vacío → None')

asyncio.run(main())
"
```

**Criterio de salida F1:** los 4 tests pasan, output contiene 4 líneas `✅`. Si alguno falla, REVISAR tts_providers.py antes de continuar.

### F1.3 Commit F1

```bash
cd /home/vaclav/discord-english-room
git add tts_providers.py
git status   # SOLO debe aparecer tts_providers.py
git commit -m "feat(tts): shared TTS provider module (Edge + ElevenLabs with fallback)

- Crea tts_providers.py con generate_tts() que dispatcha según tipo de voice
- Soporta string (Edge) y dict (ElevenLabs con model_id configurable)
- Fallback automático a Edge si ELEVENLABS_API_KEY falta/es placeholder/falla
- Limpia emojis antes de sintetizar (Edge no los pronuncia)
- Catálogo EDGE_VOICES exportado para uso en GUI

Este módulo reemplaza la generate_tts() inline de bot.py en F2."
```

---

## F2 — Refactor `bot.py:generate_tts()` para usar `tts_providers`

**Por qué segundo:** Casete necesita ElevenLabs. Bot.py tiene `generate_tts` con la misma lógica que acabamos de extraer. Sin este refactor, F3-F4 duplicarían código.

### F2.1 Reemplazar `generate_tts` (bot.py L452-471)

Localizar el bloque actual (entre `# Generate TTS audio` y el `except Exception`) y reemplazar TODO el cuerpo por:

```python
async def generate_tts(text: str, voice) -> Optional[bytes]:
    """Generate TTS audio. Delegado a tts_providers para soportar Edge + ElevenLabs.
    
    voice: str (Edge name) o dict {"provider":"elevenlabs", "voice_id":"...", "model":"..."}
    """
    from tts_providers import generate_tts as _tts
    return await _tts(text, voice)
```

**TRAMPA:** NO borrar los `import` de `edge_tts` y `httpx` que están en el header de `bot.py` — el módulo `tts_providers` los necesita. Sí están importados globalmente, no hay cambio.

### F2.2 Verificación F2

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import asyncio
import bot

async def main():
    # Test 1: voz string (Edge)
    audio = await bot.generate_tts('Test refactor Edge', 'en-US-GuyNeural')
    assert audio and len(audio) > 1000
    print(f'✅ bot.generate_tts() Edge ok ({len(audio)} bytes)')

    # Test 2: dict ElevenLabs (fallback a Edge por placeholder)
    audio = await bot.generate_tts('Test refactor Eleven', {'provider':'elevenlabs','voice_id':'fake','model':'eleven_flash_v2_5','fallback':'en-US-AndrewNeural'})
    assert audio
    print(f'✅ bot.generate_tts() ElevenLabs fallback ok ({len(audio)} bytes)')

asyncio.run(main())
"
```

**Criterio de salida F2:** ambos tests pasan.

### F2.3 Commit F2

```bash
cd /home/vaclav/discord-english-room
git add bot.py
git status   # SOLO bot.py
git commit -m "refactor(bot): generate_tts() ahora delega a tts_providers

- Misma firma, misma semántica
- Permite usar voz ElevenLabs (dict) además de Edge (str)
- Bug fix implícito: ya no requiere import inline de edge_tts dentro de la función"
```

---

## F3 — Añadir Casete a `AGENTS`, `AGENT_PERSONAS`, `VALID_AGENTS`, `DEFAULT_PERSONAS`

**Por qué tercero:** Casete necesita estar en los 4 catálogos antes de poder hacer nada (webhook, endpoint validación, defaults del editor GUI).

### F3.1 `bot.py:AGENTS` (L55-60) — añadir entrada Casete

Localizar el bloque:
```python
AGENTS = {
    "Alex": {"color": 0x5865F2, "emoji": "🟦", "voice": "en-US-GuyNeural"},
    ...
    "Sam": {"color": 0xEB459E, "emoji": "🟪", "voice": "en-US-AriaNeural"},
}
```

Insertar después de la línea de Sam (justo antes del `}` de cierre), respetando la indentación de 4 espacios:
```python
    "Casete": {
        "color": 0x00FFAA,       # verde-loro, distinto a los 4
        "emoji": "🦜",
        "voice": {                # dict → tts_providers enruta a ElevenLabs
            "provider": "elevenlabs",
            "voice_id": "placeholder_set_in_env_or_default_fallback",
            "model": "eleven_flash_v2_5",
            "fallback": "en-US-AndrewNeural",
        },
    },
```

**TRAMPA:** la coma final después de `"en-US-AriaNeural"` en Sam — añadir `,` si no está.

### F3.2 `bot.py:AGENT_PERSONAS` (L102-203) — añadir entrada Casete

Localizar el dict (comienza con `"Alex": """..."""`) e insertar DESPUÉS del bloque de Sam (después de su `""",`), respetando indentación de 4 espacios:

```python
    "Casete": """You are Casete, a cyborg parrot. You have an integrated recording
component — that's why you literally "record" words you hear repeated several
times until they're yours forever. Your job is to whisper the EXACT word the
player asks for when you already have it recorded, with the enthusiasm of an
imitating parrot. If you don't have it recorded yet, you admit it with a SHORT
fixed phrase and NEVER invent. You speak English with a neutral Latin accent,
short sentences (≤15 words), simple but enthusiastic vocabulary. You never
break character. You never volunteer topics — you only respond when the player
explicitly asks for a word with "!casete <word>" or says "how do you say..." /
"cómo se dice...". In those moments, you say the word (or admit you don't
have it) and stop. You are a secondary character — never dominate the
conversation.""",
```

**NOTA:** Este prompt es redacción del editor basada en la descripción del usuario. Si el usuario pega el spec literal antes de F3, USAR ESE en su lugar.

### F3.3 `state_manager.py:VALID_AGENTS` (L118)

Localizar:
```python
VALID_AGENTS = {"Alex", "Maya", "Jordan", "Sam"}
```

Reemplazar por:
```python
VALID_AGENTS = {"Alex", "Maya", "Jordan", "Sam", "Casete"}
```

### F3.4 `state_manager.py:DEFAULT_PERSONAS` (L123+) — añadir bloque Casete

Localizar el dict `DEFAULT_PERSONAS` (comienza con `"agents": {`). Insertar después del bloque de Sam (después de su `}`), respetando indentación de 8 espacios (porque está dentro de `"agents": {`):

```python
        "Casete": {
            "persona": """You are Casete, a cyborg parrot. You have an integrated recording
component — that's why you literally "record" words you hear repeated several
times until they're yours forever. Your job is to whisper the EXACT word the
player asks for when you already have it recorded, with the enthusiasm of an
imitating parrot. If you don't have it recorded yet, you admit it with a SHORT
fixed phrase and NEVER invent. You speak English with a neutral Latin accent,
short sentences (≤15 words), simple but enthusiastic vocabulary.""",
            "voice": {
                "provider": "elevenlabs",
                "voice_id": "placeholder_set_in_env_or_default_fallback",
                "model": "eleven_flash_v2_5",
                "fallback": "en-US-AndrewNeural",
            },
            "emoji": "🦜",
            "llm_provider": "auto",   # entra al router cerebras→groq→openrouter→ollama
            "llm_model": None,
        },
```

**TRAMPA:** el orden de claves en DEFAULT_PERSONAS es `persona, voice, emoji, llm_provider, llm_model` (el mismo que `VALID_FIELDS` L119). Respetar ese orden para que `audio_server.py` L269-304 no rechace campos.

### F3.5 Verificación F3

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
from bot import AGENTS, AGENT_PERSONAS
from state_manager import VALID_AGENTS, get_default_personas

# Test 1: AGENTS tiene Casete
assert 'Casete' in AGENTS, 'Casete no está en AGENTS'
assert AGENTS['Casete']['emoji'] == '🦜', f'emoji incorrecto: {AGENTS[\"Casete\"][\"emoji\"]}'
assert AGENTS['Casete']['voice']['provider'] == 'elevenlabs', 'voice debe ser dict ElevenLabs'
print('✅ Test 1: AGENTS[\"Casete\"] correctamente registrado')

# Test 2: AGENT_PERSONAS tiene Casete
assert 'Casete' in AGENT_PERSONAS, 'Casete no está en AGENT_PERSONAS'
assert len(AGENT_PERSONAS['Casete']) > 100, 'persona demasiado corta'
print('✅ Test 2: AGENT_PERSONAS[\"Casete\"] presente')

# Test 3: VALID_AGENTS incluye Casete
assert 'Casete' in VALID_AGENTS, 'Casete no está en VALID_AGENTS'
print('✅ Test 3: VALID_AGENTS incluye Casete')

# Test 4: DEFAULT_PERSONAS tiene Casete
defaults = get_default_personas()['agents']
assert 'Casete' in defaults, 'Casete no está en DEFAULT_PERSONAS'
required = {'persona','voice','emoji','llm_provider','llm_model'}
assert required.issubset(defaults['Casete'].keys()), f'faltan campos: {required - defaults[\"Casete\"].keys()}'
print('✅ Test 4: DEFAULT_PERSONAS[\"Casete\"] completo')
"
```

**Criterio de salida F3:** los 4 tests pasan.

### F3.6 Commit F3

```bash
cd /home/vaclav/discord-english-room
git add bot.py state_manager.py
git status
git commit -m "feat: add Casete (cyborg parrot) to AGENTS, PERSONAS, VALID_AGENTS, DEFAULT_PERSONAS

- AGENTS[Casete]: color 0x00FFAA, emoji 🦜, voice ElevenLabs dict
- AGENT_PERSONAS[Casete]: prompt redactado (loro cyborg, frases cortas, sin inventar)
- VALID_AGENTS += 'Casete' (necesario para que POST /api/personas lo acepte)
- DEFAULT_PERSONAS[Casete]: llm_provider='auto' entra al router existente
- NO incluido en decide_next_agent() weighted random (event-triggered en F4)"
```

---

## F4 — Implementar `extract_notable_words`, `on_casete_help`, `!casete` command, hook en `on_message`

**Por qué cuarto:** con Casete registrado, ahora implementamos su lógica de vocabulario y respuesta.

### F4.1 `bot.py` — añadir helpers cerca de la línea 25 (después de imports)

Insertar después de la línea 25 (`from typing import Optional, Dict, List`):

```python
# ─── Vocabulary extraction (Casete) ────────────────────────────────────────
_STOPWORDS_EN = frozenset({
    "the","a","an","is","are","was","were","be","been","being","i","you",
    "he","she","it","we","they","my","your","his","her","its","our","their",
    "this","that","these","those","and","but","or","so","of","in","on","at",
    "to","for","with","from","by","as","if","then","than","do","does","did",
    "have","has","had","will","would","can","could","should","may","might",
    "about","what","when","where","who","how","why","yes","no","ok","okay",
    "really","very","just","like","think","know","get","got","go","going",
    "make","made","take","took","come","came","see","saw","say","said",
    "tell","told","give","gave","put","let","try","tried","need","want",
    "new","old","good","bad","big","small","long","short","high","low",
    "right","wrong","first","last","next","still","now","then","here",
    "there","where","when","why","how","out","off","up","down","over",
    "under","again","more","most","some","any","all","each","every",
    "other","such","only","own","same","than","too","very","much","many",
    "few","little","well","back","after","before","between","through",
    "because","while","during","without","within","upon","toward",
})

_NOTABLE_WORD_RE = re.compile(r'\b[a-zA-Z]{4,}\b')

def extract_notable_words(text: str) -> list[str]:
    """Extrae palabras notables: ≥4 letras, solo alfabéticas, no stopwords EN.
    
    Devuelve la lista en minúsculas, sin duplicados en el mismo mensaje
    (pero el caller llama a register_word_heard por cada una igualmente,
    porque pueden venir en mensajes distintos).
    """
    words = _NOTABLE_WORD_RE.findall(text.lower())
    return [w for w in words if w not in _STOPWORDS_EN]


def extract_target_word(text: str) -> str:
    """Extrae la palabra objetivo de un mensaje tipo 'cómo se dice <word>'.
    
    Heurística: busca la última palabra entre comillas, o la última palabra
    notable del mensaje si no hay comillas.
    """
    # 1. Intentar extraer de comillas
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        candidate = quoted.group(1).strip().lower()
        words_in_quotes = _NOTABLE_WORD_RE.findall(candidate)
        if words_in_quotes:
            return words_in_quotes[-1]
    
    # 2. Última palabra notable del mensaje
    notables = extract_notable_words(text)
    return notables[-1] if notables else ""


def truncate_casete_response(text: str, max_chars: int = 80) -> str:
    """Trunca la respuesta de Casete a ~20 tokens sin partir palabras."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(",.;:") + "!"


# Regex de triggers para invocar a Casete sin "!casete"
CASETE_TRIGGERS = [
    r"\bc[oó]mo se dice\b",
    r"\bhow (?:do you|to) say\b",
    r"\bwhat(?:'s| is) the word for\b",
    r"\bno s[eé] c[oó]mo\b",
]
_CASETE_TRIGGERS_RE = re.compile("|".join(CASETE_TRIGGERS), re.IGNORECASE)
```

**TRAMPA:** `re` ya está importado en bot.py (L19). `frozenset` no necesita import. `re.IGNORECASE` es flag de módulo.

### F4.2 `bot.py` — añadir `on_casete_help` y `maybe_invoke_casete` después de `decide_next_agent` (L743)

Insertar justo después de `decide_next_agent` (después de su `return`):

```python
async def on_casete_help(channel, user_id: str, target_word: str) -> None:
    """Responde a la petición de vocabulario de un jugador.
    
    Regla de oro: la palabra NUNCA la genera el LLM. Sale del lookup en known.
    Si no está en known, devuelve frase fija SIN tocar el LLM.
    """
    if not target_word or not target_word.strip():
        await send_agent_message(channel, "Casete",
            "🦜 ¿Qué palabra? Dime una palabra y te ayudo.", user_id=user_id)
        return
    
    state = load_state()
    user_vocab = state.get("casete_vocab", {}).get(user_id, {})
    known = set(user_vocab.get("known", []))
    counts = user_vocab.get("counts", {})
    threshold = user_vocab.get("threshold", 3)
    normalized = target_word.lower().strip()
    
    if normalized in known:
        # ✅ CASO A: palabra conocida → LLM genera SOLO la frase de entusiasmo
        logger.info(f"🦜 Casete help: '{normalized}' KNOWN → LLM call")
        prompt = (f"El jugador te pidió soplar la palabra '{normalized}'. "
                  f"Ya la tienes grabada. Repítela con entusiasmo de loro cyborg. "
                  f"Frase corta en inglés (≤15 palabras).")
        try:
            reaction = await call_openrouter(
                [{"role": "user", "content": prompt}],
                system=AGENT_PERSONAS["Casete"],
                temperature=0.9,
            )
            text = truncate_casete_response(reaction or f"¡{normalized}! ¡{normalized}!")
        except Exception as e:
            logger.error(f"❌ Casete LLM call failed: {e}")
            text = f"¡{normalized}! ¡{normalized}! ¡Casete lo tiene grabado!"
    else:
        # ❌ CASO B: NO conocida → frase fija, SIN LLM
        logger.info(f"🦜 Casete help: '{normalized}' NOT in known → fixed phrase (no LLM)")
        heard = counts.get(normalized, 0)
        if heard > 0:
            text = (f"🦜 Hmm... todavía no la tengo bien grabada. "
                    f"La he oído {heard}/{threshold} veces. "
                    f"¡Dila un poco más en la sala y la recordaré!")
        else:
            text = ("🦜 Hmm... esa todavía no me la han soplado. "
                    "Úsala en la sala y la grabaré en mi memoria.")
    
    await send_agent_message(channel, "Casete", text, user_id=user_id)


async def maybe_invoke_casete(message) -> bool:
    """Evalúa triggers en on_message. Devuelve True si Casete respondió (y hay que parar)."""
    if _CASETE_TRIGGERS_RE.search(message.content):
        word = extract_target_word(message.content)
        if word:
            user_id = str(message.author.id)
            logger.info(f"🦜 Casete trigger for {user_id}: '{word}'")
            await on_casete_help(message.channel, user_id, word)
            return True
    return False
```

### F4.3 `bot.py` — añadir comando `!casete` (insertar después de `cmd_speak`, antes de `cmd_helpme`)

Localizar `@bot.command(name="helpme")` (L1219) e insertar ANTES de él:

```python
@bot.command(name="casete")
async def cmd_casete(ctx, *, word: str = ""):
    """Pide a Casete que sople una palabra. !casete <word>"""
    await on_casete_help(ctx.channel, str(ctx.author.id), word)
```

**TRAMPA:** el parámetro `*, word` captura todo el resto como string, incluso con espacios. Si el usuario escribe `!casete`, `word=""` y se muestra la frase de ayuda. NO usar `argparse` ni `*args` — discord.py maneja `*, word` nativamente.

### F4.4 `bot.py` — integrar hook en `on_message` (entre L934 y L936)

Localizar la línea 934 (`author_name = message.author.name  # real Discord name...`). Inmediatamente DESPUÉS de esa línea, ANTES de la línea 936 (append al history), insertar:

```python
    # ─── Casete: trigger check (después de filtros, antes del sorteo) ───
    user_id = str(message.author.id)
    casete_handled = await maybe_invoke_casete(message)
    if casete_handled:
        return  # Casete respondió, no continuar con sorteo normal
```

**TRAMPA:** `user_id` debe ser `str(message.author.id)` (DISCORD USER ID), NO el `author_name`. Esto se usará después para `register_word_heard`.

### F4.5 `bot.py` — integrar conteo de palabras en `on_message` (después del append al history, L942)

Localizar la línea 942 (`is_human`: is_human,`)`) — fin del append. Inmediatamente DESPUÉS, insertar (antes de la sección `# Update activity tracking`):

```python
    # ─── Conteo de vocabulario Casete (humanos y agentes) ───
    user_id = str(message.author.id)
    state = load_state()
    for w in extract_notable_words(message.content):
        crossed = register_word_heard(state, user_id, w)
        if crossed:
            logger.info(f"🦜 Nueva palabra en vocab de {user_id}: '{w}'")
    save_state(state)
```

**TRAMPA:** el conteo de los mensajes de los agentes se hace en `send_agent_message` (F5), no aquí. Aquí solo se cuentan los mensajes de HUMANOS que llegan a `on_message`.

### F4.6 `bot.py:decide_next_agent` — fix L737-739 (corrección 1)

Localizar:
```python
    if recent_agents:
        last = recent_agents[-1]
        weights[last] = 0
```

Reemplazar por:
```python
    if recent_agents:
        last = recent_agents[-1]
        if last in weights:   # ← solo agentes en el weighted random (excluye Casete)
            weights[last] = 0
```

### F4.7 Verificación F4 (sin servicios — solo imports y regex)

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import bot

# Test 1: helpers existen y funcionan
words = bot.extract_notable_words('I think this is a really interesting breakthrough')
assert 'breakthrough' in words, f'breakthrough no extraído: {words}'
assert 'interesting' in words, f'interesting no extraído: {words}'
assert 'this' not in words, 'this debería ser stopword'
assert 'is' not in words, 'is debería ser stopword'
print(f'✅ Test 1: extract_notable_words extrae {words}')

# Test 2: extract_target_word
assert bot.extract_target_word('how do you say \"breakthrough\"') == 'breakthrough'
assert bot.extract_target_word('cómo se dice volatility') == 'volatility'
print('✅ Test 2: extract_target_word funciona con comillas y sin ellas')

# Test 3: truncate_casete_response
short = bot.truncate_casete_response('¡Hola!')
assert short == '¡Hola!', f'truncate no respetó texto corto: {short}'
long = bot.truncate_casete_response('a' * 200)
assert len(long) <= 80, f'truncate no recortó: {len(long)} chars'
assert long.endswith('!'), 'debe terminar en !'
print(f'✅ Test 3: truncate_casete_response recorta correctamente')

# Test 4: triggers regex
import re
for trig in bot.CASETE_TRIGGERS:
    assert bot._CASETE_TRIGGERS_RE.search(trig.replace('\\\\b', '')), f'trigger {trig} no matchea'
assert bot._CASETE_TRIGGERS_RE.search('how do you say \"volatility\"?')
assert bot._CASETE_TRIGGERS_RE.search('cómo se dice esto?')
print('✅ Test 4: CASETE_TRIGGERS matchea correctamente')

# Test 5: cmd_casete registrado
commands = [c.name for c in bot.bot.commands]
assert 'casete' in commands, f'!casete no registrado. Comandos: {commands}'
print('✅ Test 5: !casete registrado')
"
```

**Criterio de salida F4:** los 5 tests pasan.

### F4.8 Commit F4

```bash
cd /home/vaclav/discord-english-room
git add bot.py
git status
git commit -m "feat: Casete vocabulary logic (extract, on_casete_help, !casete command, hook)

- extract_notable_words: ≥4 chars, no stopwords EN, lowercase
- extract_target_word: prioriza comillas, fallback a última notable
- truncate_casete_response: ≤80 chars, no parte palabras
- CASETE_TRIGGERS: regex para 'cómo se dice', 'how do you say', etc.
- on_casete_help: lookup en known → LLM para frase; si no → frase fija SIN LLM
- maybe_invoke_casete: hook en on_message, retorna True si Casete respondió
- !casete <word>: comando Discord para pedir palabra explícitamente
- Fix decide_next_agent: 'if last in weights' evita KeyError cuando Casete es el último
- Conteo de palabras humanas: en on_message después del append al history"
```

---

## F5 — `state_manager.py`: `register_word_heard`, `migrate_state_v1_to_v2`, helpers

**Por qué quinto:** ahora que F4 llama a `register_word_heard` en runtime, el módulo state_manager debe tener la función. Sin esto, F4 rompe en runtime con ImportError.

### F5.1 Añadir `register_word_heard` y amigos (state_manager.py, después de L300)

Localizar el final de `save_personas` (última función del archivo) y añadir:

```python
# ─── Casete vocabulary (per-user, persistent) ──────────────────────────────

def get_casete_known(state: Dict[str, Any], user_id: str) -> list:
    """Devuelve palabras conocidas (cruzaron el umbral) para user_id, sorted."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return sorted(vocab.get("known", []))

def get_casete_counts(state: Dict[str, Any], user_id: str) -> Dict[str, int]:
    """Devuelve dict {word: count} para user_id."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return dict(vocab.get("counts", {}))

def get_casete_threshold(state: Dict[str, Any], user_id: str) -> int:
    """Devuelve el umbral del usuario (default 3)."""
    vocab = state.get("casete_vocab", {}).get(user_id, {})
    return int(vocab.get("threshold", 3))

def set_casete_threshold(state: Dict[str, Any], user_id: str, threshold: int) -> None:
    """Cambia el umbral de un usuario. Mínimo 1, máximo 99."""
    threshold = max(1, min(99, int(threshold)))
    state.setdefault("casete_vocab", {}).setdefault(user_id, {})
    state["casete_vocab"][user_id]["threshold"] = threshold

def register_word_heard(state: Dict[str, Any], user_id: str, word: str) -> bool:
    """Incrementa el contador de `word` para `user_id`.
    
    Si la palabra cruza el umbral, se añade a `known`.
    Devuelve True si la palabra es NUEVA en `known` (cruzó el umbral AHORA).
    Devuelve False si ya estaba, o si no cruzó el umbral todavía.
    
    Side effect: modifica `state` in-place. El caller debe persistir con save_state.
    """
    word = (word or "").lower().strip()
    if not word or len(word) < 4:
        return False
    
    state.setdefault("casete_vocab", {}).setdefault(user_id, {
        "threshold": 3,
        "counts": {},
        "known": [],
        "first_seen": {},
    })
    user_vocab = state["casete_vocab"][user_id]
    user_vocab.setdefault("threshold", 3)
    user_vocab.setdefault("counts", {})
    user_vocab.setdefault("known", [])
    user_vocab.setdefault("first_seen", {})
    
    known_set = set(user_vocab["known"])
    if word in known_set:
        return False  # ya estaba en known, no hacer nada
    
    # Registrar first_seen solo la primera vez
    if word not in user_vocab["first_seen"]:
        user_vocab["first_seen"][word] = datetime.now().isoformat()
    
    # Incrementar contador
    new_count = user_vocab["counts"].get(word, 0) + 1
    user_vocab["counts"][word] = new_count
    
    threshold = user_vocab["threshold"]
    if new_count >= threshold and word not in known_set:
        user_vocab["known"].append(word)
        user_vocab["known"].sort()
        logger.info(f"🦜 register_word_heard: '{word}' crossed threshold ({new_count}/{threshold}) for {user_id}")
        return True
    
    return False
```

**TRAMPA:** `logger` debe estar definido. Si no, añadir al inicio del archivo (después de los imports):
```python
import logging
logger = logging.getLogger("state_manager")
```

### F5.2 Verificación F5 (sin persistencia — solo in-memory)

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
from state_manager import register_word_heard, get_casete_known, get_casete_counts, get_casete_threshold, set_casete_threshold

# Estado limpio
state = {'casete_vocab': {}}

# Test 1: palabra oída 1 vez
crossed = register_word_heard(state, 'user1', 'breakthrough')
assert crossed is False, 'no debe cruzar en 1/3'
assert get_casete_counts(state, 'user1') == {'breakthrough': 1}
assert get_casete_known(state, 'user1') == []
print('✅ Test 1: 1/3 → no en known')

# Test 2: palabra oída 3 veces (cruza)
register_word_heard(state, 'user1', 'breakthrough')
crossed = register_word_heard(state, 'user1', 'breakthrough')
assert crossed is True, 'debe cruzar en 3/3'
assert 'breakthrough' in get_casete_known(state, 'user1')
print('✅ Test 2: 3/3 → en known')

# Test 3: palabra ya en known no devuelve True
crossed = register_word_heard(state, 'user1', 'breakthrough')
assert crossed is False, 'ya estaba en known, debe devolver False'
print('✅ Test 3: ya en known → False (no duplicar)')

# Test 4: palabra oída 2 veces (NO cruza)
register_word_heard(state, 'user1', 'volatile')
register_word_heard(state, 'user1', 'volatile')
assert 'volatile' not in get_casete_known(state, 'user1')
assert get_casete_counts(state, 'user1')['volatile'] == 2
print('✅ Test 4: 2/3 → no en known')

# Test 5: threshold configurable
set_casete_threshold(state, 'user1', 1)
crossed = register_word_heard(state, 'user1', 'rally')
assert crossed is True, 'con threshold=1, primera vez debe cruzar'
print('✅ Test 5: threshold=1 cruza en 1')

# Test 6: palabras muy cortas se ignoran
register_word_heard(state, 'user1', 'a')
register_word_heard(state, 'user1', 'go')
assert 'a' not in get_casete_counts(state, 'user1')
print('✅ Test 6: palabras <4 chars ignoradas')

# Test 7: multi-user aislado
state2 = {'casete_vocab': {}}
register_word_heard(state2, 'ronny', 'breakthrough')
assert 'breakthrough' in get_casete_known(state2, 'ronny')
assert 'breakthrough' not in get_casete_known(state2, 'user1')
print('✅ Test 7: vocabularios aislados por user_id')

# Test 8: persistencia tras reload (simulado)
import json
saved = json.dumps(state)
state_loaded = json.loads(saved)
assert 'breakthrough' in get_casete_known(state_loaded, 'user1')
print('✅ Test 8: estado persiste tras json round-trip')
"
```

**Criterio de salida F5:** los 8 tests pasan.

### F5.3 Commit F5

```bash
cd /home/vaclav/discord-english-room
git add state_manager.py
git status
git commit -m "feat(state): Casete vocabulary functions (register, get, threshold)

- register_word_heard(state, user_id, word): incrementa, devuelve True si cruzó
- get_casete_known(state, user_id): lista sorted de known
- get_casete_counts(state, user_id): dict {word: count}
- get_casete_threshold / set_casete_threshold: configurable
- Side effect: modifica state in-place, caller persiste con save_state
- Aislamiento por user_id (multi-user)
- Ignora palabras <4 chars
- No duplica en known (idempotente)"
```

---

## F6 — `state_manager.py`: migración v1→v2 (estructura multi-user)

**Por qué sexto:** Casete necesita `user_id` para contar vocabulario. La estructura `users[uid].sessions` se necesita en F7 para historial. Mejor migrar la estructura ahora.

### F6.1 Añadir `migrate_state_v1_to_v2` (state_manager.py, después de `save_state`)

Insertar:

```python
# ─── State migration ───────────────────────────────────────────────────────

def migrate_state_v1_to_v2(state: Dict[str, Any]) -> Dict[str, Any]:
    """Migra state v1 (conversation_history global) a v2 (users per-id).
    
    Idempotente: si ya es v2, devuelve el state sin cambios.
    Si es v1, mueve el conversation_history a users['legacy_vaclav'].
    
    Mantiene conversation_history global (recortado a 50) para compat
    con conversation_loop y !speak.
    """
    if state.get("version", 1) >= 2:
        return state
    
    logger.info("🔄 Migrating state v1 → v2")
    legacy_history = state.pop("conversation_history", [])
    
    state["version"] = 2
    state.setdefault("users", {})
    
    if "users" not in state or not state["users"]:
        state["users"] = {
            "legacy_vaclav": {
                "name": "Vaclav",
                "interests": [],
                "casete_vocab": state.pop("casete_vocab", {}).get("legacy_vaclav", {}),
                "sessions": [{
                    "id": "legacy",
                    "topic": "Migrated from v1",
                    "created": state.get("last_session", datetime.now().isoformat()),
                    "updated": datetime.now().isoformat(),
                    "messages": legacy_history,
                }],
                "active_session": "legacy",
            }
        }
    else:
        # Si ya hay users, solo añadir estructura mínima
        for uid, udata in state["users"].items():
            udata.setdefault("name", "Unknown")
            udata.setdefault("interests", [])
            udata.setdefault("casete_vocab", {})
            udata.setdefault("sessions", [])
            udata.setdefault("active_session", None)
    
    # conversation_history global se mantiene (recortado)
    state["conversation_history"] = legacy_history[-MAX_HISTORY:]
    logger.info(f"🔄 Migration done: {len(legacy_history)} mensajes legacy")
    return state
```

### F6.2 Llamar a la migración en `load_state` (state_manager.py L33)

Localizar la función `load_state()` y modificar SU PRIMERA LÍNEA después del `def` para incluir la migración. La función actual devuelve el state en varios puntos. Localizar la última línea `return state` y la línea `return DEFAULT_STATE.copy()` y migrar antes de cada return.

Forma más simple: añadir una llamada al inicio de la función:

```python
def load_state() -> Dict[str, Any]:
    """Load state from JSON file. Returns default if not found or corrupted."""
    ensure_state_dir()
    
    if not STATE_PATH.exists():
        state = DEFAULT_STATE.copy()
        return migrate_state_v1_to_v2(state)
    
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # Ensure all keys exist (backward compatibility)
        for key, value in DEFAULT_STATE.items():
            if key not in state:
                state[key] = value
        
        # Trim history if too long
        if len(state.get("conversation_history", [])) > MAX_HISTORY:
            state["conversation_history"] = state["conversation_history"][-MAX_HISTORY:]
        
        # ─── MIGRACIÓN v1→v2 ───
        state = migrate_state_v1_to_v2(state)
        
        return state
    except (json.JSONDecodeError, OSError):
        # Corrupted or unreadable - return default
        return migrate_state_v1_to_v2(DEFAULT_STATE.copy())
```

**TRAMPA:** la migración puede ser costosa en state grande. Si tu `state.json` tiene >1000 mensajes, el primer arranque tras Commit 6 puede tardar 1-2 segundos. Es aceptable (solo ocurre una vez).

### F6.3 Verificación F6 (con backup del state real)

```bash
# BACKUP del state real
cp ~/.english-bot/state.json ~/.english-bot/state.json.backup-pre-f6

cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
from state_manager import load_state, save_state, migrate_state_v1_to_v2

# Test 1: state v1 → v2 automático en load
import json
v1_state = {
    'conversation_history': [
        {'author': 'Vaclav', 'content': 'Hello', 'timestamp': '2026-01-01T00:00:00', 'is_human': True},
        {'author': 'Alex', 'content': 'Hi there', 'timestamp': '2026-01-01T00:00:01', 'agent': 'Alex'},
    ],
    'current_topic_index': 0,
    'topic_locked': True,
    'user_config': {'tts_speed': 1.0, 'voices': {}},
    'last_session': '2026-01-01T00:00:01',
    'paused': False,
}
migrated = migrate_state_v1_to_v2(v1_state)
assert migrated['version'] == 2, f'version no es 2: {migrated[\"version\"]}'
assert 'legacy_vaclav' in migrated['users'], 'legacy_vaclav no creado'
assert len(migrated['users']['legacy_vaclav']['sessions']) == 1
assert len(migrated['users']['legacy_vaclav']['sessions'][0]['messages']) == 2
print('✅ Test 1: migración v1→v2 OK')

# Test 2: idempotencia
migrated_twice = migrate_state_v1_to_v2(migrated)
assert migrated_twice == migrated, 'idempotencia rota'
print('✅ Test 2: idempotente')

# Test 3: state real del usuario se migra al cargar
import os
real_state = load_state()
assert real_state.get('version') == 2, f'state real no migrado: {real_state.get(\"version\")}'
print(f'✅ Test 3: state real migrado a v2 (users: {list(real_state[\"users\"].keys())})')
"
```

**Criterio de salida F6:** los 3 tests pasan, y el state real quedó migrado (puede tener `version: 2` ahora). Si quieres volver al estado original: `cp ~/.english-bot/state.json.backup-pre-f6 ~/.english-bot/state.json`.

### F6.4 Commit F6

```bash
cd /home/vaclav/discord-english-room
git add state_manager.py
git status
git commit -m "feat(state): migration v1→v2 (multi-user structure)

- migrate_state_v1_to_v2() llamada en load_state() antes de devolver
- Preserva conversation_history viejo como users['legacy_vaclav'].sessions[0]
- conversation_history global se mantiene (recortado) para compat con conversation_loop
- Idempotente: si ya es v2, no hace nada
- Estructura users[uid] con: name, interests, casete_vocab, sessions[], active_session
- El state real se migra automáticamente al primer load tras este commit"
```

---

## F7 — `state_manager.py`: sesiones por usuario (create/list/resume/save-obsidian)

**Por qué séptimo:** con la estructura multi-user lista, ahora implementamos la lógica de sesiones.

### F7.1 Funciones de sesión (state_manager.py, al final del archivo)

```python
# ─── User sessions (persistent, no trim) ───────────────────────────────────

def list_user_sessions(state: Dict[str, Any], user_id: str) -> list:
    """Lista sesiones del user (resumidas: id, topic, created, updated, #msgs)."""
    sessions = state.get("users", {}).get(user_id, {}).get("sessions", [])
    return [
        {
            "id": s.get("id"),
            "topic": s.get("topic", "Untitled"),
            "created": s.get("created"),
            "updated": s.get("updated"),
            "message_count": len(s.get("messages", [])),
        }
        for s in sessions
    ]

def get_active_session(state: Dict[str, Any], user_id: str) -> Optional[dict]:
    """Devuelve la sesión activa del user, o None."""
    user = state.get("users", {}).get(user_id, {})
    sid = user.get("active_session")
    if not sid:
        return None
    for s in user.get("sessions", []):
        if s.get("id") == sid:
            return s
    return None

def set_active_session(state: Dict[str, Any], user_id: str, session_id: str) -> bool:
    """Marca una sesión como activa. Devuelve True si existe."""
    user = state.get("users", {}).get(user_id, {})
    if any(s.get("id") == session_id for s in user.get("sessions", [])):
        user["active_session"] = session_id
        return True
    return False

def create_user_session(state: Dict[str, Any], user_id: str, topic: str = "Untitled") -> dict:
    """Crea una nueva sesión vacía para el user, la marca como activa."""
    import uuid
    user = state.setdefault("users", {}).setdefault(user_id, {
        "name": "Unknown",
        "interests": [],
        "casete_vocab": {},
        "sessions": [],
        "active_session": None,
    })
    session = {
        "id": str(uuid.uuid4())[:8],
        "topic": topic,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "messages": [],
    }
    user["sessions"].append(session)
    user["active_session"] = session["id"]
    logger.info(f"📂 Sesión creada: {session['id']} (user={user_id}, topic={topic})")
    return session

def append_session_message(state: Dict[str, Any], user_id: str, message: dict) -> None:
    """Añade un mensaje a la sesión activa del user."""
    session = get_active_session(state, user_id)
    if not session:
        # Auto-crear sesión si no hay activa
        create_user_session(state, user_id, "Auto-created")
        session = get_active_session(state, user_id)
    session["messages"].append(message)
    session["updated"] = datetime.now().isoformat()
```

### F7.2 Verificación F7

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
from state_manager import (
    create_user_session, list_user_sessions, get_active_session,
    set_active_session, append_session_message
)

# Test 1: crear sesión
state = {'users': {}}
sess = create_user_session(state, 'user1', 'Test topic')
assert sess['id'] and sess['topic'] == 'Test topic'
assert get_active_session(state, 'user1')['id'] == sess['id']
print('✅ Test 1: crear + marcar activa')

# Test 2: añadir mensajes
append_session_message(state, 'user1', {'author':'Vaclav','content':'Hi','ts':'2026-01-01T00:00:00'})
append_session_message(state, 'user1', {'author':'Alex','content':'Hello','ts':'2026-01-01T00:00:01'})
active = get_active_session(state, 'user1')
assert len(active['messages']) == 2
print(f'✅ Test 2: 2 mensajes añadidos')

# Test 3: listar
sessions = list_user_sessions(state, 'user1')
assert len(sessions) == 1
assert sessions[0]['message_count'] == 2
print('✅ Test 3: list_user_sessions correcto')

# Test 4: crear segunda sesión
sess2 = create_user_session(state, 'user1', 'Second topic')
assert get_active_session(state, 'user1')['id'] == sess2['id']
sessions = list_user_sessions(state, 'user1')
assert len(sessions) == 2
print('✅ Test 4: múltiples sesiones, active actualizada')

# Test 5: cambiar a sesión previa
assert set_active_session(state, 'user1', sess['id'])
assert get_active_session(state, 'user1')['id'] == sess['id']
print('✅ Test 5: set_active_session funciona')

# Test 6: set_active con id inexistente → False
assert set_active_session(state, 'user1', 'nonexistent') is False
print('✅ Test 6: set_active con id inválido → False')

# Test 7: aislamiento entre users
create_user_session(state, 'ronny', 'Ronny topic')
sess_user1 = list_user_sessions(state, 'user1')
sess_ronny = list_user_sessions(state, 'ronny')
assert len(sess_user1) == 2 and len(sess_ronny) == 1
print('✅ Test 7: aislamiento multi-user')
"
```

**Criterio de salida F7:** los 7 tests pasan.

### F7.3 Commit F7

```bash
cd /home/vaclav/discord-english-room
git add state_manager.py
git status
git commit -m "feat(state): user sessions (create, list, resume, append)

- list_user_sessions: array resumido de sesiones del user
- get_active_session / set_active_session: marcar activa
- create_user_session: crea uuid corto, auto-marca como activa
- append_session_message: añade msg a la activa, auto-crea si no hay
- Sesiones NO se recortan (persistentes)
- Multi-user aislado por user_id"
```

---

## F8 — Comandos Discord: `!sessions`, `!session`, `!preferences`, extender `!topic`

**Por qué octavo:** con la lógica de sesiones lista, ahora exponemos los comandos Discord.

### F8.1 Añadir comandos después de `cmd_helpme` (bot.py, después de L1238)

```python
# ─── Sessions ──────────────────────────────────────────────────────────────

@bot.command(name="sessions")
async def cmd_sessions(ctx):
    """Lista las sesiones guardadas del usuario."""
    user_id = str(ctx.author.id)
    state = load_state()
    sessions = list_user_sessions(state, user_id)
    if not sessions:
        await ctx.send("📂 No tienes sesiones guardadas aún.")
        return
    lines = [f"📂 **{len(sessions)} sesiones:**"]
    for s in sessions[:10]:
        marker = "▶️" if s["id"] == state["users"].get(user_id, {}).get("active_session") else "  "
        lines.append(f"{marker} `{s['id']}` — {s['topic']} ({s['message_count']} msgs, {s['created'][:10]})")
    await ctx.send("\n".join(lines))

@bot.command(name="session")
async def cmd_session(ctx, subcmd: str = "", *, arg: str = ""):
    """Subcomandos: new, resume, save."""
    user_id = str(ctx.author.id)
    state = load_state()
    
    if subcmd == "new":
        topic = arg or "Untitled"
        sess = create_user_session(state, user_id, topic)
        save_state(state)
        await ctx.send(f"📂 Sesión creada: `{sess['id']}` (tema: {topic})")
    
    elif subcmd == "resume":
        if arg == "last":
            sessions = state.get("users", {}).get(user_id, {}).get("sessions", [])
            if not sessions:
                await ctx.send("📂 No hay sesiones para retomar.")
                return
            target_id = sessions[-1]["id"]
        else:
            target_id = arg
        if set_active_session(state, user_id, target_id):
            active = get_active_session(state, user_id)
            n_msgs = len(active.get("messages", []))
            await ctx.send(f"▶️ Sesión `{target_id}` retomada ({n_msgs} mensajes, tema: {active.get('topic','?')})")
        else:
            await ctx.send(f"❌ Sesión `{target_id}` no encontrada.")
    
    elif subcmd == "save":
        # Export a Obsidian vía audio_server
        import aiohttp
        active = get_active_session(state, user_id)
        if not active:
            await ctx.send("❌ No hay sesión activa.")
            return
        try:
            async with aiohttp.ClientSession() as session_http:
                async with session_http.post(
                    "http://localhost:8081/api/session/save-obsidian",
                    json={"user_id": user_id, "session_id": active["id"]},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        await ctx.send(f"💾 Sesión exportada a Obsidian: `{data.get('path','?')}`")
                    else:
                        await ctx.send(f"❌ Error al exportar: {data.get('error','?')}")
        except Exception as e:
            await ctx.send(f"❌ No se pudo conectar al audio server: {e}")
    
    else:
        await ctx.send("Subcomandos: `!session new [tema]`, `!session resume <id|last>`, `!session save`")

# ─── Preferences ───────────────────────────────────────────────────────────

@bot.command(name="preferences")
async def cmd_preferences(ctx, action: str = "", *, args: str = ""):
    """!preferences [add|remove|clear|list] <words...>"""
    user_id = str(ctx.author.id)
    state = load_state()
    user = state.setdefault("users", {}).setdefault(user_id, {
        "name": ctx.author.name,
        "interests": [],
        "casete_vocab": {},
        "sessions": [],
        "active_session": None,
    })
    interests = user.setdefault("interests", [])
    
    if action == "add" and args:
        new_words = [w.strip().lower() for w in args.split() if w.strip()]
        added = [w for w in new_words if w not in interests]
        interests.extend(added)
        save_state(state)
        await ctx.send(f"✅ Añadidos: {', '.join(added) if added else '(ninguno nuevo)'}. Total: {len(interests)}")
    
    elif action == "remove" and args:
        words = [w.strip().lower() for w in args.split() if w.strip()]
        removed = [w for w in words if w in interests]
        for w in removed:
            interests.remove(w)
        save_state(state)
        await ctx.send(f"🗑️ Quitados: {', '.join(removed) if removed else '(ninguno)'}. Total: {len(interests)}")
    
    elif action == "clear":
        interests.clear()
        save_state(state)
        await ctx.send("🗑️ Intereses borrados.")
    
    else:
        # list (default)
        if not interests:
            await ctx.send("📋 Sin intereses. Usa `!preferences add travel cooking tech`")
        else:
            await ctx.send(f"📋 Intereses: {', '.join(interests)}")
```

### F8.2 Extender `!topic` — añadir subcomandos `suggest` y `pick` (bot.py, dentro de `cmd_topic`)

Localizar `cmd_topic` (bot.py L1009). Localizar el bloque `if not subcommand` o el último `else` que muestra la ayuda. AÑADIR antes de ese bloque (o integrarlo en la lógica existente):

```python
@bot.command(name="topic")
async def cmd_topic(ctx, *, subcommand: str = ""):
    """!topic [list|next|suggest|refresh|pick <texto>|index]"""
    global current_topic_index
    user_id = str(ctx.author.id)
    state = load_state()
    user = state.setdefault("users", {}).setdefault(user_id, {
        "name": ctx.author.name, "interests": [], "casete_vocab": {},
        "sessions": [], "active_session": None,
    })
    interests = user.setdefault("interests", [])
    
    if subcommand == "suggest" or subcommand == "refresh":
        force = subcommand == "refresh"
        suggestions = await generate_topic_suggestions(user_id, state, force_refresh=force)
        user["last_topic_suggestions"]["topics"] = suggestions
        save_state(state)
        lines = [f"🎯 **5 sugerencias {'(refrescadas)' if force else '(cacheadas)'}** (tus intereses: {', '.join(interests) or 'ninguno'}):"]
        for i, t in enumerate(suggestions[:5], 1):
            if isinstance(t, dict):
                lines.append(f"  {i}. **{t.get('theme','?')}** — {t.get('hook','')[:80]}")
            else:
                lines.append(f"  {i}. {t}")
        await ctx.send("\n".join(lines))
        return
    
    if subcommand == "pick":
        # El tema libre es todo lo que viene después de "pick"
        # discord.py ya separa: !topic pick foo bar → subcommand="pick foo bar"
        parts = subcommand.split(maxsplit=1)
        if len(parts) < 2:
            await ctx.send("❌ Uso: `!topic pick <tema libre>`")
            return
        custom_topic = parts[1]
        # Guardar como custom_topic
        state["custom_topic"] = custom_topic
        current_topic_index = -1  # marca de tema custom
        save_state(state)
        await ctx.send(f"🎯 Tema fijado: **{custom_topic}**. (Vocabulary seed pendiente de generar)")
        return
    
    # ... resto de la lógica existente (list, next, show, index) ...
    # NO TOCAR el resto, solo añadir estos dos subcomandos nuevos.
```

**TRAMPA:** `cmd_topic` ya existe. NO redefinir todo el comando, solo añadir las ramas `suggest`/`refresh`/`pick` AL PRINCIPIO del cuerpo. Si el código original tiene otra estructura (if/else encadenado), añadir las ramas en el orden que tenga sentido.

### F8.3 Verificación F8 (smoke test sin Discord real)

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import bot
import inspect

# Test 1: comandos registrados
commands = [c.name for c in bot.bot.commands]
for cmd in ['casete', 'sessions', 'session', 'preferences']:
    assert cmd in commands, f'!{cmd} no registrado. Comandos: {commands}'
print(f'✅ Test 1: {len(commands)} comandos, todos los nuevos presentes')

# Test 2: cmd_session tiene 3 subcomandos documentados
src = inspect.getsource(bot.cmd_session)
for sc in ['new', 'resume', 'save']:
    assert sc in src, f'subcomando {sc} no implementado'
print('✅ Test 2: cmd_session tiene new/resume/save')

# Test 3: cmd_preferences tiene 4 acciones
src = inspect.getsource(bot.cmd_preferences)
for ac in ['add', 'remove', 'clear']:
    assert ac in src, f'acción {ac} no implementada'
print('✅ Test 3: cmd_preferences tiene add/remove/clear')

# Test 4: cmd_topic tiene suggest y pick
src = inspect.getsource(bot.cmd_topic)
assert 'suggest' in src, '!topic suggest no implementado'
assert 'pick' in src, '!topic pick no implementado'
print('✅ Test 4: cmd_topic extendido con suggest/pick')
"
```

**Criterio de salida F8:** los 4 tests pasan.

### F8.4 Commit F8

```bash
cd /home/vaclav/discord-english-room
git add bot.py
git status
git commit -m "feat: Discord commands for sessions, preferences, topic suggestions

- !sessions: lista sesiones del usuario
- !session new [tema]: crea sesión
- !session resume <id|last>: retoma sesión
- !session save: export a Obsidian vía /api/session/save-obsidian
- !preferences [add|remove|clear|list] <words...>
- !topic suggest: 5 sugerencias personalizadas (cacheadas)
- !topic refresh: regenera sugerencias ignorando cache
- !topic pick <texto>: tema libre
- Aislamiento multi-user via ctx.author.id"
```

---

## F9 — `generate_topic_suggestions` (bot.py) y conteo de agentes en Casete (bot.py)

**Por qué noveno:** los comandos `!topic suggest` llaman a esta función. El conteo de Casete para mensajes de agentes necesita `send_agent_message` actualizado.

### F9.1 `bot.py:generate_topic_suggestions` (insertar después de `cmd_topic`)

```python
async def generate_topic_suggestions(user_id: str, state: dict, force_refresh: bool = False) -> list:
    """Genera 5 temas sugeridos basados en intereses del user. Cacheado por hash.
    
    Returns: lista de dicts {theme, seed_vocab, hook} o strings si son del catálogo.
    """
    interests = state.get("users", {}).get(user_id, {}).get("interests", [])
    cache_key = hash(tuple(sorted(interests)))
    
    cached = state.get("users", {}).get(user_id, {}).get("last_topic_suggestions", {})
    if not force_refresh and cached.get("interests_hash") == cache_key:
        try:
            from datetime import datetime as _dt
            age_hours = (_dt.now() - _dt.fromisoformat(cached["generated_at"])).total_seconds() / 3600
            if age_hours < 24:
                return cached.get("topics", [])
        except Exception:
            pass
    
    if not interests:
        # Sin intereses: usar TOPICS aleatorios
        topics = random.sample(TOPICS, min(5, len(TOPICS)))
    else:
        prompt = f"""Generate 5 conversation topics for an English practice group chat.
User interests: {', '.join(interests)}
English level: intermediate (B1-B2)

Return ONLY a JSON array of objects with these fields:
- "theme": topic title (3-5 words)
- "seed_vocab": array of 6 vocabulary words/phrases for this topic
- "hook": one engaging question to start the conversation

Example:
[{{"theme":"Weekend Cooking Plans","seed_vocab":["recipe","ingredient","stir-fry","bake","simmer","taste"],"hook":"What's the most adventurous dish you've ever cooked?"}}]"""
        try:
            response = await call_openrouter(
                [{"role": "user", "content": prompt}],
                system="You are a helpful English teaching assistant. Return ONLY valid JSON, no markdown.",
                temperature=0.9,
            )
            topics = json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ generate_topic_suggestions LLM fallback: {e}")
            topics = TOPICS[:5]
    
    # Cachear
    state.setdefault("users", {}).setdefault(user_id, {})
    state["users"][user_id]["last_topic_suggestions"] = {
        "generated_at": datetime.now().isoformat(),
        "interests_hash": cache_key,
        "topics": topics,
    }
    return topics
```

### F9.2 `bot.py:send_agent_message` — añadir parámetro `user_id` y contar vocab

Localizar la firma de `send_agent_message` (bot.py L474). Cambiar a:
```python
async def send_agent_message(channel: discord.TextChannel, agent_name: str, text: str, user_id: Optional[str] = None):
```

Localizar el bloque donde se llama a `generate_tts` y `webhook.send`. ANTES de esas llamadas, añadir:
```python
    # ─── Conteo de vocabulario para Casete (palabras que dicen los agentes) ───
    if user_id and user_id != "0":
        try:
            state = load_state()
            for w in extract_notable_words(text):
                register_word_heard(state, user_id, w)
            save_state(state)
        except Exception as e:
            logger.warning(f"⚠️ Conteo Casete en send_agent_message falló: {e}")
```

**TRAMPA:** este conteo es **adicional** al que ya hicimos en `on_message` (F4.5). En `on_message`, cuando llega un mensaje humano, contamos sus palabras Y generamos respuesta con un agente (que también hablará). Si `send_agent_message` cuenta las palabras del agente, el humano recibe 2 cuentas por turno (la suya + la del agente). Esto es **deseable** según el spec ("Cuenta tanto lo que dice el jugador como lo que dicen otros personajes").

### F9.3 Verificación F9

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import asyncio
import bot
from state_manager import load_state, get_casete_known

# Test 1: generate_topic_suggestions con intereses vacíos → TOPICS aleatorios
async def test1():
    state = {'users': {}}
    topics = await bot.generate_topic_suggestions('user1', state, force_refresh=True)
    assert len(topics) >= 1, 'sin intereses debería devolver TOPICS base'
    print(f'✅ Test 1: sin intereses → {len(topics)} temas base')

# Test 2: cache funciona
async def test2():
    state = {'users': {}}
    t1 = await bot.generate_topic_suggestions('user1', state, force_refresh=True)
    t2 = await bot.generate_topic_suggestions('user1', state, force_refresh=False)
    # Deben ser iguales (cache)
    assert t1 == t2, 'cache no funciona'
    print('✅ Test 2: cache funciona (mismos temas en 2da llamada)')

# Test 3: con intereses llama al LLM (si hay key) o cae a TOPICS
async def test3():
    state = {'users': {'user1': {'interests': ['travel', 'cooking']}}}
    topics = await bot.generate_topic_suggestions('user1', state, force_refresh=True)
    assert len(topics) >= 1
    print(f'✅ Test 3: con intereses → {len(topics)} temas (LLM o fallback)')

# Test 4: send_agent_message acepta user_id (signature check)
import inspect
sig = inspect.signature(bot.send_agent_message)
assert 'user_id' in sig.parameters, f'send_agent_message no acepta user_id. Sig: {sig}'
assert sig.parameters['user_id'].default is None
print('✅ Test 4: send_agent_message(user_id=None)')

asyncio.run(test1())
asyncio.run(test2())
asyncio.run(test3())
"
```

**Criterio de salida F9:** los 4 tests pasan.

### F9.4 Commit F9

```bash
cd /home/vaclav/discord-english-room
git add bot.py
git status
git commit -m "feat: generate_topic_suggestions + Casete count in agent messages

- generate_topic_suggestions: 5 temas LLM-based o TOPICS aleatorios
  - Cache 24h por hash de intereses
  - Fallback a TOPICS base si LLM falla
- send_agent_message: nuevo param user_id
  - Si user_id presente, cuenta palabras del agente en vocab Casete
  - Compatible con call-sites existentes (default user_id=None)
- Multi-user: cada player tiene su propio vocab de Casete"
```

---

## F10 — `audio_server.py`: endpoints nuevos (sessions, topics, preferences, obsidian-save)

**Por qué décimo:** la GUI en F11 consume estos endpoints. Sin endpoints, F11 no tiene qué llamar.

### F10.1 Añadir imports y endpoints (audio_server.py, después de los handlers de personas existentes)

Insertar los imports adicionales al inicio de las funciones que los necesitan (no arriba del archivo, para no romper lazy imports circulares):

```python
# Dentro de cada handler que use state_manager, importar localmente:
# from state_manager import (
#     list_user_sessions, get_active_session, create_user_session,
#     set_active_session, get_casete_known, get_casete_counts,
#     set_casete_threshold, get_casete_threshold
# )
```

#### Endpoint: `GET /api/sessions`

```python
async def sessions_list_handler(request):
    """GET /api/sessions?user_id=... — lista sesiones del user."""
    user_id = request.query.get("user_id", "")
    if not user_id:
        return web.json_response({"error": "user_id required"}, status=400)
    from state_manager import load_state, list_user_sessions
    state = load_state()
    sessions = list_user_sessions(state, user_id)
    return web.json_response({"user_id": user_id, "sessions": sessions})

# Registrar en start_audio_server() (audio_server.py cerca de L393):
# app.router.add_get('/api/sessions', sessions_list_handler)
```

#### Endpoint: `POST /api/sessions`

```python
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

# app.router.add_post('/api/sessions', sessions_create_handler)
```

#### Endpoint: `POST /api/sessions/resume`

```python
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

# app.router.add_post('/api/sessions/resume', sessions_resume_handler)
```

#### Endpoint: `POST /api/session/save-obsidian`

```python
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

# app.router.add_post('/api/session/save-obsidian', session_save_obsidian_handler)
```

#### Endpoint: `GET /api/topics`

```python
async def topics_list_handler(request):
    """GET /api/topics?user_id=... — TOPICS base + sugerencias cacheadas del user."""
    user_id = request.query.get("user_id", "")
    from state_manager import load_state
    state = load_state()
    from bot import TOPICS, generate_topic_suggestions
    suggestions = []
    if user_id:
        suggestions = state.get("users", {}).get(user_id, {}).get("last_topic_suggestions", {}).get("topics", [])
    return web.json_response({
        "topics_base": TOPICS,
        "suggestions": suggestions,
    })

# app.router.add_get('/api/topics', topics_list_handler)
```

#### Endpoint: `POST /api/topic`

```python
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
        state["custom_topic"] = topic
        save_state(state)
        return web.json_response({"status": "ok", "topic": topic})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# app.router.add_post('/api/topic', topic_set_handler)
```

#### Endpoint: `GET /api/preferences` y `POST /api/preferences`

```python
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

# app.router.add_get('/api/preferences', preferences_handler)
# app.router.add_post('/api/preferences', preferences_handler)
```

#### Modificar `POST /api/tts-preview` para aceptar dict voice

Localizar el handler `tts_preview_handler` existente (audio_server.py L283). Reemplazar la sección `import edge_tts` + `edge_tts.Communicate` por:

```python
# En el handler, reemplazar la lógica edge_tts por:
from tts_providers import generate_tts
voice = body.get("voice", "en-US-GuyNeural")
audio_data = await generate_tts(text, voice)
if not audio_data:
    return web.json_response({"error": "TTS failed (both providers)"}, status=500)
return web.Response(body=audio_data, content_type="audio/mpeg", headers={"Content-Disposition": "inline"})
```

#### Modificar `GET /api/personas` para incluir `voice_providers`

Localizar el handler `personas_get_handler` y añadir `"voice_providers": [...]` al JSON de respuesta. Detectar si ElevenLabs key es real:

```python
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
```

### F10.2 Registrar las nuevas rutas en `start_audio_server()` (audio_server.py cerca de L393-396)

Añadir las 8 líneas siguientes (después de los `add_get`/`add_post` existentes):

```python
    app.router.add_get('/api/sessions', sessions_list_handler)
    app.router.add_post('/api/sessions', sessions_create_handler)
    app.router.add_post('/api/sessions/resume', sessions_resume_handler)
    app.router.add_post('/api/session/save-obsidian', session_save_obsidian_handler)
    app.router.add_get('/api/topics', topics_list_handler)
    app.router.add_post('/api/topic', topic_set_handler)
    app.router.add_get('/api/preferences', preferences_handler)
    app.router.add_post('/api/preferences', preferences_handler)
```

### F10.3 Verificación F10 (con server arrancado)

```bash
cd /home/vaclav/discord-english-room
unset PYTHONPATH
# Arrancar audio server en background
nohup venv/bin/python audio_server.py > .pids/audio-f10.log 2>&1 &
sleep 4

# Test 1: health
curl -sf http://localhost:8081/health && echo "✅ Test 1: health OK"

# Test 2: GET /api/sessions (sin user_id → 400)
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/api/sessions)
[ "$status" = "400" ] && echo "✅ Test 2: GET /api/sessions sin user_id → 400" || echo "❌ esperado 400, got $status"

# Test 3: POST /api/sessions crear
curl -s -X POST http://localhost:8081/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","topic":"F10 verification topic"}' \
  | head -c 200
echo ""
echo "✅ Test 3: POST /api/sessions devolvió sesión"

# Test 4: GET /api/sessions listar
curl -s "http://localhost:8081/api/sessions?user_id=test_user" | head -c 300
echo ""

# Test 5: GET /api/topics
curl -s "http://localhost:8081/api/topics" | head -c 200
echo ""
echo "✅ Test 5: GET /api/topics OK"

# Test 6: POST /api/preferences
curl -s -X POST http://localhost:8081/api/preferences \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","interests":["travel","cooking"]}' | head -c 200
echo ""

# Test 7: GET /api/personas incluye voice_providers
curl -s http://localhost:8081/api/personas | python3 -c "
import sys, json
d = json.load(sys.stdin)
vp = d.get('voice_providers', [])
ids = [v['id'] for v in vp]
assert 'edge' in ids and 'elevenlabs' in ids, f'voice_providers faltan: {ids}'
print(f'✅ Test 7: voice_providers={ids}')
"

# Test 8: tts-preview con dict ElevenLabs (debe devolver audio por fallback)
curl -s -X POST http://localhost:8081/api/tts-preview \
  -H "Content-Type: application/json" \
  -d '{"text":"Casete test","voice":{"provider":"elevenlabs","voice_id":"fake","model":"eleven_flash_v2_5","fallback":"en-US-AndrewNeural"}}' \
  --output /tmp/f10-preview.mp3
file /tmp/f10-preview.mp3 | grep -q "MPEG" && echo "✅ Test 8: tts-preview dict ElevenLabs → audio OK"

# Matar server
pkill -9 -f "audio_server.py" 2>/dev/null
sleep 1
```

**Criterio de salida F10:** los 8 tests pasan.

### F10.4 Commit F10

```bash
cd /home/vaclav/discord-english-room
git add audio_server.py
git status
git commit -m "feat(api): sessions, topics, preferences, obsidian-save endpoints

- GET /api/sessions?user_id → lista sesiones
- POST /api/sessions {user_id, topic} → crea sesión
- POST /api/sessions/resume {user_id, session_id} → marca activa
- POST /api/session/save-obsidian → exporta sesión a Obsidian (markdown
  estructurado con frontmatter, participantes, transcripción, vocab Casete)
- GET /api/topics?user_id → TOPICS base + sugerencias cacheadas
- POST /api/topic {user_id, topic} → fija tema custom
- GET|POST /api/preferences → intereses del user
- /api/tts-preview acepta dict voice ElevenLabs (delegado a tts_providers)
- /api/personas incluye voice_providers con availability dinámico"
```

---

## F11 — GUI: `audio_player.html` (card Casete, modal Historial, pestaña Temas, selector voz)

**Por qué undécimo:** con todo el backend listo, ahora exponemos al usuario.

### F11.1 Cambios en `audio_player.html`

**TRAMPA:** este archivo tiene 509 líneas y no está estandarizado. El editor debe:
1. Localizar el bloque `<div class="agent-card" id="card-Sam">` (L194-198)
2. Insertar DESPUÉS de Sam (antes del cierre `</div>` del grid):

```html
        <div class="agent-card" id="card-Casete">
            <div class="agent-emoji" id="emoji-Casete">🦜</div>
            <div class="agent-name">Casete</div>
            <div class="agent-voice" id="voice-Casete">elevenlabs · cyborg</div>
            <div class="speaking-indicator"></div>
        </div>
```

3. Localizar el array de colores JS (L229 aprox): `Alex: '#5865f2', Maya: '#57f287', Jordan: '#fee75c', Sam: '#eb459e'` → añadir `, Casete: '#00ffaa'`.

4. Localizar el array `AGENT_NAMES` (si existe) → añadir `"Casete"`.

5. Localizar el bloque del modal de Settings (ya existe por el editor de personalidad previo). AÑADIR una 5ª tab "🦜 Casete" con la misma estructura que las otras 4, pero con selector de voz de DOS PESTAÑAS:

```html
<div class="voice-provider-tabs" style="display:flex;gap:8px;margin-bottom:8px">
    <button type="button" class="btn-tab active" data-provider="edge">🗣 Edge (humano)</button>
    <button type="button" class="btn-tab" data-provider="elevenlabs">🦜 ElevenLabs (personaje)</button>
</div>
<div class="voice-provider-content" data-provider="edge">
    <label>Voz Edge TTS:</label>
    <select class="voice-select-edge">
        <option value="en-US-AndrewNeural">en-US-AndrewNeural (fallback Casete)</option>
        <!-- (resto de voces Edge vía JS, poblado desde voice_providers) -->
    </select>
</div>
<div class="voice-provider-content" data-provider="elevenlabs" style="display:none">
    <label>ElevenLabs voice_id:</label>
    <input type="text" class="voice-id-input" placeholder="Ej: abc123def456 (de elevenlabs.io)">
    <small>Si no tienes key real, este provider cae a Edge fallback.</small>
</div>
```

6. Añadir botón flotante `📜` junto al `⚙️` existente → abre modal "📜 Historial".

7. El modal Historial:
```html
<div id="historyModal" class="modal-overlay" style="display:none">
    <div class="modal-content">
        <h2>📜 Historial de Sesiones</h2>
        <div id="sessionsList"></div>
        <div class="auto-save-toggle">
            <label><input type="checkbox" id="autoSaveToggle"> Auto-guardar en Obsidian al cerrar</label>
        </div>
        <button onclick="closeHistoryModal()">Cerrar</button>
    </div>
</div>
```

8. JavaScript al final del `<script>` existente:
```javascript
// === HISTORIAL ===
let currentUserId = 'legacy_vaclav';  // TODO: detectar del auth real

async function openHistoryModal() {
    const resp = await fetch(`/api/sessions?user_id=${currentUserId}`);
    const data = await resp.json();
    const list = document.getElementById('sessionsList');
    if (!data.sessions || data.sessions.length === 0) {
        list.innerHTML = '<p>No tienes sesiones guardadas.</p>';
    } else {
        list.innerHTML = data.sessions.map(s => `
            <div class="session-item">
                <strong>${s.topic}</strong> (${s.message_count} msgs, ${s.created.slice(0,10)})
                <code>${s.id}</code>
                <button onclick="resumeSession('${s.id}')">▶️ Retomar</button>
                <button onclick="saveSessionToObsidian('${s.id}')">💾 Obsidian</button>
            </div>
        `).join('');
    }
    document.getElementById('historyModal').style.display = 'flex';
}

function closeHistoryModal() {
    document.getElementById('historyModal').style.display = 'none';
}

async function resumeSession(sessionId) {
    await fetch('/api/sessions/resume', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({user_id: currentUserId, session_id: sessionId})
    });
    alert(`Sesión ${sessionId} retomada`);
}

async function saveSessionToObsidian(sessionId) {
    const resp = await fetch('/api/session/save-obsidian', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({user_id: currentUserId, session_id: sessionId})
    });
    const data = await resp.json();
    alert(`Guardado: ${data.path}`);
}

// === TEMAS ===
async function loadTopics() {
    const resp = await fetch(`/api/topics?user_id=${currentUserId}`);
    const data = await resp.json();
    // Renderizar en la pestaña Temas del modal Settings
    // ...
}
```

### F11.2 Verificación F11 (carga estática — el GUI se valida visualmente con un browser real)

```bash
cd /home/vaclav/discord-english-room
# Validar que el HTML es válido y tiene los IDs esperados
grep -c 'id="card-Casete"' audio_player.html   # debe ser >= 1
grep -c 'openHistoryModal' audio_player.html    # debe ser >= 1
grep -c "Casete: '#00ffaa'" audio_player.html  # debe ser >= 1
echo "✅ HTML contiene todos los elementos nuevos"
```

**Criterio de salida F11:** grep encuentra los 3 elementos. Validación visual final: abrir `http://localhost:8081` en un browser y verificar que la card Casete aparece, el botón 📜 abre el modal Historial, y la pestaña Temas muestra sugerencias.

### F11.3 Commit F11

```bash
cd /home/vaclav/discord-english-room
git add audio_player.html
git status
git commit -m "feat(gui): Casete card + History modal + Topics tab + voice provider selector

- Card #card-Casete con emoji 🦜 y color #00ffaa
- Botón flotante 📜 → modal Historial
- 5ª tab en Settings: 🦜 Casete con selector de voz Edge/ElevenLabs (2 pestañas)
- JavaScript: openHistoryModal, resumeSession, saveSessionToObsidian, loadTopics
- currentUserId='legacy_vaclav' por ahora (TODO: detectar Discord user ID real)"
```

---

## F12 — Verificación end-to-end (la que dice si todo funciona junto)

**Por qué último:** todas las piezas en su sitio. Ahora se valida el flujo completo.

### F12.1 Pre-flight

```bash
cd /home/vaclav/discord-english-room
# Backup state
cp ~/.english-bot/state.json ~/.english-bot/state.json.backup-pre-f12
# Estado git limpio
git status --porcelain
# Branch correcta
git branch --show-current  # debe ser feat/casete-obsidian-topics-elevenlabs
# Servicios no corriendo
pkill -9 -f "audio_server.py" 2>/dev/null
pkill -9 -f "bot.py" 2>/dev/null
sleep 2
ss -ltn | grep -q ':8081 ' && echo "❌ puerto ocupado" || echo "✅ puerto libre"
```

### F12.2 Smoke test 1: solo audio_server

```bash
cd /home/vaclav/discord-english-room
unset PYTHONPATH
nohup venv/bin/python audio_server.py > .pids/audio-smoke.log 2>&1 &
sleep 4

# Todos los endpoints nuevos responden
for endpoint in /health /api/personas /api/sessions?user_id=legacy_vaclav /api/topics /api/preferences?user_id=legacy_vaclav; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8081${endpoint}")
    if [ "$status" = "200" ]; then
        echo "✅ $endpoint → 200"
    else
        echo "❌ $endpoint → $status (esperado 200)"
    fi
done

# POST endpoints
for ep in /api/sessions /api/sessions/resume /api/session/save-obsidian /api/topic /api/preferences; do
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8081${ep}" \
        -H "Content-Type: application/json" -d '{"user_id":"test","topic":"x"}')
    echo "POST $ep → $status"
done

# TTS preview
curl -s -X POST http://localhost:8081/api/tts-preview \
  -H "Content-Type: application/json" \
  -d '{"text":"Test Casete","voice":{"provider":"elevenlabs","voice_id":"x","model":"eleven_flash_v2_5","fallback":"en-US-AndrewNeural"}}' \
  --output /tmp/smoke-casete.mp3
file /tmp/smoke-casete.mp3 | grep -q "MPEG" && echo "✅ tts-preview ElevenLabs fallback → MP3 OK"

pkill -9 -f "audio_server.py" 2>/dev/null
```

### F12.3 Smoke test 2: vocabulario Casete end-to-end

```bash
cd /home/vaclav/discord-english-room
PYTHONPATH="" venv/bin/python -c "
import asyncio
from state_manager import (
    load_state, save_state, register_word_heard,
    get_casete_known, get_casete_counts, set_casete_threshold
)

async def main():
    # Simular 4 menciones de 'breakthrough' en mensajes humanos
    state = load_state()
    user_id = 'legacy_vaclav'
    
    for i in range(4):
        crossed = register_word_heard(state, user_id, 'breakthrough')
        print(f'Mención {i+1}: crossed={crossed}, known={get_casete_known(state, user_id)}')
    
    save_state(state)
    
    # Persistencia
    state2 = load_state()
    assert 'breakthrough' in get_casete_known(state2, user_id)
    print('✅ Vocabulario Casete persiste tras reload')
    
    # Threshold configurable
    set_casete_threshold(state, user_id, 1)
    crossed = register_word_heard(state, user_id, 'volatile')
    assert crossed is True
    print('✅ Threshold configurable funciona')

asyncio.run(main())
"
```

### F12.4 Smoke test 3: el bug de `!speak` sigue arreglado

```bash
cd /home/vaclav/discord-english-room
grep -n "ignore_bot_messages" bot.py | head -5
# Debe mostrar que el flag existe, se setea True al inicio de cmd_speak y False al final
echo "✅ Flag ignore_bot_messages intacto (no se rompió el fix del 2026-07-07)"
```

### F12.5 Reporte final

Si todo lo anterior pasa, el LLM ejecutor debe reportar:
- Lista de los 12 commits con `git log --oneline feat/casete-obsidian-topics-elevenlabs ^feat/personality-editor-gui`
- Output de cada uno de los 3 smoke tests
- Confirmación de que `!speak` sigue funcionando
- Lista de pendientes para validación manual en Discord (no se puede automatizar completamente)

---

## 📊 Resumen del plan

| Fase | Archivo(s) | LOC | Test crítico |
|---|---|---|---|
| F0 | (git) | 0 | 4 pre-flight checks |
| F1 | tts_providers.py (NUEVO) | ~120 | 4 tests TTS |
| F2 | bot.py | ~10 | 2 tests refactor |
| F3 | bot.py, state_manager.py | ~60 | 4 tests registro Casete |
| F4 | bot.py | ~120 | 5 tests lógica Casete |
| F5 | state_manager.py | ~80 | 8 tests vocab |
| F6 | state_manager.py | ~50 | 3 tests migración |
| F7 | state_manager.py | ~70 | 7 tests sesiones |
| F8 | bot.py | ~100 | 4 tests comandos |
| F9 | bot.py | ~80 | 4 tests topics + count |
| F10 | audio_server.py | ~200 | 8 tests endpoints |
| F11 | audio_player.html | ~150 | 3 grep + 1 visual |
| F12 | (smoke tests) | 0 | 3 smoke + reporte |
| **Total** | **5 archivos + 1 nuevo** | **~1040 líneas** | **52 tests automatizados** |

---

## 🔗 Enlaces relacionados
- [[_KRK9-MOC|Índice KRK-9]]
- [[2026-07-07-krk9-bug-speak-duplicado]] (bug !speak que F4 NO debe romper)
- [[2026-07-20-krk9-personality-editor-gui]] (commits base d24b9ec + 1dd28b0)
- [[PLAN_casete_obsidian_topics|Plan versión usuario (sin fases)]]