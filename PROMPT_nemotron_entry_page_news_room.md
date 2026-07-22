# PROMPT DE CONSTRUCCIÓN — Entry Page + News Room + Asistente KRK-9

> **Para**: LLM ejecutor de nivel medio (Nemotron Ultra 3 550B o similar)
> **Basado en**: `PROMPT_entry_page_news_room_assistant.md` (versión avanzada) — esta versión es **simplificada y con decisiones ya tomadas**. NO improvises arquitectura. El documento avanzado es solo orientación; si algo aquí contradice al documento avanzado, **ESTE documento gana**.
> **Repo**: `/home/vaclav/discord-english-room`
> **Rama base**: `feat/casete-obsidian-topics-elevenlabs` (HEAD `46b3363`, pusheada a `github.com:vaseksindelaru/lenguage-room.git`)
> **Rama nueva**: `feat/entry-page-news-room-assistant`

---

## ⛔ META-INSTRUCCIONES (léelas antes de escribir una línea)

1. **Trabaja FASE POR FASE.** No pases a la fase siguiente hasta que la verificación de la actual imprima `✅`. Si falla, para y reporta.
2. **No diseñes.** Las decisiones de arquitectura YA están tomadas abajo. Tu trabajo es escribir el código que se te indica.
3. **No fabriques output.** Si un test falla, pega el error real. Nunca digas "debería funcionar".
4. **No re-arquitectures lo existente.** El bot actual funciona. Solo AÑADES cosas nuevas.
5. **Commits pre-escritos.** Usa los mensajes de commit que te doy en cada fase, tal cual.

---

## 🔧 REGLAS DE ENTORNO (hard rules, errores reales que ya ocurrieron)

```bash
# ANTES de cualquier python/pip, SIEMPRE:
cd /home/vaclav/discord-english-room && unset PYTHONPATH
# Python correcto: venv/bin/python (NUNCA "python3" a secas)
```

**⚠️ ERRORES REALES QUE YA COMETIMOS HOY — no los repitas:**

| # | Error real | Lección |
|---|---|---|
| 1 | `youtube-transcript-api` cambió API: `get_transcript()` ya no existe en v1.2.4 | **Las librerías cambian de API.** Antes de usar una función de librería, verifica con `venv/bin/python -c "from lib import x; print(dir(x))"` |
| 2 | `audio_server.py` lee el webhook de `/tmp/discord_voice_webhook.txt` UNA VEZ al arrancar → si arranca antes que `bot.py`, queda `None` | **ORDEN DE ARRANQUE OBLIGATORIO: bot.py PRIMERO, esperar 10s, audio_server DESPUÉS** |
| 3 | Casete vocab se escribía en `state["casete_vocab"][uid]` pero se leía de `state["users"][uid]["casete_vocab"]` → contador siempre 0 | **UNA SOLA ubicación de verdad para cada dato.** En este proyecto los datos por usuario viven en `state["users"][uid][...]` |
| 4 | `en-US-TonyNeural` no existe en Edge TTS → TTS devolvía "No audio" | **Verifica nombres de voz contra `EDGE_VOICES` en `tts_providers.py` antes de usar uno nuevo** |
| 5 | Reiniciar audio_server para cambios de HTML/CSS es innecesario (el navegador recarga con Ctrl+F5) | **Solo reinicia servicios si tocas `.py`. HTML/CSS/JS → solo refrescar navegador** |

---

## 🎯 DECISIONES YA TOMADAS (no las cuestiones, impleméntalas)

El documento avanzado proponía cosas complejas. Para ti se simplifican así:

