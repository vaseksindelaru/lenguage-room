---
type: project-moc
project: CGAlpha
tags:
  - proyecto/cgalpha
  - moc
created: 2026-07-20
---

# 🟢 CGAlpha v3 — Índice del Proyecto (MOC)

> [!info] Punto de entrada del proyecto. Todo lo de CGAlpha vive bajo `CGAlpha/`.
> Cada sesión de trabajo va en `CGAlpha/Sessions/` con tag `#proyecto/cgalpha`.

## 📌 Qué es
Sistema de trading algorítmico. BTCUSDT 5min, estrategia de triple coincidencia.

## 🔑 Datos clave (fuente de verdad)
- **Features reales del oracle**: 23 (12 extra vs 11 esperado). NO usa `l2tp_*`.
- `test_oracle_encoding.py` está en `/tests/` (root), NO en `cgalpha_v3/tests/`.
- Los tests fallan porque se añadieron features DESPUÉS de escribir los tests.
- Hay `.venv` en el proyecto — usar para pytest.

## 🗂️ Sesiones
- _(aún sin sesiones registradas aquí — las nuevas irán apareciendo abajo)_
- Ver todas: buscar `path:CGAlpha/Sessions`

## 🔗 Conocimiento aplicado
- [[Books/Philosophy-Software-Design/Applied-to-CGAlpha|Ousterhout aplicado a CGAlpha]]

## ⏭️ Pendientes
- [ ] Procesar más capítulos de Ousterhout (2,3,5,9,10,20) aplicados a CGAlpha
- [ ] Reconciliar tests con las 23 features reales

## 📊 Graphify Analysis
- **Analysis date**: 2026-07-25
- **Graph files**: `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json`
- **Stats**: 2798 nodes · 5671 edges · 152 communities
- **Saved in vault**: `graph-analysis-20260725-131118.html`, `graph-report-20260725-131118.md`, `graphify-notes-20260725.md`
- **Install guide**: `graphify/doc` (from graphify.com — installation and usage docs)

## 🔄 Auto-Update Workflow
- Run `graphify update .` after every approved code change
- Re-generate HTML and save to vault
- Use `graphify query "..."` for deep exploration
- Use `graphify explain "NodeName"` for node details
- MCP server: `python -m graphify.serve graphify-out/graph.json` for multi-assistant access
