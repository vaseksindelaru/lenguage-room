---
type: project-moc
project: Hermes
tags:
  - proyecto/hermes
  - moc
created: 2026-07-20
last_updated: 2026-08-01
---

# 🟣 Hermes + Obsidian (Mejoras & Aprendizaje) — Índice del Proyecto (MOC)

> [!info] Punto de entrada del proyecto. Todo lo de mejoras a Hermes y
> aprender a usar Obsidian vive bajo `Hermes/`.
> Cada sesión va en `Hermes/sessions/` con tag `#proyecto/hermes`.

## 📌 Qué es
Configuración, mejoras y flujo de trabajo de Hermes Agent + aprender a usar
Obsidian como "segundo cerebro" compartido con Hermes.

## 🔑 Datos clave (fuente de verdad)
- Vault REAL: `~/Documents/Obsidian-Vault` (guion, sin acento). ⚠️ NO confundir
  con `~/Documentos/Obsidian Vault` (vault de prueba vacío).
- `OBSIDIAN_VAULT_PATH` en `~/.hermes/.env`
- Obsidian AppImage v1.12.7 en `~/Applications/Obsidian.AppImage`
- Regla de arranque: Hermes lee `Hermes/sessions/` al iniciar sesión.
- **Metodología universal**: `Hermes/methodology/hermes-vault-methodology.md` — template para cualquier proyecto

## 🗂️ Sesiones
- `Hermes/sessions/2026-07-20-organizacion-3-proyectos.md` — Organizacion 3 Proyectos
- `Hermes/sessions/2026-07-19-obsidian-hermes.md` — Obsidian Hermes
- `Hermes/sessions/2026-07-19-bc-autoload.md` — Bc Autoload
- Ver todas: buscar `path:Hermes/sessions`

## 📚 Learning (Clases/Tutoriales)
- **Índice**: `learning/00-índice.md` (pendiente)
- **01** — Hermes Basics (config, skills, tools)
- **02** — Obsidian Integration (vault, MOC, sessions)
- **03** — Vault Methodology (esta metodología universal)

> 📖 Lee en orden. Cada clase construye sobre la anterior.

## 🔧 Development (Roadmap activo)
- **Índice**: `development/00-roadmap.md` (pendiente)
- **01** — Auto-load MOC context on session start (skill: cgalpha-vault-auto pattern)
- **02** — Session continuation protocol (MOC → context injection)
- **03** — Cross-project vault search skill

## 🔗 Conocimiento aplicado
- [[Hermes/methodology/hermes-vault-methodology.md|Metodología Universal Hermes Vault]]

## ⏭️ Pendientes verificados
- [ ] Crear repo Git remoto para vault
- [ ] Migrar `Hermes/Sessions/` → `Hermes/sessions/` (lowercase)
- [ ] Crear skill `hermes-vault-auto` desde template
- [ ] Crear cron `hermes-moc-sync`
- [ ] Aplicar metodología a KRK9/Discord-Bot project

## 🔄 Auto-Update Workflow
1. Skill `hermes-vault-auto` auto-loads on `Hermes/**` paths
2. Cron `hermes-moc-sync` cada 15 min sincroniza MOC
3. Git hook post-commit actualiza MOC en commits con cambios en sessions/
4. Al guardar: `write_file(Hermes/sessions/...) → update_moc_sessions() → push`

---

*Actualizado a metodología universal 2026-08-01 — ver `Hermes/methodology/hermes-vault-methodology.md`*