---
type: hermes-session
project: KRK-9
date: "2026-07-21"
tags:
  - proyecto/krk9
  - prompt
  - entry-page
  - news-room
  - assistant
title_original: "PROMPT para LLM avanzado: Entry Page + News Room + KRK-9 Assistant"
---

# PROMPT PARA LLM AVANZADO: Entry Page + News Room + KRK-9 Assistant

> **Propósito**: Implementar especificación completa en `/home/vaclav/discord-english-room`.
> **Rama base**: `feat/casete-obsidian-topics-elevenlabs` (HEAD = b30aa48).
> **Nueva rama**: `feat/entry-page-news-room-assistant`.

---

## 🎯 Objetivo General

Transformar KRK-9 de un **bot de conversación simple** a una **plataforma multi-sala** con:
1. **Entry Page (SPA)** — Landing page con cards de salas (Conversation, News Briefing, Assistant, Settings).
2. **News Room** — Briefing matutino tipo secretaria a las 4am (cron), fuentes RSS/Web, resumen LLM estilo secretaria, interruptible, meeting organizer.
3. **KRK-9 Assistant Persistente** — Ventana colapsable (Entry Page + Chat), modos PTT/VAD/Off, tools (schedule_meeting, web_search, get_briefing), streaming responses, interruptible.

---

## 🔧 Estado Actual del Repo (VERIFICADO)

```
Rama: feat/casete-obsidian-topics-elevenlabs
HEAD: b30aa48 fix(gui): anti-echo blocker for voice recognition
Commits por pushear: 2 (b30aa48, 3469113)
Cambios sin commitear: bot.py (modificado - !video command + logging)
Sin seguimiento: PLAN_casete_obsidian_topics.md
```

**Arquitectura actual**:
- `bot.py` — Discord bot + LLM router (Cerebras→Groq→OpenRouter→Ollama) + `!video` command + `!casete` + `!speak` + `!topic` + `!session` + `!preferences` + multi-user `on_message`
- `audio_server.py` — aiohttp + WebSocket (audio) + REST (personas, sessions, tts-preview, active-agents, preferences, topics)
- `audio_player.html` — SPA oscura, grid agents, mic PTT, anti-echo blocker (localStorage), settings modal (persona/voice/LLM)
- `state_manager.py` — `state.json` v2 (users[uid] con sessions[], casete_vocab, interests), atomic writes, thread-safe
- `personas.json` — 5 agentes (Alex, Maya, Jordan, Sam, Casete) con voice dict (Edge/ElevenLabs), llm_provider/model
- `persons.json` — NO existe aún (rooms, assistant_config vendrán en v3)

---

## 📋 ESPECIFICACIÓN COMPLETA (PARA EL LLM EJECUTOR)

### 1. STATE MANAGER v3 (`state_manager.py`)

**Nueva estructura `DEFAULT_STATE_V3`**:
```python
{
    "version": 3,
    "users": {
        "<uid>": {
            "name": "Vaclav",
            "rooms": [
                {"id": "uuid", "type": "conversation", "name": "English Practice", "config": {...}},
                {"id": "uuid", "type": "news", "name": "Morning Briefing", "config": NewsRoomConfig},
                {"id": "uuid", "type": "assistant", "name": "KRK-9", "config": AssistantConfig}
            ],
            "active_room": "<room_id>",
            "assistant_config": AssistantConfig,  # NUEVO
            "news_queue": [],       # Briefings generados pendientes
            "news_history": [],     # Briefings pasados (con markdown)
            "casete_vocab": {...},
            "sessions": [...],
            "interests": [...],
            "active_session": "..."
        }
    },
    "global": {...}  # conversation_history, etc. (compat)
}
```

**Nuevas funciones**:
```python
def get_user_rooms(state, uid) -> list
def set_active_room(state, uid, room_id) -> bool
def add_room(state, uid, room_type, name, config) -> str  # returns room_id
def update_room_config(state, uid, room_id, config) -> None
def get_assistant_config(state, uid) -> AssistantConfig
def set_assistant_config(state, uid, config) -> None
def append_news_briefing(state, uid, briefing) -> None
def get_news_history(state, uid, limit=30) -> list
```

**Migración idempotente**: `load_state()` detecta `version < 3` y crea estructura `users[uid].rooms[]` + `assistant_config` con defaults.

---

### 2. SCHEMAS / CONFIG (`schemas.py` NUEVO)

```python
@dataclass
class NewsRoomConfig:
    enabled: bool = True
    update_hour: int = 4          # 4am local
    timezone: str = "Europe/Madrid"
    sources: List[NewsSource] = field(default_factory=list)
    max_items_per_briefing: int = 8
    style: str = "secretary"      # secretary / bullet / narrative
    interruptible: bool = True
    meeting_proposals_enabled: bool = True

@dataclass
class NewsSource:
    id: str
    type: Literal["rss", "youtube", "web"]
    url: str
    name: str
    enabled: bool = True
    category: str = "ai"          # ai, tech, science, general

@dataclass
class AssistantConfig:
    enabled: bool = True
    voice_mode: Literal["ptt", "vad", "off"] = "ptt"
    language: str = "en-US"
    auto_listen_after_tts: bool = False
    tools_enabled: List[str] = field(default_factory=lambda: ["schedule_meeting", "web_search", "get_briefing"])
    personality: str = "helpful_secretary"  # helpful_secretary, technical_expert, casual_friend
    max_tokens_per_response: int = 500
    streaming: bool = True
    interruptible: bool = True
```

