---
type: hermes-session
project: KRK-9
date: "2026-07-07"
tags:
  - proyecto/krk9
hermes_session: "20260707_174324_b49cd0"
title_original: "Problema app English Room y reinicio"
---

# KRK-9 — 2026-07-07 · Bug `!speak` duplicado + reinicio de servicios

> [!info] Nota de sesión de Hermes. Para volver al chat original completo,
> pídele a Hermes: *"busca la sesión `20260707_174324_b49cd0`"*.

## 🎯 Objetivo
Arreglar que la app English Room (KRK-9) no cargaba en el puerto 8081 y que el
comando `!speak` en Discord producía **mensajes duplicados** de los bots.

## 🔍 Diagnóstico
1. Los contenedores **Docker no estaban corriendo** → se levantaron los servicios.
2. El **puerto 8081** (audio server) no respondía inicialmente; tras reiniciar
   quedó confirmado: `🔊 Audio server confirmed running at http://localhost:8081`.
3. El **audio funcionaba**, pero la **duplicación de mensajes persistía**.
4. Hipótesis principal: el handler `on_message` estaba procesando los mensajes
   de los **webhooks** (Alex/Maya/Jordan/Sam) y disparando respuestas extra que
   se solapaban con las de `cmd_speak`.

## 💻 Cambios / Debug aplicado
- Se añadió **logging detallado** en `bot.py` (`cmd_speak`): marcadores
  `START / END / DONE`, conteo de openings enviados, para detectar si
  `cmd_speak` se ejecutaba **una o dos veces**.
- Se reforzó el filtro en `on_message` (líneas ~868-892 de `bot.py`):
  ```python
  async def on_message(message: discord.Message):
      global last_vaclav_activity, ignore_bot_messages
      # FIX: ignorar mensajes durante ejecución de !speak
      if ignore_bot_messages:
          return
      # FIX: ignorar TODOS los mensajes de bots (incl. self),
      #      salvo el relay de voz de Vaclav
      if message.author.bot:
          if message.content.startswith("🎤 **Vaclav (voice):**"):
              pass
          else:
              return
      if message.channel.id != CHANNEL_ID:
          return
      # comandos: dejar que discord.py los procese UNA vez
      if message.content.startswith("!"):
          await bot.process_commands(message)
          return   # importante: no seguir hasta el final
  ```
- Comando de diagnóstico del log:
  ```bash
  tail -50 ~/discord-english-room/bot.log | grep -E "(START|END|DONE|Sent|Opening|Inviting)"
  ```

## 🖥️ Datos operativos confirmados (del log del bot)
- Bot conectado como `chat room#0720` (ID `1523132776327680041`)
- Canal objetivo: `1523161377747763342`
- User ID Vaclav: `1458317824299892746`
- State en `/home/vaclav/.english-bot/state.json`
- Webhooks activos: Alex, Maya, Jordan, Sam + "Vaclav voice input"
- LLM respondió vía **Cerebras (gpt-oss-120b)**
- Arranque del bot:
  ```bash
  cd ~/discord-english-room && PYTHONPATH="" venv/bin/python bot.py 2>&1 | tee bot.log
  ```

## ⚠️ Estado al cerrar la sesión
- El fix del filtro se aplicó pero **NO se commiteó** — el usuario dijo
  *"sí, pero todavía no commitees"* porque quería **probar primero** con el
  nuevo bot (con logging) si la duplicación desaparecía.

## ⏭️ Pendiente
- [ ] Ejecutar `!speak` y revisar el log: ¿`cmd_speak` corre 1 o 2 veces?
- [ ] Si 1 vez → bug resuelto → **commitear** el fix.
- [ ] Si 2 veces → seguir investigando (posible doble registro del handler).

## 🔗 Enlaces
- [[_KRK9-MOC|Índice del proyecto KRK-9]]
