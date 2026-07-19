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

### Hermes DEBE (regla de arranque, 2026-07-19):
- ✅ En el PRIMER mensaje de cada sesión, leer `Hermes/Sessions/` (search_files o última nota) y retomar contexto
- ✅ Si el usuario dice "inicie la sesion"/"retoma"/"continúa" → leer vault SIN que lo pidan explícitamente con ruta
- ✅ Ante ambigüedad de arranque, leer el vault de todos modos (no fiarse solo de memoria interna)
- ✅ Para CGAlpha: fuente de verdad = Obsidian, NO memoria interna (esta tiene datos desactualizados)

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
