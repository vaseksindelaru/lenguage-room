---
type: hermes-session
project: KRK-9
date: "2026-07-21"
tags:
  - proyecto/krk9
  - casete
  - multiuser
  - gui-redesign
  - elevenlabs
title_original: "KRK-9 — Resumen de cambios Fase Casete + UI multiusuario"
---

# KRK-9 — 2026-07-21 · Resumen de Cambios: Casete + UI Multiusuario

> [!info] Nota de cierre de la fase "Casete y rediseño de UI". Resume el resultado de ejecutar el `PLAN_casete_obsidian_topics.md` (12 fases, 14 commits en `feat/casete-obsidian-topics-elevenlabs`).

---

## 🦜 1. Personaje Casete (loro cyborg)

### Backend
- **Escucha pasiva e interactiva:** Casete incrementa contadores de palabras cuando las dice un humano (`on_message`) o un agente (`send_agent_message`). Al cruzar el umbral (default 3), la palabra entra a `known` y queda disponible para asistencia futura.
- **Persistencia:** vive en `state.json` bajo `casete_vocab[user_id] = {threshold, counts, known, first_seen}` — sobrevive entre sesiones y entre reinicios.
- **Comando `!casete <palabra>`:** fuerza a Casete a soplar la palabra si está en `known`, o admite que no la tiene con frase fija si no.
- **Triggers en chat:** detecta `cómo se dice...`, `how do you say...`, `no sé cómo...` vía regex (`CASETE_TRIGGERS`) en `on_message`, antes del sorteo normal.
- **Fuera del weighted random:** `decide_next_agent()` solo sorte entre los agentes activos del estado (`active_agents`), no incluye Casete en el peso base. Casete es event-triggered.

### Frontend
- **Doble panel TTS** (Edge / ElevenLabs): menu de 2 tabs para que los agentes cyborg oscilen entre proveedor humano (Edge Neural) y personaje (ElevenLabs).
- **Bug fix visual:** el render inicial mostraba literalmente `[object Object]` en la card de voz. Corregido.

### Archivos tocados
- `bot.py` (49→69KB): `on_casete_help`, `extract_notable_words`, `maybe_invoke_casete`, hook en `on_message`
- `state_manager.py` (11→19KB): `register_word_heard`, `get_casete_known`, `migrate_state_v1_to_v2`
- `audio_player.html`: card `#card-Casete`, color `#00ffaa`, doble panel TTS
- `personas.json`: bloque Casete con prompt y voz ElevenLabs dict

---

## 🎛️ 2. Motor de "Participantes Activos" (`audio_server.py`)

### Funcionalidad
- **Control total del usuario sobre QUIÉNES hablan.** Si apagas a Maya desde la GUI, Maya no se dispara en Discord ni en audio bajo ninguna circunstancia.
- **Endpoints:**
  - `GET /api/active-agents` → devuelve la lista actual (default: `["Alex","Maya","Jordan","Sam","Casete"]`)
  - `POST /api/active-agents` → actualiza `state["active_agents"]` con la lista recibida
- **Integración con `bot.py`:**
  - `decide_next_agent()` (L819) filtra los `weights` para solo incluir agentes activos
  - `on_message` (L906) y otros call-sites (L1499) usan la lista filtrada
  - Casete también respeta la lista: si está inactivo, su trigger en `on_message` no opera

### Archivos tocados
- `audio_server.py` (16→27KB): handlers `active_agents_get_handler` / `active_agents_post_handler` + registro de rutas
- `bot.py`: 3 call-sites actualizados para leer `state["active_agents"]`
- `audio_player.html` L1389-1422: fetch + render de la lista activa

---

## 🎨 3. Rediseño Total de la Main GUI

### Cambios visuales
- **Tipografía universal:** Inter (Google Fonts) en todo el portal — look Discord/Premium moderno.
- **Logo superior eliminado:** el espacio se destina al grid de avatares (más funcional).
- **Selector "Participants":** botones glassmorphism (semi-transparente + blur estilo MacOS/iOS) en la parte alta.
- **Grid 1 fila lineal:** las 5 tarjetas (Alex, Maya, Jordan, Sam, Casete) fluyen en horizontal sin apilarse. Distribución uniforme.
- **Estado inactivo visual:** tarjetas de agentes desactivados se ven en grayscale + opacidad reducida. Control visual rápido.
- **Responsive móvil** (`@media width<600px`): las 5 cajas NO se apilan; mantienen fila con scroll horizontal tipo carrusel (ahorra batería + scrolls innecesarios).
- **Status banner:** reducido a texto pequeño de 1 fila estilo toast mini.

### Archivo tocado
- `audio_player.html` (21→69KB): refactor completo del CSS + DOM, sin tocar la lógica JS principal

---

## 🗃️ 4. Historial Persistente + Exportación Multiusuario

