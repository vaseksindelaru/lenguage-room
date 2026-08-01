---
type: hermes-session
project: KRK-9
date: "2026-07-21"
tags:
  - proyecto/krk9
  - youtube
  - !video-command
  - bugfix
  - multi-user
title_original: "KRK-9 — Comando !video YouTube + fixes anti-eco + bug vocab v2"
---

# KRK-9 — 2026-07-21 · Comando !video YouTube + Bugfixes

> [!info] Sesión de integración de YouTube + arreglos de bugs encontrados durante la prueba en vivo.

---

## 🎯 Trabajo realizado

### 1. Comando `!video <URL>` — YouTube como tema de conversación

Los bots pueden ahora discutir videos contigo. El usuario pega un link, el bot descarga la transcripción, y los agentes opinan en inglés sobre el contenido.

**Implementación** (bot.py L1505-1600):
- Instalada dep `youtube-transcript-api` (v1.2.4)
- Comando `@bot.command(name="video")` con extracción de video ID (soporta `watch?v=`, `youtu.be/`, `shorts/`, ID crudo)
- 3 bots responden en secuencia (Alex → Maya → Jordan) sobre el contenido
- Transcript limitado a **1500 chars** para no saturar el límite de tokens del LLM
- Mensaje se inyecta con `is_human: True` y autor = usuario, para que el bot lo trate como input del jugador

**Uso**:
```
!video https://www.youtube.com/watch?v=VIDEO_ID
```

### 2. Bugfix crítico: `youtube-transcript-api` API cambió

**Error**: `type object 'YouTubeTranscriptApi' has no attribute 'get_transcript'`

**Causa**: la nueva versión 1.2.4 usa `api.fetch(video_id)` en vez de `YouTubeTranscriptApi.get_transcript(video_id)`. Además devuelve `FetchedTranscriptSnippet` (objetos) en vez de `dict` con clave `'text'`.

**Fix** (bot.py):
```python
# Antes (v0.x):
transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[...])
text = " ".join([t['text'] for t in transcript])

# Ahora (v1.2.4):
api = YouTubeTranscriptApi()
transcript = api.fetch(video_id)
text = " ".join([snippet.text for snippet in transcript])
```

### 3. Bugfix audio server: webhook no configurado

**Error**: `POST /api/voice` → `500 Voice webhook not configured`

**Causa**: `audio_server.py` lee el webhook URL de `/tmp/discord_voice_webhook.txt` UNA VEZ al arrancar. Si el audio server arranca ANTES que el bot, el archivo no existe → `VOICE_WEBHOOK_URL = None` cacheado en memoria. El bot después escribe el archivo pero audio server no lo relee.

**Fix**: reiniciar audio server DESPUÉS del bot (orden correcto). Para automatizar: arrancar siempre `./start.sh` que respeta el orden, o invertir el flujo (bot primero, audio server 10s después).

**Workaround implementado**: el código ya tiene el patrón correcto — `load_voice_webhook_url()` intenta `os.getenv("DISCORD_VOICE_WEBHOOK_URL")` primero y luego el archivo, así que solo el orden de arranque importa.

### 4. Bugfix Casete vocab location v1 vs v2 (ya commiteado en sesión 2026-07-21 anterior)

`register_word_heard` escribía en `state["casete_vocab"][uid]` (formato legacy) pero `on_casete_help` leía de `state["users"][uid]["casete_vocab"]` (formato v2). El contador nunca se incrementaba en runtime.

**Fix** (commit `3469113`): unificado a `state["users"][uid]["casete_vocab"]`.

### 5. Anti-echo blocker en GUI

**Síntoma**: eco inmediato cuando el bot habla (TTS de Discord lee el mensaje → mic del browser lo capta → loop).

**Fix** (commit `b30aa48`): 3 puntos en `audio_player.html`:
- `playAudio()`: marca `localStorage['recognition_blocked_until']` con timestamp = ahora + duración del audio + 2s margen
- `startListening()`: si está bloqueado, muestra "⏳ Espera Ns" y no arranca el mic
- `onresult final`: si llega transcripción durante bloqueo, la descarta con "🚫 Eco descartado"

### 6. Configuración audio Linux (PipeWire)

Problema reportado: "no puedo hablar y escuchar a la vez". Diagnóstico:
- Profile activo: `hdmi-surround` (salida a monitor BK WXGA por HDMI)
- Mic integrado de laptop como entrada

**Fix aplicado**:
```bash
pactl set-card-profile 44 output:analog-stereo+input:analog-stereo
pactl set-default-sink alsa_output.pci-0000_00_1b.0.analog-stereo
pactl set-default-source alsa_input.pci-0000_00_1b.0.analog-stereo.3
```

Resultado: salida a auriculares (`analog-output-headphones`) + entrada desde mic de auriculares (`analog-input-mic`).

### 7. personas.json — bloque Casete añadido

El bloque Casete faltaba en `personas.json` (estaba en el código pero no en el JSON), lo que impedía mostrar la voz ElevenLabs en la GUI. Añadido con prompt del loro cyborg, voice dict ElevenLabs, emoji 🦜.

---

## 📦 Commits añadidos en esta sesión

```
b30aa48 fix(gui): anti-echo blocker for voice recognition
3469113 fix: Casete vocab location unified to users[uid].casete_vocab (v2)
```

(commits previos ya documentados en sesión 2026-07-21 anterior)

---

## 📁 Archivos modificados

| Archivo | Cambio |
|---|---|
| `bot.py` | +`!video` command (90 líneas) + logging en `on_message` para comandos |
| `audio_player.html` | +anti-echo blocker (3 puntos) |
| `state_manager.py` | Casete vocab unificado a v2 (sessión anterior) |
| `personas.json` | +bloque Casete con voice ElevenLabs |
| `requirements.txt` (o venv) | +`youtube-transcript-api==1.2.4` |

---

## ⚠️ Pendientes para siguientes sesiones

- [ ] **Multi-user en Discord**: el bot ya soporta multi-user (Discord ID en vez de hardcodear "Vaclav"), pero falta validar con un amigo real (Ronny u otro) que los vocabularios de Casete se aíslan correctamente entre usuarios.
- [ ] **Persistencia de `!video`**: el transcript se guarda en `conversation_history` pero NO en `users[uid].sessions[active].messages` (sesiones no incluyen el contexto del video). Si quieres poder retomar una "sesión de discusión de video" después, hay que duplicar el append.
- [ ] **Persistencia de la config de audio PipeWire**: el cambio de profile sobrevive a la sesión pero no necesariamente al reinicio de la PC. Si quieres automatizar, crear un script que corra al startup con esos `pactl set-*`.
- [ ] **Más comandos de "fuente externa"**: si quieres, podemos añadir `!podcast <feed RSS>`, `!article <URL>`, etc. usando el mismo patrón que `!video`.

---

## 🔗 Enlaces
- [[_KRK9-MOC|Índice del proyecto KRK-9]]
- [[2026-07-20-krk9-personality-editor-gui]] (sesión previa, base del editor)
- [[2026-07-21-krk9-casete-ui-multiusuario]] (sesión del día, Casete + rediseño GUI)
- [[PLAN_casete_obsidian_topics|Plan técnico ejecutado]]