| Documento avanzado | ⭐ Decisión simplificada PARA TI |
|---|---|
| WebSocket bidireccional para el asistente con streaming | **REST simple: POST `/api/assistant/chat` → respuesta completa (sin streaming, sin SSE)** |
| APScheduler con CronTrigger | **asyncio task simple: loop que cada 60s mira la hora; si `hora == update_hour` y no corrió hoy → genera briefing** |
| Pydantic / dataclasses para schemas | **Dicts planos + función `validate_*()` que devuelve el dict o lanza ValueError** |
| VAD (hands-free) con detección de silencio | **PTT (mantener pulsado) como default. VAD queda para fase opcional final** |
| Drag-drop en settings de salas | **Lista simple con botones: [⬆] [⬇] [✏️] [🗑]** |
| Meeting organizer automático | **Botón manual "🤝 Proponer reunión" que envía un mensaje fijo al canal de Discord invitando a 2 bots expertos** |
| Interruptibilidad del briefing en tiempo real | **El briefing se muestra por secciones colapsables; "interrumpir" = botón "❓ Preguntar sobre esto" que manda la sección al chat del asistente** |
| 12 commits | **8 commits (8 fases)** |

---

## F0 — PRE-FLIGHT (obligatorio, 5 min)

Ejecuta y verifica cada línea:

```bash
cd /home/vaclav/discord-english-room
unset PYTHONPATH
git rev-parse --abbrev-ref HEAD          # esperado: feat/casete-obsidian-topics-elevenlabs
git status --porcelain                   # esperado: VACÍO (nada)
git log --oneline -1                     # esperado: 46b3363
ls bot.py audio_server.py audio_player.html state_manager.py tts_providers.py personas.json
test -f /tmp/discord_voice_webhook.txt && echo "webhook file OK" || echo "webhook file FALTA (el bot creará uno al arrancar)"
```

Si `git status` NO está vacío: `git add -A && git commit -m "WIP before entry-page-news-room-assistant"`

```bash
git checkout -b feat/entry-page-news-room-assistant
```

**✅ Salida esperada**: rama nueva activa. Reporta el output de cada comando.

---

## F1 — STATE v3: salas y config del asistente (solo `state_manager.py`)

### Objetivo
Añadir a cada usuario una lista `rooms[]` y un dict `assistant_config`, con migración automática.

### Paso 1.1 — En `state_manager.py`, sube `DEFAULT_STATE` de versión

Localiza `DEFAULT_STATE` (cerca de L17). Cambia `"version": 2` por `"version": 3` si existe la clave; si no existe, añádela.

### Paso 1.2 — Defaults nuevos (copia tal cual)

Añade tras `DEFAULT_STATE`:

```python
DEFAULT_ASSISTANT_CONFIG = {
    "enabled": True,
    "voice_mode": "ptt",          # "ptt" | "off"  (vad = fase opcional, NO ahora)
    "language": "en-US",
    "max_tokens": 400,
    "interruptible": True,
}

DEFAULT_NEWS_CONFIG = {
    "enabled": True,
    "update_hour": 4,             # 4am
    "timezone": "local",          # hora local del servidor
    "sources": [
        {"id": "hn",   "type": "rss", "name": "Hacker News", "url": "https://hnrss.org/frontpage", "enabled": True},
        {"id": "arstechnica-ai", "type": "rss", "name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "enabled": True},
    ],
    "max_items": 6,
    "last_run_date": None,        # "YYYY-MM-DD" cuando corrió por última vez
}

def default_rooms() -> list:
    """Salas por defecto de un usuario nuevo o migrado."""
    return [
        {"id": "conversation", "type": "conversation", "name": "English Practice", "enabled": True},
        {"id": "news",         "type": "news",         "name": "Morning Briefing", "enabled": True,
         "config": dict(DEFAULT_NEWS_CONFIG)},
    ]
```

### Paso 1.3 — Migración v2→v3 (copia tal cual, ponla junto a `migrate_state_v1_to_v2`)

```python
def migrate_state_v2_to_v3(state):
    """Añade rooms[] y assistant_config a cada usuario. Idempotente."""
    if state.get("version", 1) >= 3:
        return state
    state["version"] = 3
    for uid, user in state.setdefault("users", {}).items():
        user.setdefault("rooms", default_rooms())
        user.setdefault("assistant_config", dict(DEFAULT_ASSISTANT_CONFIG))
        user.setdefault("news_queue", [])
        user.setdefault("news_history", [])
    logger.info("🔄 Migrated state v2 → v3 (rooms + assistant_config)")
    return state
```

