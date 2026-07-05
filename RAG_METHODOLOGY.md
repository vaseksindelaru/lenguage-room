# Metodología RAG por Práctica Iterativa

## Principio
"Aprender haciendo, no planificando."

## Ciclo de Práctica (1 semana por ciclo)

### Semana 1: Ingestión Mínima
- **Objetivo:** Ingerir 1 documento (PDF/MD/TXT < 50KB)
- **Herramienta:** langchain + chromadb local
- **Test:** "¿De qué trata el doc?" → respuesta coherente
- **Métrica:** Relevancia > 80% (evaluación manual)

### Semana 2: Recuperación Básica
- **Objetivo:** Retrieval top-k + prompt injection
- **Test:** Pregunta específica → cita exacta del doc
- **Métrica:** Cita correcta > 70%

### Semana 3: Contexto Conversacional
- **Objetivo:** Historial + RAG combinado
- **Test:** Conversación de 5 turnos usando el doc
- **Métrica:** Coherencia > 75%

### Semana 4: Multi-documento
- **Objetivo:** 3–5 docs relacionados
- **Test:** Síntesis entre docs
- **Métrica:** Síntesis correcta > 70%

## Regla de Oro
No avanzar de semana hasta que la actual funcione en producción real.
Si falla → repetir semana con ajustes mínimos.

## Stack Técnico (fijo)

| Componente | Valor |
|------------|-------|
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (384-dim, local) |
| Vector DB | chromadb → `~/.english-bot/chroma/` |
| Chunking | 500 tokens, overlap 50 |
| Retrieval | top-3, threshold 0.7 |
| Prompt template | `prompts/rag_chat.j2` (Jinja2) |

## Integración futura con Bot (referencia)
- `!rag add <archivo>` → ingiere documento
- `!rag list` → lista docs
- `!rag clear` → limpia índice
- En chat: mensaje con `[RAG]` → inyecta contexto automático