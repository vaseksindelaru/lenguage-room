---
type: hermes-session
project: KRK-9
date: "2026-07-20"
tags:
  - proyecto/krk9
summary_of_chats: true
hermes_sessions:
  - "20260707_174324_b49cd0"   # Problema app English Room y reinicio (bug !speak duplicado)
  - "20260629_120226_a410ee"   # Mentoria Python Oracle (mixta: rebranding KRK-9, arquitectura)
  - "20260716_172531_d965cf"   # Solucion error KAT-Coder (mixta: healthchecks, router LLM)
---

# KRK-9 — Recopilación de Chats de Hermes (contexto histórico)

> [!info] Esta nota recopila lo que se discutió sobre **KRK-9** en chats
> anteriores de Hermes. Los `session_id` están en el frontmatter: para volver
> al chat original completo, pídele a Hermes *"busca la sesión `<id>`"* y hará
> `session_search`.

## 🧩 De dónde salió cada cosa

### 🐛 Chat 2026-07-07 — "Problema app English Room y reinicio"
`session_id: 20260707_174324_b49cd0`

**Tema central:** bug de **mensajes duplicados** en el comando `!speak`.
- Los contenedores Docker no estaban corriendo → se levantaron.
- El puerto **8081** (audio server WebSocket) no cargaba.
- Se añadió **logging detallado** en `bot.py` (`cmd_speak`): marcadores
  `START / END / DONE`, conteo de openings enviados, para detectar si
  `cmd_speak` se ejecutaba **una o dos veces**.
- Comando de diagnóstico usado:
  ```bash
  tail -50 ~/discord-english-room/bot.log | grep -E "(START|END|DONE|Sent|Opening|Inviting)"
  ```
- Datos operativos confirmados en el log del bot:
  - Bot conectado como `chat room#0720` (ID `1523132776327680041`)
  - Canal objetivo: `1523161377747763342`
  - User ID Vaclav: `1458317824299892746`
  - State en `/home/vaclav/.english-bot/state.json`
  - Webhooks activos: Alex, Maya, Jordan, Sam + "Vaclav voice input"
  - Audio server OK en `http://localhost:8081`
  - LLM respondió vía **Cerebras (gpt-oss-120b)**
  - Arranque del bot: `cd ~/discord-english-room && PYTHONPATH="" venv/bin/python bot.py 2>&1 | tee bot.log`
- ⚠️ Pendiente de esa sesión: NO se había commiteado el fix (usuario dijo
  "todavía no commitees, quiero probar primero").

### 🏗️ Chat 2026-06-29 — "Mentoría Python Oracle" (mixta con CGAlpha)
`session_id: 20260629_120226_a410ee`

**Lo relevante a KRK-9:**
- **Rebranding**: "Discord English bot" → **KRK-9**, en `~/discord-english-room`.
- 4 agentes: **Alex / Maya / Jordan / Sam** vía webhooks + Edge TTS.
- Router multi-LLM: **Cerebras → Groq → OpenRouter → Ollama**.
- Rotación de temas cada 30 min.
- Web Speech API (micrófono) → webhook de Discord. WebSocket TTS puerto 8081.
- **Fase 1 futura: multi-usuario** — modificar `bot.py` para que el amigo
  **Ronny** (no-programador) pueda hablar con los bots.
- Ronny quiere aprender "vibe coding" con este proyecto.
- Idea de dobles docs: `README_USERS.md` (no-coders) + `README_DEVS.md` (coders).

### 🔧 Chat 2026-07-16 — "Solución error KAT-Coder" (mixta)
`session_id: 20260716_172531_d965cf`

**Lo relevante a KRK-9:** confirmación de arquitectura para watchdogs —
healthcheck de los 4 webhooks, verificación del router LLM y del WebSocket
TTS 8081 como candidatos a monitoreo 24/7 desde un Hermes servidor.

## 🎯 Estado consolidado de KRK-9
- Ruta: `~/discord-english-room`
- Arranque bot: `cd ~/discord-english-room && PYTHONPATH="" venv/bin/python bot.py 2>&1 | tee bot.log`
- Audio server: puerto 8081 (WebSocket + HTTP `/api/audio`)
- Deploy previo con Docker Compose (bot, audio-server, ollama)

## ⏭️ Pendientes heredados de los chats
- [ ] Verificar/commitear el fix del bug `!speak` duplicado (2026-07-07)
- [ ] Fase 1 multi-usuario para Ronny (modificar `bot.py`)
- [ ] Dobles README (USERS / DEVS)

## 🔗 Enlaces
- [[_KRK9-MOC|Índice del proyecto KRK-9]]
