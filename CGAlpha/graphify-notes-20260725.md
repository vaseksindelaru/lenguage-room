---
date: 2026-07-25
session: graphify-cgalpha-analysis
topic: Graphify installation, CGAlpha analysis, and LLM evaluator findings for next development steps
tags:
  - proyecto/cgalpha
  - graphify
  - analysis
  - next-steps
model: inclusionai/ling-3.0-flash:free (openrouter)
---

# Graphify & CGAlpha Analysis

## Graphify Setup

- **Installed**: `uv tool install graphifyy` → `graphify` CLI at `/home/vaclav/.local/bin/graphify`
- **Docs**: https://graphify.com/docs
- **Analysis run**: `graphify . --code-only` in `/home/vaclav/CGAlpha_0.0.1-Aipha_0.0.3/`
- **Results**: 2798 nodes, 5671 edges, 152 communities (94% EXTRACTED, 6% INFERRED)
- **Output files**:
  - `graphify-out/graph.html` (2.9MB interactive graph) → saved to Obsidian vault at `CGAlpha/graph-analysis-20260725-131118.html`
  - `graphify-out/GRAPH_REPORT.md` (51KB architecture report) → saved to `CGAlpha/graph-report-20260725-131118.md`
  - `graphify-out/graph.json` (3.4MB machine-readable graph)

## Graphify Key Concepts for CGAlpha Analysis

1. **Nodes** = symbols (classes, functions, files) — 2798 total
2. **Edges** = imports, calls, references — 5671 total
3. **Communities** = auto-detected modules/clusters — 152 found
4. **Confidence tags**: EXTRACTED (grounded in code), INFERRED (graph-based guess), AMBIGUOUS
5. **God nodes** = most connected nodes (entry points / hubs)
6. **`graphify query "X"`** — natural language queries against the graph with path citations
7. **`graphify path "A" "B"`** — shortest path between two symbols
8. **`graphify explain "X"`** — plain-language explanation of a node and its neighbors
9. **`graphify update .`** — re-scan after code changes (no API cost, local only)

## CGAlpha Project State (per LLM Evaluator)

### Key Findings from Evaluator Chat

1. **Fase real según evidencia**: Reconstrucción gobernada del Oracle (v6, Fase A/B) bajo marco constitucional de gobernanza
2. **IDENTITY Memory (Paso 1)**: COMPLETADO — tiene 11 ADRs viviendo en `aipha_memory/identity/`, no solo el mantra original
3. **La evaluación externa está obsoleta**: no coincide con estado real del repo
4. **6 tests failing**: 5 explicados por evolución intencional + 1 genuino (`test_clearance_instrumentation_robust` — max_price_since_detection 10200 vs 10100 esperado)

### El bug encontrado por el evaluador

- **Causa raíz**: En `process_stream()`, el loop no valida `idx >= zone.candle_index` antes de intentar retest
- **Efecto**: Una zona inyectada antes de arrancar el loop se trata como si llevara existiendo desde idx=0, disparando un retest falso
- **Bug de fixture del test, no regresión de producción** — samples reales no contaminados
- **Fix recomendado**: Ajustar `zone.candle_index=0` en el fixture O procesar en dos tramos

### Principios reitores documentados en crónica del proyecto
- "Instrumentar antes de filtrar"
- "Los filtros se añaden después de medir"
- "LLM como fuente de verdad" → parsing estático, no generación de texto

## Next Steps Decision Needed

### Opción A: Seguir el camino propuesto por el evaluador
Investigar el único bug genuino abierto (`max_price_since_detection` en `test_clearance_instrumentation.py`) como prioridad antes de cualquier nueva feature.

### Opción B: Repaso profundo de CGAlpha antes de seguir
Usar graphify para mapear todas las relaciones del programa y entender el estado actual antes de decidir qué sigue.

### Opción C: Ambos caminos en paralelo
Investigar el bug Y hacer repaso profundo con graphify simultáneamente.

## Graphify Queries Recomendadas para CGAlpha

1. `graphify query "¿qué conecta auth con la base de datos?"` — encontrar dependencias clave
2. `graphify path "OracleTrainerV3" "OracleV6Base"` — entender relación entre versiones del oracle
3. `graphify path "EvolutionOrchestratorV4" "CodeCraftSage"` — entender wiring del orchestrator
4. `graphify explain "max_price_since_detection"` — entender el feature del bug
5. `graphify cluster-only .` — regenerar reporte cuando cambien comunidades
6. `graphify update .` — re-escanear después de cada cambio de código

## Auto-Update Plan

- Cada vez que haya cambios de código aprobados → ejecutar `graphify update .`
- Guardar HTML en vault de Obsidian CGAlpha
- MCP server disponible para consultas desde cualquier asistente
- Cloud sync vía Obsidian sync (ya configurado para vault)