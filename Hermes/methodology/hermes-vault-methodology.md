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

## 1. Estructura de Vault Universal

```
/home/vaclav/Documents/Obsidian-Vault/
├── <PROJECT_NAME>/
│   ├── _<PROJECT>-MOC.md          # Mapa de contenido (índice único)
│   ├── sessions/                   # Logs cronológicos (YYYY-MM-DD-topic.md)
│   ├── learning/                   # Conocimiento teórico, clases, tutoriales
│   │   └── tutor-methodology/      # Metodologías específicas (opcional)
│   ├── development/                # Documentos de desarrollo activo, roadmap
│   ├── <project-assets>/           # HTML reports, graphs, análisis
│   └── .git/                       # Git repo local (source of truth = local)
│
├── Hermes/                         # Proyecto Hermes interno
│   ├── _Hermes-MOC.md
│   ├── Sessions/
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
| Learning | `learning/NN-name.md` | `learning/01-intro.md` |
| Development | `development/NN-topic.md` | `development/01-roadmap.md` |

---

## 2. MOC Template (Map of Content)

Cada proyecto tiene un `_<PROJECT>-MOC.md` con esta estructura:

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

## 📌 Qué es
<Resumen ejecutivo 1-2 líneas>

## 🔑 Datos clave (fuente de verdad)
- **Dato crítico 1**: valor
- **Dato crítico 2**: valor
- **Config importante**: path, comando, versión

## 🗂️ Sesiones
- `<PROJECT_NAME>/sessions/YYYY-MM-DD-topic.md` — Descripción
- Ver todas: buscar `path:<PROJECT_NAME>/sessions`

## 📚 Learning (Clases/Tutoriales)
- **Índice**: `learning/00-índice.md`
- **01** — Nombre (descripción)
- **02** — Nombre (descripción)

> 📖 Lee en orden. Cada clase construye sobre la anterior.

## 🔧 Development (Roadmap activo)
- **Índice**: `development/00-roadmap.md`
- **01** — Tarea (estado: fix listo/diagnóstico completo)
- **02** — Tarea (estado)

## 🔗 Conocimiento aplicado
- [[Books/Topic/Applied-to-<PROJECT>|Referencia externa aplicada]]

## ⏭️ Pendientes verificados
- [ ] Tarea accionable con referencia a archivo
- [ ] Decisión pendiente

## 📊 Análisis/Reports (si aplica)
- **Fecha**: YYYY-MM-DD
- **Archivos**: paths a reports
- **Stats**: métricas clave

## 🔄 Auto-Update Workflow
1. Comando para actualizar análisis
2. Regenerar y guardar en vault
3. Query/exploración commands
4. MCP server si aplica
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
# Crear cron job (una vez por proyecto)
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
# Instalar en vault repo:
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
  1. Crea estructura de carpetas
  2. Crea _<Project>-MOC.md desde template
  3. Crea skill <project>-vault-auto desde template
  4. Crea cron job <project>-moc-sync
  4. (Opcional) Instala git hook
```

---

## 7. Comandos de Invocación Rápida

### Para abrir/continuar proyecto existente:
```bash
# En chat Hermes:
"continúa sesión vault/cgalpha"
"continúa sesión vault/krk9"
"abre proyecto vault <ProjectName>"
```

### Para crear nuevo proyecto con esta estructura:
```bash
# En chat Hermes:
"nuevo proyecto vault MiProyecto"
# O paso a paso:
"crea estructura vault para MiProyecto"
"crea skill mi-proyecto-vault-auto"
"crea cron mi-proyecto-moc-sync"
```

### Para ajustar proyecto existente a esta estructura:
```bash
# En chat Hermes:
"migra proyecto vault <ProjectName> a estructura estándar"
"aplica metodología hermes-vault a <ProjectName>"
```

---

## 8. Checklist Setup Nuevo Proyecto

- [ ] Carpeta `/home/vaclav/Documents/Obsidian-Vault/<ProjectName>/`
- [ ] `_<ProjectName>-MOC.md` con template completo
- [ ] Subcarpetas: `sessions/`, `learning/`, `development/`
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
| **Estructura = Pensamiento** | Misma estructura = mismo modelo mental en todos los proyectos |
| **Tags = Navegación** | `#proyecto/<name>` permite búsqueda cross-proyecto |

---

## 10. Referencias en este Vault

- **CGAlpha implementation**: `CGAlpha/_CGAlpha-MOC.md`, skill `cgalpha-vault-auto`
- **Hermes internal**: `Hermes/_Hermes-MOC.md`, `Hermes/Sessions/`
- **Methodology source**: Esta nota (`Hermes/methodology/hermes-vault-methodology.md`)

---

*Esta metodología nació de la implementación real en CGAlpha (2026-08-01) y se generaliza como template universal para cualquier proyecto que use Hermes + Obsidian.*