Y en `load_state()`, después de la llamada a `migrate_state_v1_to_v2(state)` añade:

```python
state = migrate_state_v2_to_v3(state)
```

(Hazlo en los DOS puntos de retorno de `load_state`: el try y el except.)

### Paso 1.4 — Funciones de acceso (copia tal cual)

```python
def get_user_rooms(state, uid):
    return state.get("users", {}).get(uid, {}).get("rooms", [])

def set_active_room(state, uid, room_id):
    user = state.get("users", {}).get(uid, {})
    if any(r.get("id") == room_id for r in user.get("rooms", [])):
        user["active_room"] = room_id
        return True
    return False

def get_assistant_config(state, uid):
    cfg = state.get("users", {}).get(uid, {}).get("assistant_config", {})
    out = dict(DEFAULT_ASSISTANT_CONFIG)
    out.update(cfg)
    return out

def get_news_config(state, uid):
    """Config de la sala 'news' del usuario (o defaults si no existe)."""
    for r in get_user_rooms(state, uid):
        if r.get("type") == "news":
            cfg = dict(DEFAULT_NEWS_CONFIG)
            cfg.update(r.get("config", {}))
            return cfg
    return dict(DEFAULT_NEWS_CONFIG)

def save_news_config(state, uid, new_config):
    user = state.get("users", {}).get(uid, {})
    for r in user.get("rooms", []):
        if r.get("type") == "news":
            r.setdefault("config", {}).update(new_config)
            return True
    return False
```

### Verificación F1 (imprime esto; deben salir 4 líneas ✅)

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH && venv/bin/python -c "
from state_manager import load_state, get_user_rooms, get_assistant_config, get_news_config
s = load_state()
assert s['version'] == 3, f'version {s.get(\"version\")}'
print('✅ 1/4 version=3')
uid = list(s['users'].keys())[0]
rooms = get_user_rooms(s, uid)
assert any(r['type'] == 'news' for r in rooms), 'falta sala news'
print('✅ 2/4 rooms con news')
assert get_assistant_config(s, uid)['voice_mode'] == 'ptt'
print('✅ 3/4 assistant_config ptt default')
assert get_news_config(s, uid)['update_hour'] == 4
print('✅ 4/4 news update_hour=4')
"
```

### Commit F1
```bash
git add state_manager.py
git commit -m "feat(state): v3 rooms + assistant_config + news_config with auto-migration"
```

---

## F2 — ENTRY PAGE (HTML/JS estático + API mínima)

### Objetivo
`http://localhost:8081/` muestra una **landing con cards de salas**, NO el chat. El chat actual se mueve a `http://localhost:8081/chat`.

### Paso 2.1 — Mover el chat actual

En `audio_server.py`, localiza `index_handler` (el que sirve `audio_player.html`). Cámbialo así (copia tal cual):

```python
async def index_handler(request):
    """Entry page: landing con cards de salas."""
    return web.FileResponse("./entry_page.html")

async def chat_handler(request):
    """Sala de conversación (la GUI existente)."""
    return web.FileResponse("./audio_player.html")
```

Y en el registro de rutas (`start_audio_server`), cambia:

```python
app.router.add_get('/', index_handler)
app.router.add_get('/chat', chat_handler)
```

### Paso 2.2 — Endpoint de salas (copia tal cual, añade junto a los otros handlers)

```python
async def rooms_get_handler(request):
    """GET /api/rooms?user_id=<uid> — lista salas del usuario."""
    from state_manager import load_state, get_user_rooms
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    return web.json_response({"rooms": get_user_rooms(state, uid)})
```

Regístrala: `app.router.add_get('/api/rooms', rooms_get_handler)`

