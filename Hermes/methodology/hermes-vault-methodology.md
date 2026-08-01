---
title: Hermes Vault Configuration Methodology — Universal Project Template
date: 2026-08-01
category: Hermes/methodology
tags: [hermes, vault, methodology, template, universal, project-structure]
status: complete
---

# Hermes Vault Configuration Methodology — Universal Project Template

> **Propósito**: Estructura estándar para configurar cualquier proyecto con "pensamiento de Hermes" — vault local como source of truth, MOC como índice navegable, auto-sync via skills, sessions como log cronológico.

---

## 1. Estructura de Vault Universal (Mínima + Opcional)

```
/home/vaclav/Documents/Obsidian-Vault/
├── <PROJECT_NAME>/
│   ├── _<PROJECT>-MOC.md          # Mapa de contenido (ÍNDICE ÚNICO - OBLIGATORIO)
│   ├── sessions/                   # Logs cronológicos (YYYY-MM-DD-topic.md) - OBLIGATORIO
│   ├── notes/                      # Referencias, prompts, planes, docs varios - RECOMENDADO
│   ├── analysis/                   # Reports, graphs, análisis técnicos - OPCIONAL
│   ├── learning/                   # Clases, tutoriales, conocimiento teórico - OPCIONAL
│   │   └── tutor-methodology/      # Metodologías específicas (solo proyectos complejos tipo CGAlpha)
│   ├── development/                # Roadmap, tasks, arquitectura - OPCIONAL
│   └── .git/                       # Git repo local (source of truth = local)
│
├── Hermes/                         # Proyecto Hermes interno
│   ├── _Hermes-MOC.md
│   ├── sessions/
│   └── Welcome.md
│
└── <OTRO_PROYECTO>/               # Mismo patrón para cada proyecto
```

### Convenciones de naming:
| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| Carpeta proyecto | PascalCase | `CGAlpha`, `KRK9`, `MyProject` |
| MOC | `_<Project>-MOC.md` | `_CGAlpha-MOC.md` |
| Sesiones | `sessions/YYYY-MM-DD-topic.md` | `2026-08-01-restart-fix.md` |
| Notes | `notes/descriptive-name.md` | `notes/PLAN_feature.md` |
| Analysis | `analysis/report-name.md` | `analysis/graph-report.md` |
| Learning (opcional) | `learning/NN-name.md` | `learning/01-intro.md` |
| Development (opcional) | `development/NN-topic.md` | `development/01-roadmap.md` |

**Regla**: Solo crea `learning/` y `development/` si el proyecto los necesita (ej: CGAlpha análisis complejo). Proyectos simples usan solo `sessions/`, `notes/`, `analysis/`.

---

## 2. MOC Template (Map of Content)

Cada proyecto tiene un `_<PROJECT>-MOC.md` con esta estructura base:

```markdown
---
type: project-moc
project: <PROJECT_NAME>
tags:
  - proyecto/<project-lower>
  - moc
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

# 🟢 <PROJECT_NAME> — Índice del Proyecto (MOC)

> [!info] Punto de entrada. Todo vive bajo `<PROJECT_NAME>/`.
> Sesiones en `<PROJECT_NAME>/sessions/` con tag `#proyecto/<project-lower>`.
> Repo: `<github-repo>` | Local: `<local-path>`

## 📌 Qué es
<Resumen ejecutivo 1-2 líneas>

## 🔑 Datos clave (fuente de verdad)
- **Dato crítico 1**: valor
- **Dato crítico 2**: valor
- **Config importante**: path, comando, versión

## 🧩 Componentes (si aplica)
| Componente | Descripción | Ubicación |
|------------|-------------|-----------|
| **Nombre** | Qué hace | `path/` |

## 🗂️ Sesiones (cronológico)
- `<PROJECT_NAME>/sessions/YYYY-MM-DD-topic.md` — Descripción
- Ver todas: buscar `path:<PROJECT_NAME>/sessions`

## 📋 Referencias (notes/)
| Archivo | Descripción |
|---------|-------------|
| `notes/plan.md` | Plan técnico |
| `notes/prompt.md` | Prompt clave |

## 📊 Análisis (analysis/) — si aplica
- **Fecha**: YYYY-MM-DD
- **Stats**: métricas clave
- **Guardado en**: `analysis/report.md`

## 📚 Learning (learning/) — SOLO si proyecto complejo
- **Índice**: `learning/00-índice.md`
- **01** — Nombre (descripción)

> 📖 Lee en orden. Cada clase construye sobre la anterior.

## 🔧 Development (development/) — SOLO si roadmap activo
- **Índice**: `development/00-roadmap.md`
- **01** — Tarea (estado)

## ⏭️ Pendientes
- [ ] Tarea accionable con referencia a archivo

## 🔗 Referencias externas
- Repo: `<git-url>`
- Skill: `<project>-vault-auto`
- Cron: `<project>-moc-sync`
```

---

## 3. Skill Auto-Sync Template

Para cada proyecto, crear skill en `~/.hermes/skills/devops/<project>-vault-auto/`:

### Estructura del skill:
```
~/.hermes/skills/devops/<project>-vault-auto/
├── SKILL.md
├── scripts/
│   ├── update_moc_sessions.py      # Core: escanea sessions/, actualiza MOC
│   ├── update-<project>-moc.sh     # Wrapper shell
│   └── git-hook-post-commit        # Hook opcional
└── references/
    └── usage.md
