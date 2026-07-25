---
type: project-moc
project: KRK-9
tags:
  - proyecto/krk9
  - moc
created: 2026-07-20
---

# 🔵 KRK-9 (Discord English Bot) — Índice del Proyecto (MOC)

> [!info] Punto de entrada del proyecto. Todo lo de KRK-9 vive bajo `Discord-Bot/`.
> Cada sesión de trabajo va en `Discord-Bot/Sessions/` con tag `#proyecto/krk9`.

## 📌 Qué es
App colaborativa GRATIS de práctica de inglés en Discord. 4 agentes de IA
(Alex/Maya/…) vía webhooks + Edge TTS + OpenRouter. 100% local con Ollama.
Cualquiera puede instalarlo vía Hermes.

## 🔑 Datos clave
- Ruta del proyecto: `~/discord-english-room`
- Router multi-LLM: **Cerebras → Groq → OpenRouter → Ollama** (fallback qwen2.5:3b)
- Servidor de audio: WebSocket + HTTP (puerto TTS 8081)
- Web Speech API necesita HTTPS/ngrok
- Canal de Discord: `1523161377747763342`
- Branding configurable vía `static/logo.png`

## 🎯 Visión
- Primer tester no-técnico: **Ronny** (Windows)
- Futuro: multi-usuario, botón GUI "Invite friends", integración con app Roger (repo PRIVADO)

## 🗂️ Sesiones
- [[2026-07-07-krk9-bug-speak-duplicado|2026-07-07 — Bug `!speak` duplicado + reinicio de servicios]]
- [[2026-07-20-krk9-personality-editor-gui|2026-07-20 — Editor GUI personalidad/voz/LLM + fix load_dotenv]]
- [[2026-07-21-krk9-casete-ui-multiusuario|2026-07-21 — Casete loro cyborg + rediseño GUI multiusuario + 14 commits]]
- [[2026-07-21-krk9-youtube-command-bugfixes|2026-07-21 (tarde) — Comando !video YouTube + bugfixes (vocab v2, anti-eco, audio server, Casete JSON)]]

## 📋 Planes (pendientes de ejecución)
- [[PLAN_casete_obsidian_topics|Plan técnico: Casete + historial + temas + ElevenLabs]] (2026-07-21, Aprobado y **EJECUTADO** — ver sesión 2026-07-21)
- Ver todas: buscar `path:Discord-Bot/Sessions`

## ⏭️ Pendientes
- [ ] Probar en Discord (`./start.sh` + `!speak`) que la GUI aplica persona/voz/LLM y que `!speak` no duplica (ver sesión 2026-07-20)

## 📊 Graphify Analysis
- **Analysis date**: 2026-07-25
- **Project**: lenguage-room unified (Discord-Bot + news_room)
- **Graph files**: `graphify-out/graph.html` (240KB), `graphify-out/GRAPH_REPORT.md` (143 lines), `graphify-out/graph.json`
- **Stats**: 272 nodes, 557 edges, 16 communities
- **Note**: Uses `PYTHONPATH` fix for graphifyy Python 3.13 compatibility
