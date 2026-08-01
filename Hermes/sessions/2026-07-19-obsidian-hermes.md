---
type: hermes-session
date: "2026-07-19"
project: "Obsidian + Hermes Integration"
model: "tencent/hy3:free (OpenRouter)"
---

# Sesión 2026-07-19 — Obsidian + Hermes: Instalación y Flujo de Trabajo

## 🎯 Objetivo de la Sesión

Configurar Obsidian como "segundo cerebro" compartido con Hermes, y establecer
el flujo para que Hermes pueda recordar contexto entre conversaciones distintas
y aplicar conocimiento de libros/papers a proyectos reales (CGAlpha, KRK-9).

## 🔍 Descubrimientos / Lo que hicimos

1. **Modelo KAT-Coder-Air V2.5**: se configuró en Hermes (`kwaipilot/kat-coder-air-v2.5`
   vía OpenRouter). La API key funcionaba (probado con curl). El problema inicial
   era que el modelo no se "cargaba" en la UI — se resolvió con `hermes config set`.

2. **Video YouTube Obsidian+Hermes**: no tenía subtítulos, no se pudo transcribir.
   Se dio versión propia mejorada de la integración basada en el skill `obsidian`.

3. **Dos agentes Hermes (local + servidor)**: se explicó arquitectura de vault
   compartido vía Git como puente. Ventajas: monitoreo 24/7, divider cómputo,
   continuidad de sesiones.

4. **Aprendizaje desde libros (concepto "Lila")**: DEMOSTRACIÓN REAL con
   "A Philosophy of Software Design" (Ousterhout). Se extrajeron cap 4 y 6 con
   `pdftotext`, se estructuraron en `Books/Philosophy-Software-Design/` y se
   aplicaron a CGAlpha (`shadow_trader.py`): detectados 4 problemas
   (método shallow `get_active_trade_count`, constantes hardcodeadas, código
   duplicado `_write_bridge_entry`, demasiados métodos públicos).

5. **Alternativas a Obsidian**: investigado costo (Obsidian es GRATIS; Sync $4/mes,
   Publish $8/mes, Commercial $50/año opcional). Alternativas: Foam (VS Code+Git),
   Logseq (open source+API), zk (CLI). Recomendación: Obsidian gratis + Git sync.

6. **INSTALACIÓN COMPLETA**:
   - Obsidian AppImage v1.12.7 en `~/Applications/Obsidian.AppImage`
   - Vault en `~/Documents/Obsidian-Vault` con estructura (Inbox, CGAlpha,
     Discord-Bot, Trading, Books, Hermes/Sessions, Daily, Reports, _templates)
   - Git inicializado (3 commits de prueba)
   - `OBSIDIAN_VAULT_PATH=/home/vaclav/Documents/Obsidian-Vault` en `~/.hermes/.env`
   - Prueba de integración: Hermes LEYÓ y ESCRIBIÓ en el vault ✓
   - Script auto-sync en `.obsidian/auto-sync.sh`
   - Icono de escritorio creado en `~/Escritorio/obsidian.desktop` + icono SVG

7. **Control de calidad**: Hermes debe pedir confirmación antes de escribir en vault.
   `Inbox/` como cuarentena. Borrar con `git rm` + commit.

## 💻 Código / Comandos Clave

```bash
# Leer/escribir vault desde Hermes (ya funciona)
OBSIDIAN_VAULT_PATH=/home/vaclav/Documents/Obsidian-Vault

# Sync manual
cd ~/Documents/Obsidian-Vault && git add -A && git commit -m "..." && git push

# Borrar nota del vault (y del git)
git rm Inbox/nota-basura.md && git commit -m "clean: remove noise"
```

## 📝 Decisiones Tomadas

- Usar Obsidian GRATIS + Git sync (NO Obsidian Sync de pago)
- Estructura de carpetas definida y creada
- Regla: Hermes pide confirmación antes de escribir en vault
- `Inbox/` como cuarentena antes de promover a carpetas reales

## 🔗 Referencias

- [[Hermes/Welcome]] — reglas de convivencia Hermes↔Obsidian
- [[Books/Philosophy-Software-Design/Index]] — notas del libro procesado
- [[Books/Philosophy-Software-Design/Applied-to-CGAlpha]] — diagnóstico real

## ⏭️ Próximos Pasos

- [ ] **Conectar servidor**: crear repo Git remoto (GitHub/GitLab privado),
      `git remote add origin`, push. Clonar en servidor, configurar
      `OBSIDIAN_VAULT_PATH` allá. (PENDIENTE — usuario decidió posponer hasta
      tener servidor listo o querer backup)
- [ ] Configurar auto-sync (cron en server para pull cada hora)
- [ ] Disciplina de sesiones: al terminar chat importante → "guarda resumen en
      Obsidian"; al abrir chat nuevo → "lee Hermes/Sessions/ y continúa"
- [ ] Procesar más capítulos de Ousterhout (2,3,5,9,10,20) aplicados a CGAlpha
- [ ] Limpieza mensual de `Inbox/` (opcional cron)
