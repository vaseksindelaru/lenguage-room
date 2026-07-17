---
type: hermes-config
version: 1.0
created: "2026-07-17"
---

# Hermes ↔ Obsidian Integration

## ✅ Configuración Verificada

- [x] Vault creado en `~/Documents/Obsidian-Vault`
- [x] Variable `OBSIDIAN_VAULT_PATH` configurada
- [x] Git inicializado para sync
- [x] Skill `obsidian` cargado
- [x] Hermes puede leer/escribir en el vault

## 📋 Reglas de Convivencia

### Hermes PUEDE:
- ✅ Leer cualquier nota del vault para contexto
- ✅ Crear notas en `Inbox/`, `Books/`, `Hermes/`, `Reports/`
- ✅ Añadir secciones a notas existentes (con `patch`)
- ✅ Buscar información en el vault con `search_files`

### Hermes NO DEBE:
- ❌ Borrar notas sin preguntar
- ❌ Modificar `_templates/` sin permiso
- ❌ Sobreescribir notas completas sin confirmar

## 🔍 Cómo Hermes Encuentra Información

Cuando pregunto algo, Hermes automáticamente:
1. Busca en su memoria interna (2,200 chars)
2. Si no encuentra → busca en este vault
3. Si encuentra → usa el contexto para responder
4. Si no encuentra → me lo dice y ofrece crear la nota