### Cambios
- **Migración state v1 → v2:** pasamos de `conversation_history` global (recortado a 50) a estructura `users[user_id].sessions[]` (sin recorte, persistentes).
- **Identificación por Discord ID:** `str(message.author.id)` en vez de hardcodear "Vaclav".
- **Sesiones persistentes:** cada sesión tiene `{id, topic, created, updated, messages}`. Las sesiones NUNCA se borran (a diferencia del viejo `conversation_history`).
- **Endpoints:**
  - `GET /api/sessions?user_id=...` → lista sesiones
  - `POST /api/sessions` → crea nueva sesión
  - `POST /api/sessions/resume` → marca activa
  - `POST /api/session/save-obsidian` → exporta a markdown
- **Markdown exportado** (formato estructurado con frontmatter estricto):
  - Tipo `krk9-session`, proyecto KRK-9, fecha, tema, user, session_id, # mensajes, duración
  - Tags: `[proyecto/krk9, conversation]`
  - Secciones: Resumen, Transcripción, Enlaces a MOC y sesión previa
  - Ruta: `~/Documents/Obsidian-Vault/Discord-Bot/Sessions/<YYYY-MM-DD>-krk9-session-<uuid>.md`
  - Fallback: `./SESSIONS/` en el repo
- **Botón 📜 en GUI:** abre modal "Historial de Sesiones" con lista + botones "▶️ Retomar" / "💾 Obsidian" / "🗑 Borrar" por sesión.
- **Toggle "Auto-guardar en Obsidian":** configurable por usuario (off por defecto para no spammear).

### Archivos tocados
- `state_manager.py`: `migrate_state_v1_to_v2`, `create_user_session`, `list_user_sessions`, `get_active_session`, `set_active_session`, `append_session_message`
- `audio_server.py`: 4 endpoints nuevos
- `audio_player.html`: modal Historial + JS de gestión

---

## 📦 Despliegue

### Rama
- `feat/casete-obsidian-topics-elevenlabs` (basada en `feat/personality-editor-gui`)
- **NO pusheada** todavía (sin push al remoto).

### Commits (14 total, ordenados del más reciente al más antiguo)
```
fbb69aa style(gui): remove logo, shrink status, align 1-row layout
e123cb7 feat(gui): restore Casete participant card & add toggle logic
aeb11f8 fix(gui): correct voice object stringification in card
305ae84 feat(gui): Casete card + History modal + voice provider selector
f656766 feat(api): endpoints para GUI de sesiones y topics
40aa366 feat: generate_topic_suggestions + Casete count in agent messages
4395b77 feat: Comandos de sesión, preferencias y topics dinámicos
5967d85 feat(state): user sessions logic (persistent, no trim)
f72ea6a feat(state): migración a estado multi-usuario (v1 -> v2)
4db7340 feat(state): Casete vocabulary functions (register, get, threshold)
51aa704 feat: Casete vocabulary logic (extract, on_casete_help, !casete command, hook)
14d5dcc feat: add Casete (cyborg parrot) to AGENTS, PERSONAS, VALID_AGENTS, DEFAULT_PERSONAS
3410eb8 refactor(bot): generate_tts() ahora delega a tts_providers
ee464c7 feat(tts): shared TTS provider module (Edge + ElevenLabs with fallback)
```
(La rama incluye además `1dd28b0` heredado del fix `load_dotenv`.)

### Estado del working tree
- Limpio, salvo `PLAN_casete_obsidian_topics.md` (untracked, no commiteado).

---

## ✅ Compatibilidad verificada

- El flag `ignore_bot_messages` (fix del bug `!speak` del 2026-07-07) sigue intacto en `bot.py` L1136-1216. Casete no rompe el fix.
- `conversation_history` global se mantiene recortado a 50 para compat con `conversation_loop`. La estructura nueva `users[uid].sessions` corre paralela.
- `VALID_AGENTS = {"Alex","Maya","Jordan","Sam","Casete"}` — el endpoint `POST /api/personas` acepta a Casete sin rechazar.
- Estado real (`~/.english-bot/state.json`) migrado automáticamente a `version: 2` al primer load tras F6.

---

## ⏭️ Pendiente para validación manual en Discord (no automatizable)

- [ ] `!casete breakthrough` → Casete responde con entusiasmo (LLM genera frase)
- [ ] `!casete xyzabc` → frase fija, **sin** llamar al LLM (verificar en logs ausencia de `✅ LLM response`)
- [ ] Repetir una palabra 3 veces → aparece en `known` de `casete_vocab[user_id]`
- [ ] `!sessions` lista sesiones, `!session resume last` retoma
- [ ] Botón "💾 Obsidian" crea `.md` en vault
- [ ] Activar/desactivar agente desde GUI → respuesta en Discord refleja el cambio
- [ ] `!speak` sigue funcionando sin duplicación

---

## 🔗 Enlaces
- [[_KRK9-MOC|Índice del proyecto KRK-9]]
- [[2026-07-07-krk9-bug-speak-duplicado]] (bug `!speak` previo que Casete respeta)
- [[2026-07-20-krk9-personality-editor-gui]] (editor GUI previo, base de esta fase)
- [[PLAN_casete_obsidian_topics]] (plan técnico ejecutado)