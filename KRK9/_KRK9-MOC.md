---
type: project-moc
project: KRK9
tags:
  - proyecto/krk9
  - moc
created: 2026-07-20
last_updated: 2026-08-01
---

# 🔵 KRK9 — Discord English Room Bot (MOC)

> [!info] Punto de entrada del proyecto. Todo vive bajo `KRK9/`.
> Sesiones en `KRK9/sessions/` con tag `#proyecto/krk9`.
> Repo código: `lenguage-room` (GitHub) | Proyecto local: `~/discord-english-room`

## 📌 Qué es
App colaborativa GRATIS de práctica de inglés en Discord. 4 agentes de IA
(Alex, Maya, Sam, Jordan) vía webhooks + Edge TTS + OpenRouter. 100% local con Ollama.
Cualquiera puede instalarlo vía Hermes.

## 🔑 Datos clave (fuente de verdad)
- **Proyecto local**: `~/discord-english-room`
- **Repo GitHub**: `vaseksindelaru/lenguage-room` (rama `main`)
- **Router multi-LLM**: Cerebras → Groq → OpenRouter → Ollama (fallback qwen2.5:3b)
- **Servidor audio**: WebSocket + HTTP (puerto TTS 8081)
- **Web Speech API**: requiere HTTPS/ngrok
- **Canal Discord**: `1523161377747763342`
- **Branding**: configurable vía `static/logo.png`

## 🧩 Componentes
| Componente | Descripción | Ubicación |
|------------|-------------|-----------|
| **Discord Bot** | 4 agentes IA + comandos (`!speak`, `!video`, `!casete`) | `~/discord-english-room/bot/` |
| **News Room** | News aggregator + entry page assistant | `~/discord-english-room/news_room/` |
| **TTS Server** | Edge TTS + WebSocket (puerto 8081) | `~/discord-english-room/tts/` |
| **GUI** | Personality/voice/LLM editor | `~/discord-english-room/gui/` |

## 🗂️ Sesiones (cronológico)
- `KRK9/sessions/2026-07-23-krk9-personality-edit.md` — Personality edit
- `KRK9/sessions/2026-07-21-krk9-youtube-command-bugfixes.md` — `!video` YouTube + bugfixes (vocab v2, anti-eco, audio server, Casete JSON)
- `KRK9/sessions/2026-07-21-krk9-casete-ui-multiusuario.md` — Casete loro cyborg + rediseño GUI multiusuario + 14 commits
- `KRK9/sessions/2026-07-20-krk9-personality-editor-gui.md` — Editor GUI personalidad/voz/LLM + fix load_dotenv
- `KRK9/sessions/2026-07-07-krk9-bug-speak-duplicado.md` — Bug `!speak` duplicado + reinicio de servicios
- Ver todas: buscar `path:KRK9/sessions`

## 📋 Planes y Prompts (referencia)
| Archivo | Descripción |
|---------|-------------|
| `KRK9/notes/PLAN_casete_obsidian_topics.md` | Plan técnico: Casete + historial + temas + ElevenLabs (APROBADO y EJECUTADO) |
| `KRK9/notes/PROMPT_entry_page_news_room_assistant.md` | Prompt para News Room Assistant |
| `KRK9/notes/PROMPT_nemotron_entry_page_news_room.md` | Prompt Nemotron para News Room |

## 📊 Análisis Graphify
- **Fecha**: 2026-07-25
- **Proyecto**: lenguage-room unified (Discord-Bot + news_room)
- **Archivos**: `graphify-out/graph.html`, `GRAPH_REPORT.md`, `graph.json`
- **Stats**: 272 nodos, 557 aristas, 16 comunidades
- **Nota**: Fix `PYTHONPATH` para compatibilidad Python 3.13
- **Guardado en**: `KRK9/analysis/graph-report-20260725.md`

## ⏭️ Pendientes
- [ ] Probar en Discord (`./start.sh` + `!speak`) que GUI aplica persona/voz/LLM y que `!speak` no duplica
- [ ] Migrar vault a rama `krk9-vault` en origin

## 🔗 Referencias externas
- Repo: `git@github.com:vaseksindelaru/lenguage-room.git`
- Hermes skill: `krk9-vault-auto` (por crear)
- Cron: `krk9-moc-sync` (por crear)