### Paso 2.3 — `entry_page.html` (archivo NUEVO, copia tal cual COMPLETO)

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KRK-9 — Salas</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; padding: 24px; }
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
  h1 { color: #5865f2; font-size: 1.5rem; }
  .rooms { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; max-width: 1000px; }
  .card { background: #16213e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 24px; cursor: pointer; transition: all .2s; }
  .card:hover { border-color: #5865f2; transform: translateY(-2px); }
  .card h2 { font-size: 1.1rem; margin-bottom: 8px; }
  .card p { font-size: .85rem; color: #999; }
  .card .emoji { font-size: 2rem; margin-bottom: 12px; }
  .card.disabled { opacity: .4; cursor: not-allowed; }
  #assistant-fab { position: fixed; bottom: 20px; right: 20px; width: 56px; height: 56px; border-radius: 50%;
    background: #5865f2; border: none; font-size: 1.6rem; cursor: pointer; z-index: 999; }
</style>
</head>
<body>
<header>
  <h1>🎧 KRK-9</h1>
  <span id="user">Vaclav</span>
</header>

<div class="rooms" id="rooms"></div>

<button id="assistant-fab" title="Asistente KRK-9" onclick="location.href='/assistant'">🤖</button>

<script>
const USER_ID = 'legacy_vaclav';   // TODO futuro: usuario real por login
const ROOM_ICONS = { conversation: '💬', news: '📰', assistant: '🤖', custom: '🛠' };
const ROOM_ROUTES = { conversation: '/chat', news: '/news', assistant: '/assistant' };

async function load() {
  const r = await fetch(`/api/rooms?user_id=${USER_ID}`);
  const data = await r.json();
  const grid = document.getElementById('rooms');
  grid.innerHTML = '';
  for (const room of data.rooms) {
    const div = document.createElement('div');
    div.className = 'card' + (room.enabled === false ? ' disabled' : '');
    div.innerHTML = `<div class="emoji">${ROOM_ICONS[room.type] || '🛠'}</div>
                     <h2>${room.name}</h2><p>${room.type}</p>`;
    if (room.enabled !== false && ROOM_ROUTES[room.type]) {
      div.onclick = () => location.href = ROOM_ROUTES[room.type];
    }
    grid.appendChild(div);
  }
}
load();
</script>
</body>
</html>
```

### Verificación F2

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
# arrancar SOLO audio_server para probar (el bot no hace falta para HTML)
venv/bin/python audio_server.py & sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/         && echo " ✅ / (entry)"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/chat     && echo " ✅ /chat"
curl -s "http://localhost:8081/api/rooms?user_id=legacy_vaclav" | grep -q '"type": "news"' && echo "✅ rooms API tiene news"
kill %1 2>/dev/null
```

Las 3 líneas deben imprimir `200 ✅` / `200 ✅` / `✅ rooms API tiene news`.

### Commit F2
```bash
git add entry_page.html audio_server.py
git commit -m "feat(entry): landing page with room cards; chat moved to /chat"
```

---

## F3 — NEWS: fetch + resumen (SIN scheduler todavía)

### Objetivo
Un módulo `news_room.py` con `generate_briefing(uid)` que: descarga RSS → resume con el LLM del bot → guarda markdown en state. Se prueba a mano. El cron viene en F4.

### Paso 3.1 — Dependencia

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
venv/bin/pip install feedparser 2>&1 | tail -1
```

### Paso 3.2 — `news_room.py` (archivo NUEVO, copia COMPLETO)

```python
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
        "## ✅ Suggested Tasks\n(3 checkboxes accionables relacionados con las noticias)\n\n"
        "Noticias de hoy:\n" + "\n\n".join(lines)
    )

async def generate_briefing(uid: str) -> str:
    """Genera y guarda el briefing del usuario. Devuelve el markdown."""
    from state_manager import load_state, save_state, get_news_config
    from bot import call_openrouter   # reusar el router LLM existente

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
```

### Paso 3.3 — Endpoints en `audio_server.py` (copia tal cual)

```python
async def news_briefing_handler(request):
    """GET /api/news/briefing?user_id=<uid> — último briefing (o genera si no hay de hoy)."""
    from state_manager import load_state
    uid = request.query.get("user_id", "legacy_vaclav")
    state = load_state()
    history = state.get("users", {}).get(uid, {}).get("news_history", [])
    today = datetime.now().strftime("%Y-%m-%d")
    if history and history[0]["date"].startswith(today):
        return web.json_response({"briefing": history[0]["markdown"], "cached": True})
    return web.json_response({"briefing": None, "cached": False,
                              "message": "No hay briefing de hoy. Usa POST /api/news/refresh."})

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
```

Registrar:
```python
app.router.add_get('/api/news/briefing', news_briefing_handler)
app.router.add_post('/api/news/refresh', news_refresh_handler)
```

### Paso 3.4 — Página `/news` (copia COMPLETO como `news_page.html`)

```html
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📰 Morning Briefing</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
 body{font-family:'Inter',sans-serif;background:#1a1a2e;color:#eee;padding:24px;max-width:800px;margin:auto}
 h1{color:#5865f2;font-size:1.4rem;margin-bottom:16px}
 #briefing{background:#16213e;border:1px solid #2a2a4a;border-radius:12px;padding:24px;line-height:1.6;white-space:pre-wrap}
 button{background:#5865f2;color:#fff;border:none;border-radius:8px;padding:10px 20px;cursor:pointer;font-weight:600;margin:8px 8px 16px 0}
 a{color:#8ea1e1}
</style></head><body>
<h1>📰 Morning Briefing</h1>
<button onclick="refreshBriefing()">🔄 Generar ahora</button>
<button onclick="location.href='/'">← Salas</button>
<div id="briefing">Cargando…</div>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
const USER_ID = 'legacy_vaclav';
async function loadBriefing(){
  const r = await fetch(`/api/news/briefing?user_id=${USER_ID}`);
  const d = await r.json();
  document.getElementById('briefing').innerHTML = d.briefing ? marked.parse(d.briefing) : '<p>No hay briefing de hoy. Pulsa "Generar ahora".</p>';
}
async function refreshBriefing(){
  document.getElementById('briefing').textContent = '⏳ Generando (puede tardar 30-60s)…';
  const r = await fetch('/api/news/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:USER_ID})});
  const d = await r.json();
  document.getElementById('briefing').innerHTML = d.briefing ? marked.parse(d.briefing) : '❌ ' + (d.error||'error');
}
loadBriefing();
</script></body></html>
```

Y en `audio_server.py` añade la ruta: `app.router.add_get('/news', lambda r: web.FileResponse('./news_page.html'))`

### Verificación F3

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
venv/bin/python news_room.py legacy_vaclav | head -20     # debe imprimir markdown del briefing
# luego con server:
venv/bin/python audio_server.py & sleep 4
curl -s -X POST http://localhost:8081/api/news/refresh -H "Content-Type: application/json" -d '{"user_id":"legacy_vaclav"}' | head -c 300 && echo "" && echo "✅ refresh endpoint OK"
kill %1 2>/dev/null
```

### Commit F3
```bash
git add news_room.py news_page.html audio_server.py
git commit -m "feat(news): RSS briefing generator + /news page + refresh endpoint"
```

---

## F4 — NEWS: scheduler simple (sin APScheduler)

### Objetivo
Un loop asyncio dentro de `bot.py` que cada 60 segundos mira si ya son las `update_hour` y si hoy no corrió; si toca, llama `generate_briefing` para cada usuario.

### Paso 4.1 — En `bot.py`, añade esta task (copia tal cual, junto a las otras tasks)

```python
@tasks.loop(seconds=60)
async def news_scheduler_loop():
    """Cada minuto mira si toca generar el briefing matutino de algún usuario."""
    try:
        from state_manager import load_state, get_news_config
        from news_room import generate_briefing
        now = datetime.now()
        today = f"{now:%Y-%m-%d}"
        state = load_state()
        for uid in list(state.get("users", {}).keys()):
            cfg = get_news_config(state, uid)
            if not cfg.get("enabled", True):
                continue
            if now.hour != cfg.get("update_hour", 4):
                continue
            if cfg.get("last_run_date") == today:
                continue
            logger.info(f"📰 {now:%H:%M} — generando briefing diario para {uid}")
            await generate_briefing(uid)
    except Exception as e:
        logger.error(f"❌ news_scheduler_loop: {e}")
```

### Paso 4.2 — Arráncala donde arrancan las demás tasks

Busca en `bot.py` dónde se inicia `conversation_loop` (en `on_ready` o `setup_hook`). Añade junto a ella:

```python
if not news_scheduler_loop.is_running():
    news_scheduler_loop.start()
```

### Verificación F4 (sin esperar a las 4am)

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH && venv/bin/python -c "
# Simular: cambiar update_hour a la hora actual y last_run_date a ayer
from state_manager import load_state, save_state, save_news_config
from datetime import datetime
s = load_state()
save_news_config(s, 'legacy_vaclav', {'update_hour': datetime.now().hour, 'last_run_date': '2000-01-01'})
save_state(s)
print('✅ config forzada: update_hour =', datetime.now().hour)
# Ahora en el próximo minuto el scheduler la generaría. Comprueba la lógica importando:
from bot import news_scheduler_loop
print('✅ news_scheduler_loop importable:', callable(new_scheduler_loop) if False else True)
"
```

(No ejecutes el bot entero solo para esto: basta con que el import no falle y el `python -m py_compile bot.py` pase.)

### Commit F4
```bash
git add bot.py
git commit -m "feat(news): simple 60s scheduler loop for daily briefing at update_hour"
```

---

## F5 — ASISTENTE KRK-9 (REST simple, sin streaming)

### Objetivo
`POST /api/assistant/chat {user_id, message}` → respuesta de texto completa. El asistente ve el briefing y el historial. Nada de WebSocket ni streaming.

### Paso 5.1 — `krk9_assistant.py` (NUEVO, copia COMPLETO)

```python
"""Asistente KRK-9: chat REST con contexto de briefing + historial."""
import logging
from datetime import datetime

logger = logging.getLogger("krk9_assistant")

SYSTEM = (
    "You are KRK-9, Vaclav's personal assistant inside his English practice app. "
    "You know his news briefing, his English practice sessions, and his vocabulary progress. "
    "Be concise (max 3 sentences unless asked for detail), warm, and practical. "
    "If he asks about the news, use the briefing context provided. "
    "If asked to do something you cannot do, say so plainly."
)

async def assistant_reply(uid: str, message: str) -> str:
    from state_manager import load_state, get_assistant_config
    from bot import call_openrouter

    state = load_state()
    cfg = get_assistant_config(state, uid)
    if not cfg.get("enabled", True):
        return "(Assistant disabled in settings)"

    user = state.get("users", {}).get(uid, {})
    briefing = user.get("news_history", [{}])[0].get("markdown", "(no briefing yet)")[:1200]
    sessions = user.get("sessions", [])
    last_session = sessions[-1]["topic"] if sessions else "(none)"

    context = (f"Latest briefing (may be old):\n{briefing}\n\n"
               f"Last practice session topic: {last_session}")

    try:
        reply = await call_openrouter(
            [{"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER MESSAGE: {message}"}],
            system=SYSTEM,
            temperature=0.7,
        )
        return reply or "(empty reply)"
    except Exception as e:
        logger.error(f"❌ assistant_reply: {e}")
        return "Sorry, my brain is not available right now. Try again in a moment."
```

### Paso 5.2 — Endpoint en `audio_server.py`

```python
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
```

Registrar: `app.router.add_post('/api/assistant/chat', assistant_chat_handler)`

### Verificación F5

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
venv/bin/python audio_server.py & sleep 4
curl -s -X POST http://localhost:8081/api/assistant/chat -H "Content-Type: application/json" \
  -d '{"user_id":"legacy_vaclav","message":"What is in my briefing today?"}' | head -c 400
kill %1 2>/dev/null
```

Debe devolver JSON con `reply` (texto del LLM o mensaje de fallback).

### Commit F5
```bash
git add krk9_assistant.py audio_server.py
git commit -m "feat(assistant): KRK-9 REST chat with briefing + session context"
```

---

## F6 — ASISTENTE: ventana en GUI (collapsible, chat simple)

### Objetivo
`http://localhost:8081/assistant` muestra una ventana de chat con KRK-9. Además, un botón flotante 🤖 en `/` (entry) y `/chat` lleva ahí.

### Paso 6.1 — `assistant_page.html` (NUEVO, copia COMPLETO)

```html
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 KRK-9 Assistant</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
 body{font-family:'Inter',sans-serif;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;height:100vh;margin:0}
 header{padding:12px 20px;background:#16213e;border-bottom:1px solid #2a2a4a;display:flex;justify-content:space-between;align-items:center}
 h1{color:#5865f2;font-size:1.1rem}
 #msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:10px}
 .msg{max-width:75%;padding:10px 14px;border-radius:12px;line-height:1.45;white-space:pre-wrap}
 .msg.user{align-self:flex-end;background:#5865f2;color:#fff}
 .msg.bot{align-self:flex-start;background:#16213e;border:1px solid #2a2a4a}
 #inputrow{display:flex;gap:8px;padding:12px 20px;background:#16213e;border-top:1px solid #2a2a4a}
 input{flex:1;background:#0f0f1a;border:1px solid #2a2a4a;border-radius:8px;color:#eee;padding:10px 14px;font-size:.95rem}
 button{background:#5865f2;color:#fff;border:none;border-radius:8px;padding:10px 18px;cursor:pointer;font-weight:600}
 #ptt{background:#3a3a5a}
</style></head><body>
<header><h1>🤖 KRK-9 Assistant</h1><button onclick="location.href='/'">← Salas</button></header>
<div id="msgs"></div>
<div id="inputrow">
  <button id="ptt" title="Mantén para hablar">🎤</button>
  <input id="txt" placeholder="Escribe o mantén 🎤 para hablar…" autofocus>
  <button onclick="send()">Enviar</button>
</div>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
const USER_ID='legacy_vaclav';
const msgs=document.getElementById('msgs'), txt=document.getElementById('txt');
function add(role,text){const d=document.createElement('div');d.className='msg '+role;d.innerHTML=marked.parse(text);msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;return d;}
async function send(){
  const m=txt.value.trim(); if(!m) return; txt.value='';
  add('user',m); const thinking=add('bot','⏳…');
  try{
    const r=await fetch('/api/assistant/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:USER_ID,message:m})});
    const d=await r.json(); thinking.innerHTML=marked.parse(d.reply||('❌ '+(d.error||'error')));
  }catch(e){thinking.textContent='❌ conexión';}
}
txt.addEventListener('keydown',e=>{if(e.key==='Enter')send();});

/* PTT: usa Web Speech API igual que /chat */
let rec=null;
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){
  rec=new SR(); rec.lang='en-US'; rec.interimResults=false;
  rec.onresult=e=>{txt.value=e.results[0][0].transcript;send();};
  const ptt=document.getElementById('ptt');
  ptt.onmousedown=()=>{try{rec.start();ptt.textContent='🔴';}catch(_){}};
  ptt.onmouseup=()=>{try{rec.stop();ptt.textContent='🎤';}catch(_){}};
}else{document.getElementById('ptt').style.display='none';}

add('bot','¡Hola! Soy KRK-9. Puedo resumirte tu briefing, hablar de tu práctica de inglés o responder preguntas. ¿En qué te ayudo?');
</script></body></html>
```

### Paso 6.2 — Ruta en `audio_server.py`

```python
app.router.add_get('/assistant', lambda r: web.FileResponse('./assistant_page.html'))
```

### Verificación F6

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
venv/bin/python audio_server.py & sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/assistant && echo " ✅ /assistant carga"
kill %1 2>/dev/null
```

Luego abre `http://localhost:8081/assistant` en el navegador y escribe "hello" → debe responder el LLM.

### Commit F6
```bash
git add assistant_page.html audio_server.py
git commit -m "feat(assistant): chat window at /assistant with PTT mic button"
```

---

## F7 — VOZ: VAD opcional (hands-free experimental)

> **⭐ Esta fase es OPCIONAL.** Solo hazla si F1–F6 están ✅ y queda tiempo. Si algo falla aquí, revierte este commit y entrega sin VAD.

### Objetivo
En `/assistant`, un toggle "🗣 Hands-free" que active `SpeechRecognition.continuous = true` y envíe al terminar cada frase final.

### Paso 7.1 — En `assistant_page.html`, dentro del `<script>` tras el bloque PTT

```javascript
/* VAD experimental (hands-free) */
let vad=false, vadRec=null;
if(SR){
  vadRec=new SR(); vadRec.lang='en-US'; vadRec.continuous=true; vadRec.interimResults=false;
  vadRec.onresult=e=>{const t=e.results[e.results.length-1][0].transcript.trim(); if(t){txt.value=t;send();}};
  vadRec.onend=()=>{ if(vad){ try{vadRec.start();}catch(_){}} };
}
const vadBtn=document.createElement('button');
vadBtn.textContent='🗣 VAD: OFF'; vadBtn.id='vadbtn';
vadBtn.onclick=()=>{
  vad=!vad;
  vadBtn.textContent='🗣 VAD: '+(vad?'ON':'OFF');
  if(vad&&vadRec){try{vadRec.start();}catch(_){}} else if(vadRec){try{vadRec.stop();}catch(_){}}
};
document.getElementById('inputrow').prepend(vadBtn);
```

### Verificación F7
Manual en navegador: activar VAD → hablar una frase → debe enviarse sola al pausar.

### Commit F7
```bash
git add assistant_page.html
git commit -m "feat(assistant): optional hands-free VAD toggle (experimental)"
```

---

## F8 — VERIFICACIÓN END-TO-END + limpieza

```bash
cd /home/vaclav/discord-english-room && unset PYTHONPATH
# Orden OBLIGATORIO: bot primero, audio_server después (lección #2 de errores reales)
venv/bin/python bot.py & sleep 12
venv/bin/python audio_server.py & sleep 5

curl -s http://localhost:8081/health                          # {"status":"ok",...}
curl -s -o /dev/null -w "%{http_code} / (entry)\n"        http://localhost:8081/
curl -s -o /dev/null -w "%{http_code} /chat\n"            http://localhost:8081/chat
curl -s -o /dev/null -w "%{http_code} /news\n"            http://localhost:8081/news
curl -s -o /dev/null -w "%{http_code} /assistant\n"       http://localhost:8081/assistant
curl -s "http://localhost:8081/api/rooms?user_id=legacy_vaclav" | grep -q news && echo "✅ rooms"
curl -s -X POST http://localhost:8081/api/assistant/chat -H "Content-Type: application/json" -d '{"user_id":"legacy_vaclav","message":"hi"}' | grep -q reply && echo "✅ assistant"

grep -iE "error|traceback" .pids/bot.log | tail -5        # debe estar vacío o solo warnings conocidos
```

Reporta cada línea con su resultado real. Si alguna falla → para, reporta cuál, no sigas.

---

## 🚫 PROHIBIDO (si haces algo de esto, el trabajo se rechaza)

- ❌ No añadas Pydantic, AsyncIOScheduler, Celery, Redis ni bases de datos nuevas.
- ❌ No cambies `decide_next_agent`, el flag `ignore_bot_messages`, ni el flujo de `!speak`.
- ❌ No pongas el asistente como WebSocket (ya decidido: REST).
- ❌ No subas `update_hour` a cada usuario desde un proceso global distinto del loop de F4.
- ❌ No commitees `.env`, `personas.json`, `venv/`, `.pids/`, `__pycache__/`, `*.log`.
- ❌ No fabriques outputs de tests. Pega los reales.

---

## 📤 ENTREGA FINAL (qué reportas al usuario)

1. `git log --oneline feat/entry-page-news-room-assistant ^feat/casete-obsidian-topics-elevenlabs` (los 7-8 commits)
2. Output real de la verificación F8
3. Qué probaste manualmente en el navegador (con URLs)
4. Qué quedó fuera (VAD, etc.) y por qué

---

## 🔗 Referencias (lee solo si te atascas)

- `audio_player.html` — patrón de mic PTT + anti-echo (`recognition_blocked_until`)
- `tts_providers.py` — `EDGE_VOICES` válidos
- `bot.py` L267-414 — router LLM (`call_openrouter`)
- `state_manager.py` — patrón de escritura atómica + migraciones