```

### SKILL.md template:
```yaml
---
name: <project>-vault-auto
description: Auto-load <PROJECT> vault context and keep MOC synchronized with sessions
version: "1.0"
triggers:
  - path_pattern: "<PROJECT_NAME>/**"
  - category: "<PROJECT_NAME>"
  - keyword: "vault"
  - keyword: "<project-lower>"
auto_load: true
---
```

### update_moc_sessions.py (adaptar):
- `sessions_dir = Path(vault_path) / "<PROJECT_NAME>" / "sessions"`
- `moc_path = Path(vault_path) / "<PROJECT_NAME>" / "_<PROJECT>-MOC.md"`
- Frontmatter tag: `last_updated:`
- Section header: `## 🗂️ Sesiones`

---

## 4. Cron Job Template

```bash
cronjob action=create \
  name="<project>-moc-sync" \
  schedule="*/15 * * * *" \
  prompt="Sync <PROJECT> MOC with session files" \
  skills=["<project>-vault-auto"] \
  workdir="/home/vaclav/Documents/Obsidian-Vault" \
  deliver="local"
```

---

## 5. Git Hook Template (opcional)

```bash
ln -sf ~/.hermes/skills/devops/<project>-vault-auto/scripts/git-hook-post-commit \
  /home/vaclav/Documents/Obsidian-Vault/.git/hooks/post-commit
chmod +x /home/vaclav/Documents/Obsidian-Vault/.git/hooks/post-commit
```

El hook detecta cambios en `<PROJECT>/sessions/*.md` y actualiza MOC en el mismo commit.

---

## 6. Flujo de Trabajo "Pensamiento Hermes"

### Al iniciar sesión en proyecto:
```
Tú: "continúa sesión vault/<project>"
Hermes: 
  1. Auto-carga skill <project>-vault-auto
  2. Lee _<PROJECT>-MOC.md
  3. Inyecta contexto: summary, key facts, latest sessions, pending
```

### Al guardar trabajo:
```
Tú: "guárdalo en Obsidian"
Hermes:
  1. write_file(<PROJECT>/sessions/YYYY-MM-DD-topic.md, content)
  2. terminal("python3 ~/.hermes/skills/devops/<project>-vault-auto/scripts/update_moc_sessions.py")
  3. git push origin <project>-vault
```

### Para nuevo proyecto (setup inicial):
```
Tú: "nuevo proyecto vault <ProjectName>"
Hermes:
  1. Crea estructura de carpetas (mínima: sessions/, notes/)
  2. Crea _<Project>-MOC.md desde template
  3. Crea skill <project>-vault-auto desde template
  4. Crea cron job <project>-moc-sync
  4. (Opcional) Instala git hook
```

---

## 7. Comandos de Invocación Rápida

### Para abrir/continuar proyecto existente:
```
"continúa sesión vault/cgalpha"
"continúa sesión vault/krk9"
"abre proyecto vault <ProjectName>"
```

### Para crear nuevo proyecto con esta estructura:
```
"nuevo proyecto vault MiProyecto"
# O paso a paso:
"crea estructura vault para MiProyecto"
"crea skill mi-proyecto-vault-auto"
"crea cron mi-proyecto-moc-sync"
```

### Para ajustar proyecto existente a esta estructura:
```
"migra proyecto vault <ProjectName> a estructura estándar"
"aplica metodología hermes-vault a <ProjectName>"
```

---

## 8. Checklist Setup Nuevo Proyecto (Mínimo Viable)

- [ ] Carpeta `/home/vaclav/Documents/Obsidian-Vault/<ProjectName>/`
- [ ] `_<ProjectName>-MOC.md` con template base
- [ ] Subcarpetas **obligatorias**: `sessions/`, `notes/`
- [ ] Subcarpetas **opcionales**: `analysis/`, `learning/`, `development/`
- [ ] Skill `~/.hermes/skills/devops/<project>-vault-auto/`
  - [ ] `SKILL.md` con triggers correctos
  - [ ] `scripts/update_moc_sessions.py` adaptado
  - [ ] `scripts/git-hook-post-commit`
- [ ] Cron job `<project>-moc-sync` creado
- [ ] (Opcional) Git hook instalado en vault repo
- [ ] Rama git `<project>-vault` en origin
- [ ] Push inicial: `git push origin <project>-vault`

---

## 9. Principios Rectores

| Principio | Aplicación |
|-----------|------------|
| **Local = Source of Truth** | Vault local es autoridad; remoto = backup |
| **MOC = Índice Único** | Un archivo por proyecto que lo resume todo |
| **Sessions = Log Inmutable** | Una file por sesión, nunca editar pasado |
| **Auto-sync > Manual** | Skills + cron + hooks eliminan olvido humano |
| **Estructura = Pensamiento** | Misma estructura base = mismo modelo mental |
| **Tags = Navegación** | `#proyecto/<name>` permite búsqueda cross-proyecto |
| **Mínimo Viable** | Solo `sessions/` + `notes/` obligatorios; resto opcional |

---

## 10. Referencias en este Vault

- **CGAlpha** (complejo, con learning/development): `CGAlpha/_CGAlpha-MOC.md`, skill `cgalpha-vault-auto`
- **KRK9** (simple, sessions + notes + analysis): `KRK9/_KRK9-MOC.md`, skill `krk9-vault-auto`
- **Hermes internal**: `Hermes/_Hermes-MOC.md`, skill `hermes-vault-auto`
- **Methodology source**: Esta nota (`Hermes/methodology/hermes-vault-methodology.md`)

---

*Esta metodología nació de la implementación real en CGAlpha/KRK9 (2026-08-01) y se generaliza como template universal. Usa estructura mínima obligatoria + carpetas opcionales según complejidad del proyecto.*