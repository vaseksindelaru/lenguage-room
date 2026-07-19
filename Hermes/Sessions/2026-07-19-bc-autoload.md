---
type: hermes-session
date: "2026-07-19"
project: "Obsidian + Hermes — Auto-lectura y corrección de memoria"
model: "tencent/hy3:free (OpenRouter)"
continuation_of: "2026-07-19-obsidian-hermes.md"
---

# Sesión 2026-07-19 (B+C) — Arranque automático + limpieza de memoria

## 🎯 Objetivo

Resolver que las sesiones nuevas de Hermes NO conectaban con Obsidian y
dependían de memoria interna desactualizada (decía `l2tp_*` para CGAlpha,
pero el código real tiene 23 features, 12 extra vs 11 esperado, SIN l2tp_).

## 🔍 Diagnóstico

- La sesión nueva del usuario arrancó en blanco y usó SOLO la memoria interna
  (`memories/MEMORY.md`), ignorando Obsidian. Respondió con el resumen viejo
  de CGAlpha (Paso 1, l2tp_*).
- IMPORTANTE: MEMORY.md YA estaba corregido el 2026-07-19 (línea 9 decía
  dato real 23 features, NO l2tp_). Pero la sesión nueva usó una versión
  vieja/contaminada de la memoria. Confirma: memoria interna es INESTABLE.
- `hooks/` de Hermes está VACÍO → no hay sistema de hook de arranque nativo.
- `config.yaml` no tiene campo `system_prompt` → no se puede inyectar
  auto-lectura nativa de forma garantizada.

## 💻 Solución aplicada (B + C)

### B — Auto-lectura al arrancar
- No hay hooks ni system_prompt → vía MEMORY.md (se inyecta cada turno):
  regla OBLIGATORIA de leer `Hermes/Sessions/` en el primer mensaje o ante
  "inicie la sesion"/"retoma"/"continúa", SIN pedir ruta explícita.
- Documentado también en `Hermes/Welcome.md` (regla de arranque).

### C — Corregir memoria interna
- `memories/MEMORY.md` línea 9: eliminada mención a l2tp_ como errónea,
  reforzado "Fuente de verdad = Obsidian (Hermes/Sessions/), NO memoria interna".
- Línea 13 (Obsidian): reemplazada regla vieja "usuario debe pedir explícito"
  por regla obligatoria de auto-lectura.

## 📝 Próximo paso (pendiente de probar)

- [ ] Cerrar y abrir chat nuevo, decir SOLO "inicie la sesion" → verificar que
      Hermes SÍ lee Obsidian esta vez (gracias a la regla en MEMORY.md).
- [ ] Si falla, considerar cron job al iniciar o script de bootstrap que
      escriba contexto en un archivo que Hermes lea en turno 1.

## 🔗 Referencias
- [[2026-07-19-obsidian-hermes]] — sesión previa (instalación)
- [[Hermes/Welcome]] — reglas actualizadas