---

### 3. NEWS ROOM (`news_room.py` NUEVO)

**Componentes**:
- `NewsFetcher` — RSS (feedparser), YouTube (youtube-transcript-api), Web (requests + readability)
- `NewsSummarizer` — LLM prompt "secretary style" con secciones fijas
- `NewsScheduler` — `AsyncIOScheduler` (apscheduler), cron por usuario a `update_hour` en su `timezone`
- `MeetingOrganizer` — propone reuniones con bots expertos, crea evento, notifica

**Flujo briefing (4am cron)**:
1. Fetch sources → parse → filter duplicates (title hash)
2. LLM summarize (prompt: secretary style, 8 items max, sections: News, Recommendations, Tasks, Meeting Proposals)
3. Store en `users[uid].news_queue` + `news_history` (markdown con frontmatter)
4. Push WebSocket notification si usuario online

**Prompt secretary** (resumido):
```
Eres la secretaria ejecutiva de un ingeniero de IA. Genera un briefing matutino con:
1. Top 5 AI/Tech news (título, fuente, 1 párrafo, implicación técnica)
2. Recommendations (1 libro, 1 video, 1 paper) con "por qué ahora"
2. Tasks accionables (checkboxes)
3. Meeting proposals con bots expertos (Jordan=reasoning, Sam=code review, etc.)
Tono: eficiente, cálida, profesional. Formato markdown con frontmatter.
```

---

### 4. NEWS ENDPOINTS (`audio_server.py`)

```python
GET  /api/news/briefing?user_id=<uid>          # Briefing actual (markdown)
POST /api/news/refresh?user_id=<uid>           # Forzar regeneración
GET  /api/news/history?user_id=<uid>&limit=30
POST /api/news/interrupt                        # {user_id, question} → streaming response
POST /api/news/meeting/propose                  # {user_id, topic, experts} → crea reunión
GET  /api/news/sources?user_id=<uid>
POST /api/news/sources                          # Añadir fuente
DELETE /api/news/sources/<id>
```

---

### 5. ENTRY PAGE SPA (`entry_page.html` + `entry_page.js`)

**Rutas**:
- `/` → Entry Page (cards de salas)
- `/room/<room_id>` → Sala específica (conversation/news/assistant)

**Layout**:
```
Header: KRK-9 logo + user avatar + settings
Main: Grid 2x2/1x4 cards (responsive)
  Card Conversation → /room/<conv_id>
  Card News Briefing → /room/<news_id> (muestra último briefing preview)
  Card KRK-9 Assistant → /room/<assist_id>
  Card Settings → /settings
Footer: Version + links
```

**Assistant Window** (colapsable, persistente en `localStorage`):
- Header: 🤖 KRK-9 | voice mode select (PTT/VAD/Off) | config | toggle
- Messages: streaming bubbles, markdown, code blocks
- Input row: PTT btn (hold) | text input | send
- VAD mode: `SpeechRecognition.continuous + silence detection (800ms)`

---

### 6. KRK-9 ASSISTANT (`krk9_assistant.py` NUEVO)

```python
class KRK9Assistant:
    def __init__(self, state_manager, llm_router, news_room):
        self.state = state_manager
        self.llm = llm_router
        self.news = news_room
        self.tools = {
            "schedule_meeting": self._schedule_meeting,
            "web_search": self._web_search,
            "get_briefing": self._get_briefing,
            "set_reminder": self._set_reminder,
        }
    
    async def chat_stream(self, user_id: str, message: str, mode: str) -> AsyncGenerator[str, None]:
        # 1. Build context (history + briefing + assistant_config)
        # 2. LLM with tools (function calling)
        # 3. Stream tokens via WebSocket
        # 4. Handle tool calls → execute → feed back
        # 5. If mode=="vad" and interruption → cancel, process, resume
```

**Tools**:
- `schedule_meeting(topic, participants, duration_min)` → crea evento, notifica bots
- `web_search(query)` → duckduckgo/serpapi → summary
- `get_briefing()` → último briefing markdown
- `set_reminder(time, message)` → schedule

---

### 6. ASSISTANT WEBSOCKET (`audio_server.py`)

```
WS /ws/assistant?user_id=<uid>
  → frames: {"type": "token", "data": "..."} | {"type": "tool_call", "tool": "...", "args": {...}} | {"type": "tool_result", "tool": "...", "result": "..."} | {"type": "done"} | {"type": "error", "msg": "..."}
```

