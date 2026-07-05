# Test Suite Manual — English Practice Bot

## Test 1: Inicio con un comando
- **Ejecutar:** `./start.sh` (local) o `./start.sh --docker`
- **Esperado:** Servicios up, URL `http://localhost:8081` visible en terminal
- **Resultado:** [x] PASS [ ] FAIL
- **Notas:** Local mode verificado 2026-07-05

## Test 2: Persistencia de sesión
- **Pasos:** Enviar 3 mensajes en Discord → `./start.sh --stop && ./start.sh`
- **Esperado:** Mensaje "Welcome back! Last session: [fecha]. Topic: [tema]. Resuming..." + historial conservado
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 3: Timing adaptativo
- **Pasos:** Forzar mensaje largo de agente (ej. `!speak` genera mensaje largo) → medir tiempo hasta siguiente mensaje
- **Esperado:** Mensaje largo (≥100 chars) → ≥8s antes del siguiente; mensaje corto (<30 chars) → ≥3s; nunca >15s
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 4: Sin rotación automática
- **Pasos:** Dejar bot 30+ min sin interactuar (no escribir en Discord, no tocar micrófono)
- **Esperado:** Cero mensajes nuevos de agentes en el canal
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 5: Comandos de tema
- **Pasos:** `!topic list` → `!topic 2` → `!topic next` → `!topic crypto`
- **Esperado:** Tema cambia correctamente, persiste en state.json tras reinicio
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 6: Comando !speak
- **Pasos:** `!speak` en Discord
- **Esperado:** Bots envían 1-2 mensajes de apertura sobre tema actual con delays adaptativos
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 7: Audio TTS funciona
- **Pasos:** Abrir `http://localhost:8081` → click "Test audio" → dar permiso micrófono → mantener 🎤 y hablar
- **Esperado:** Se escucha beep de test → al hablar se transcribe y aparece en Discord → bots responden con audio TTS (se oye en pestaña 8081)
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

## Test 8: Persistencia tras reinicio completo
- **Pasos:** `./start.sh --stop` → `./start.sh` → verificar estado
- **Esperado:** Historial, tema actual, pausa/tema_locked se restauran
- **Resultado:** [ ] PASS [ ] FAIL
- **Notas:** 

---

## Criterios de Aceptación por Fase

| Fase | Tests requeridos PASS |
|------|----------------------|
| 1 (Inicio + Persistencia) | Test 1, 2, 8 |
| 2 (Timing adaptativo) | Test 3 |
| 3 (Control temas) | Test 4, 5 |
| 4 (RAG metodología) | Archivo existe |
| 5 (Roger integración) | Archivo existe |
| Todos | Test 6, 7 |

---

## Registro de Pruebas

| Fecha | Fase | Test | Resultado | Observaciones |
|-------|------|------|-----------|---------------|
|       |      |      |           |               |