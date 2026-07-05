# Decision Log — English Practice Bot

> Registro de decisiones técnicas tomadas durante el desarrollo. Formato: **Qué**, **Por qué**, **Resultado**.

---

## 2026-07-05

### 1. Token de Discord comprometido → Rotación inmediata
- **Qué:** GitHub detectó token en .env subido accidentalmente, lo revocó y generó nuevo token.
- **Por qué:** Seguridad. El token original quedó expuesto en commit 633bf48.
- **Resultado:** Token rotado a `[REDACTED]`. .env limpiado del historial con `git filter-branch`.

### 2. Separación de servicios: Audio Server independiente
- **Qué:** Audio server (WebSocket + HTTP API) corre en proceso separado del bot Discord.
- **Por qué:** El bot y el audio server tienen ciclos de vida diferentes. El audio server debe persistir aunque el bot se reinicie. WebSocket nativo no funcionaba bien con aiohttp en mismo proceso.
- **Resultado:** Audio server en puerto 8081 con WebSocket + HTTP API `/api/audio` (TTS) y `/api/voice` (STT). CORS configurado para localhost:8081 y 127.0.0.1:8081.

### 3. Ollama local como fallback final
- **Qué:** qwen2.5:3b via Ollama como último proveedor LLM.
- **Por qué:** Garantía de funcionamiento offline / sin créditos. Modelo 3B cabe en 16GB RAM con cuantización Q4.
- **Resultado:** Ollama corriendo en puerto 11434, endpoint nativo `/api/chat` (no `/v1` compatible OpenAI que tenía timeouts). Warmup al arrancar.

### 4. LLM Router multi-proveedor (Cerebras → Groq → OpenRouter → Ollama)
- **Qué:** Router con fallback automático por rate limits (429) y errores.
- **Por qué:** Cerebras (1M tokens/día gratis) como principal, Groq (LPU ultra-rápido) como fallback rápido, OpenRouter diversificado, Ollama red de seguridad.
- **Resultado:** Funciona. Cerebras principal con gpt-oss-120b.

### 5. Eliminación de rotación automática de temas (30 min)
- **Qué:** Eliminado `topic_rotation` task (@tasks.loop(minutes=30)).
- **Por qué:** Usuario quiere control total. Los cambios automáticos interrumpen el flujo de práctica.
- **Resultado:** Eliminado completamente. Ahora `topic_locked = True` por defecto. Usuario controla con `!topic`.

### 6. Delays fijos → Timing adaptativo `calculate_delay()`
- **Qué:** Reemplazados todos los `random.randint(3,8)`, `random.randint(5,10)`, `asyncio.sleep(8)` por `calculate_delay(message)`.
- **Por qué:** Bots hablaban demasiado rápido. Usuario no alcanzaba a leer/escuchar.
- **Fórmula:** `base_delay + max(reading_time, audio_time) + jitter(0.5-1.5)`, clamp 3-15s.
- **Resultado:** Mensajes cortos ~3-4s, medios ~6-8s, largos 10-15s.

### 7. Persistencia de sesión en ~/.english-bot/state.json
- **Qué:** Módulo `state_manager.py` + carga/guardado automático.
- **Qué persiste:** Historial (últimos 50), tema actual, pausa, topic_locked, configuración usuario, última sesión.
- **Al arrancar:** "Welcome back! Last session: [fecha]. Topic: [tema]. Resuming..."
- **Resultado:** Reiniciar bot → historial y tema se mantienen.

### 7. Comandos de tema ampliados (`!topic`)
- **Qué:** `!topic` (show), `!topic list`, `!topic <nombre/índice>`, `!topic next`, `!topic crypto` (match parcial).
- **Por qué:** Usuario controla temas, no rotación automática.
- **Persistencia:** Cambios se guardan en state.json automáticamente.

### 8. Comando `!speak`
- **Qué:** Invita a bots a hablar 1-2 mensajes de apertura sobre tema actual con delays adaptativos.
- **Por qué:** Usuario quiere iniciar conversación sin escribir.

### 9. Comando `!speak` y `!pause`/`!resume` persisten estado
- **Qué:** Comandos actualizan `state.json` (paused, current_topic_index, topic_locked).
- **Resultado:** Estado sobrevive a reinicios.

### 8. AudioContext resume en on_ready + Test audio
- **Qué:** AudioContext necesita gesto de usuario para iniciar (política browser). Botón "Test audio" lo desbloquea.
- **Resultado:** Click "Test audio" → AudioContext resume → TTS funciona.

### 9. CORS en Audio Server para localhost + 127.0.0.1
- **Qué:** aiohttp-cors configurado para ambos orígenes.
- **Por qué:** Usuario accede como `http://localhost:8081` o `http://127.0.0.1:8081` indistintamente.
- **Resultado:** CORS headers correctos en `/api/audio` y `/api/voice`.

### 10. RAG y Roger solo documentación (no código)
- **Qué:** `RAG_METHODOLOGY.md` (metodología iterativa 4 semanas) + `ROGER_INTEGRATION.md` (contrato stub).
- **Por qué:** Usuario quiere desarrollar RAG por práctica iterativa, no plan teórico. Roger solo cuando tenga API estable.
- **Resultado:** Documentos creados, NO código implementado.

### 11. `start.sh` usa `docker compose` (v2), no `docker-compose`
- **Qué:** Detección automática: `docker compose` → fallback `docker-compose`.
- **Por qué:** En sistemas modernos solo está el plugin v2; `docker-compose` standalone no existe.
- **Resultado:** `./start.sh` funciona sin instalar paquete legacy.

### 12. Fixes post-implementación (bugs encontrados)
- **Qué:** Eliminadas referencias rotas a `topic_rotation` en `on_ready`. Duplicados `!pause`/`!resume` removidos. Bug doble `generate_agent_reply` corregido. `state_manager.py` en Dockerfile. Volumen `~/.english-bot` en docker-compose. `OLLAMA_URL` env para Docker.
- **Resultado:** Bot arranca sin crash; estado persiste en contenedor.

---

## Decisiones Pendientes / Por Revisar

| Tema | Estado | Nota |
|------|--------|------|
| Velocidad TTS configurable | Pendiente | Añadir `tts_speed` en user_config |
| Voces por agente editables | Pendiente | Editar voices en state.json |
| Límite historial (50) ajustable | Pendiente | Configurable en state.json |
| Logs estructurados (JSON) | Pendiente | Para debugging producción |
| Métricas de uso (prometheus) | Pendiente | Opcional futuro |