REST fallback:
```
POST /api/assistant/chat {user_id, message, mode} → streaming SSE
```

---

### 7. AUDIO PLAYER MODS (`audio_player.html`)

- Añadir modo VAD a selector de voz (PTT/VAD/Off)
- Mantener anti-echo `recognition_blocked_until` (ya en b30aa48)
- Integrar `krk9_assistant.js` para ventana asistente

---

### 7. STATE MIGRATION SCRIPT

```python
# scripts/migrate_state_v3.py
def migrate_v2_to_v3(state):
    if state.get("version", 1) >= 3: return state
    # Crear users[uid] con rooms[], assistant_config defaults
    # Migrar casete_vocab, sessions, interests a users[uid]
    state["version"] = 3
    return state
```

Ejecutar al primer `load_state()` post-deploy.

---

## 📁 ESTRUCTURA FINAL ESPERADA

```
discord-english-room/
├── bot.py                          # + imports news_room, logging commands
├── audio_server.py                 # + endpoints news, assistant, rooms
├── audio_player.html               # + VAD mode, assistant window
├── entry_page.html                 # NUEVO
├── entry_page.js                   # NUEVO
├── krk9_assistant.py               # NUEVO
├── news_room.py                    # NUEVO
├── state_manager.py                # + v3, rooms[], assistant_config
├── schemas.py                      # NUEVO (dataclasses)
├── personas.json                   # + NewsRoomConfig, AssistantConfig defaults
├── requirements.txt                # + apscheduler, feedparser, youtube-transcript-api
├── .env.example                    # + NEWS_API_KEY, RSS_FEEDS, SERPAPI_KEY
├── scripts/
│   └── migrate_state_v3.py
└── tests/
    ├── test_state_migration.py
    ├── test_news_fetcher.py
    └── test_assistant_tools.py
```

---

## 🚀 REGLAS DE ORO PARA EL LLM EJECUTOR

1. **Pre-flight**: `git status` → si dirty → `git add -A && git commit -m "WIP before entry-page-news-room"`
2. **Rama**: `git checkout -b feat/entry-page-news-room-assistant`
3. **Python**: `unset PYTHONPATH` antes de CUALQUIER `python`/`pip`
4. **NO inventes APIs**. Si dudas → `grep -n` / `read_file` en archivo existente.
5. **Commits atómicos** (12 sugeridos). Cada commit: `python -m py_compile <file>` + test `__main__`.
6. **Pre-commit checks**: `python -m py_compile bot.py audio_server.py state_manager.py`
7. **Verificación final**:
   ```bash
   ./start.sh --stop && ./start.sh && sleep 5
   curl -s http://localhost:8081/health  # {"status":"ok"}
   ```
8. **Reporte final**: diff stat, logs reales, qué probaste manualmente en Discord.

---

## ✅ CRITERIOS DE ACEPTACIÓN (Definition of Done)

| # | Feature | Test Auto | Test Manual |
|---|---|---|---|
| 1 | Entry Page carga sin chat | `GET /` → 200, no `.chat-container` | Abrir `http://localhost:8081` → grid cards |
| 2 | Cards dinámicas | `GET /api/rooms?user_id=test` → JSON válido | Crear 2 salas en Settings → aparecen |
| 3 | News Room 4am cron | Mock time → `generate_briefing()` ejecuta | `GET /api/news/briefing` → markdown válido |
| 4 | Briefing formato secretary | Markdown válido, secciones requeridas | Leer briefing → estilo secretaria |
| 5 | Briefing interruptible | `POST /api/news/interrupt` → streaming | Hablar durante briefing → KRK-9 responde y retoma |
| 6 | Meeting organizer | `POST /api/news/meeting/propose` → evento | KRK-9 propone reunión Jordan+Sam, bots notificados |
| 7 | Assistant colapsable | `localStorage` persiste estado | Recargar → asistente mantiene abierto/cerrado |
| 8 | PTT mode | `mousedown`→graba→`mouseup`→envía | Mantener 🎤 → hablar → soltar → transcribe |
| 9 | VAD mode | `SpeechRecognition` continuous + silence | Hablar sin botón → transcribe al pausar |
| 10 | Anti-echo | `recognition_blocked_until` funciona | Bot habla → mic bloqueado → no loop |
| 11 | State v3 migration | `load_state()` → version 3, rooms[] existe | Reiniciar → salas persisten |

---

## 🔗 ENLACES RELACIONADOS EN OBSIDIAN

- [[_KRK9-MOC|Índice KRK-9]]
- [[PLAN_casete_obsidian_topics|Plan Casete + Obsidian + Temas]]
- [[2026-07-21-krk9-casete-ui-multiusuario|Sesión Casete + UI Multiusuario]]
- [[2026-07-20-krk9-personality-editor-gui|Editor GUI Personalidad]]

---

*Generado: 2026-07-21 | Para: LLM avanzado (Claude 4 / Gemini 2.5 / GPT-5) | Rama base: feat/casete-obsidian-topics-elevenlabs@b30aa48*