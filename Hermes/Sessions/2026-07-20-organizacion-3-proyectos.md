---
type: hermes-session
project: Hermes
date: "2026-07-20"
tags:
  - proyecto/hermes
hermes_session: "PENDIENTE"   # se completa cuando el chat quede indexado (session_search)
title_original: "Organización de Obsidian en 3 proyectos + captura KRK-9"
---

# Hermes — 2026-07-20 · Organización del vault en 3 proyectos separados

> [!info] Para volver al chat original: pídele a Hermes *"busca la sesión que
> organizó Obsidian en 3 proyectos"* (o completa el `hermes_session` del
> frontmatter cuando lo tengas).

## 🎯 Objetivo
Organizar el vault de Obsidian para tener 3 "sesiones"/proyectos que NO se
mezclen: (1) CGAlpha, (2) KRK-9 (Discord-Bot), (3) Hermes (mejoras + aprender
Obsidian). Y aprender a pasar contenido de chats de Hermes a notas enlazadas.

## 🔍 Hallazgo importante (sin resolver)
- **La app Obsidian abre el vault EQUIVOCADO**: `~/Documentos/Obsidian Vault`
  (con acento, VACÍO, solo `Bienvenido.md`).
- El vault REAL con todo el contenido es `~/Documents/Obsidian-Vault`
  (con guion, sin acento). ⚠️ Pendiente: apuntar la app al correcto vía
  "Open folder as vault".

## 💻 Lo que se hizo
1. Estructura de 3 proyectos, cada uno con **carpeta + MOC (`_<Proj>-MOC.md`) + `Sessions/`**:
   - `CGAlpha/` → `_CGAlpha-MOC.md`
   - `Discord-Bot/` → `_KRK9-MOC.md`  (el usuario prefiere el nombre "Discord-Bot")
   - `Hermes/` → `_Hermes-MOC.md`
2. Sistema anti-mezcla:
   - **Carpeta** = separación física
   - **Tag** = `#proyecto/cgalpha` | `#proyecto/krk9` | `#proyecto/hermes`
   - **MOC** = índice/punto de entrada de cada proyecto
3. Puente chat→nota: el **`session_id` de Hermes** se guarda en el frontmatter
   (`hermes_session:`). Desde una nota se recupera el chat con `session_search`.
4. Se capturó **1 sesión de KRK-9**: `Discord-Bot/Sessions/2026-07-07-krk9-bug-speak-duplicado.md`
   (bug `!speak` duplicado; `session_id: 20260707_174324_b49cd0`).
   - Nota: primero se creó por error una recopilación de 3 chats; el usuario
     aclaró que solo quería la del 2026-07-07 → se borró la de 3 y se dejó solo esa.

## 📝 Regla aprendida (guardada en memoria interna)
- Al "guardar sesión en Obsidian": capturar **SOLO ese chat concreto**, no
  recopilar todos los chats relacionados.
- **Guardado AUTOMÁTICO** (decisión del usuario 2026-07-20): Hermes debe guardar
  la sesión en Obsidian de forma proactiva al cerrar/cambiar de tema, SIN que el
  usuario lo pida. Deduce el proyecto por el tema; si duda entre
  CGAlpha/Discord-Bot/Hermes → PREGUNTA en cuál guardar.

## ⚠️ Límite honesto del guardado automático (aclarado 2026-07-20)
- Hermes solo actúa cuando recibe un mensaje. Si el usuario **cierra el chat de
  golpe** sin escribir, o hay **corte de luz**, la nota NO se crea en ese momento.
- PERO el chat NO se pierde: Hermes guarda todo en su DB interna (`state.db`),
  recuperable con `session_search`. En la siguiente sesión se puede crear la nota
  entonces. Es decir: se guarda tarde, pero no se pierde.
- Para garantía inmediata, el usuario dice "guarda"/"cierro" antes de cerrar.
- Idea pendiente (ofrecida, no implementada): cron nocturno que revise los chats
  del día y auto-genere en Obsidian los que falten.

## ⏭️ Pendientes
- [ ] Apuntar la app Obsidian al vault correcto (`~/Documents/Obsidian-Vault`)
- [ ] (Opcional) borrar el vault de prueba vacío `~/Documentos/Obsidian Vault`
- [ ] Completar `hermes_session` de esta nota cuando el chat quede indexado

## 🔗 Enlaces
- [[_Hermes-MOC|Índice del proyecto Hermes]]
- [[2026-07-19-obsidian-hermes]] · [[2026-07-19-bc-autoload]]
