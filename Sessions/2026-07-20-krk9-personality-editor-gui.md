---
type: hermes-session
project: KRK-9
date: "2026-07-20"
tags:
  - proyecto/krk9
  - personality-edit
  - gui
title_original: "KRK-9 — Editor GUI de personalidad/voz/LLM + validación y fix"
---

# KRK-9 — 2026-07-20 · Editor GUI de Personalidad/Voz/LLM

> [!info] Nota de sesión de Hermes. El chat original es de esta fecha en el runtime de Hermes.

## 🎯 Objetivo
Construir panel ⚙️ Settings en `audio_player.html` para:
1. Editar carácter/persona de Alex/Maya/Jordan/Sam
2. Elegir LLM por agente (router por defecto o provider concreto con fallback)
3. Elegir voz TTS y emoji por personaje
4. Auto-generar resumen de la edición en Obsidian al guardar

## 🛠️ Qué se construyó (commit `d24b9ec`, rama `feat/personality-editor-gui`)
- `personas.json` (gitignored, config local tipo `.env`) con 4 agentes
- `state_manager.py`: `load_personas()` / `save_personas()` / `DEFAULT_PERSONAS`
  (constante copiada de bot.py para evitar import circular)
- `audio_server.py`: 4 rutas nuevas
  - `GET/POST /api/personas`
  - `POST /api/tts-preview` ← CORRECCIÓN: NO usar `/api/voice` (ese envía
    texto al canal de Discord vía webhook → habría espameado)
  - `POST /api/session-export` → escribe `.md` en Obsidian (fallback `./SESSIONS/`)
- `bot.py`: hot-reload de persona/voice/LLM desde `personas.json` por request;
  `call_openrouter()` acepta `provider_override`+`model_override` con fallback
  a la cadena router si el provider falla
- `audio_player.html`: modal 4 tabs, emoji picker (30), voice dropdown + 🎲 preview,
  LLM/model selector dinámico, Obsidian export al Save & Close

## 🐛 Bug encontrado y corregido (commit `1dd28b0`)
- `audio_server.py` **NO llamaba `load_dotenv()`** → `/api/personas` solo reportaba
  `['router']` aunque el `.env` tenía `CEREBRAS_API_KEY` y `OLLAMA_URL` reales.
- `bot.py` sí lo hacía (L45); se añadió a `audio_server.py`.
- Validado end-to-end: ahora detecta `['router', 'cerebras', 'ollama']` correctamente.

## ✅ Verificación real ejecutada (no fabricada)
- Puerto 8081 libre tras matar server viejo que ocupaba el puerto
- `GET /health` → `{"status":"ok"}`
- `POST /api/session-export` → escribió de verdad
  `~/Documents/Obsidian-Vault/Discord-Bot/Sessions/2026-07-20-test-export-real.md`
  (luego borrado tras la prueba) con `is_obsidian: true`
- `GET /api/personas` → 4 agentes + providers detectados tras el fix
- `file` del MP3 de `/api/tts-preview` → `MPEG ADTS, layer III` (audio real, sin tocar Discord)

## 📌 Notas de contexto
- El fix del bug de `!speak` duplicado del 07-07 **quedó commiteado** en este flujo
  (commit `32eff67` + flag `ignore_bot_messages` en `bot.py` L1136-1216). El pendiente
  original "no commitear hasta validar" ya no aplica.
- `.gitignore` ahora excluye `.pids/` y `personas.json`.
- Rama `feat/personality-editor-gui` NO está pusheada (sin remoto en el repo local).

## ⏭️ Pendiente (prueba manual en Discord, diferida a más tarde)
- [ ] Levantar `./start.sh` (bot + audio server con soporte personas)
- [ ] `!speak` en Discord → verificar que los bots usan persona de `personas.json`
- [ ] Cambiar voz de Alex en GUI → Save → `!speak` → oír nueva voz
- [ ] Cambiar LLM de Alex a `ollama` → verificar que usa Ollama y cae a router si falla
- [ ] Confirmar que la duplicación de `!speak` NO volvió tras el reinicio

## 🔗 Enlaces
- [[_KRK9-MOC|Índice del proyecto KRK-9]]
- [[2026-07-07-krk9-bug-speak-duplicado|Bug !speak duplicado (sesión previa)]]
