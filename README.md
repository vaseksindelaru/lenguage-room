# 🧠 Vault de Conocimiento — Vaclav + Hermes

Este vault es mi **segundo cerebro**, compartido entre yo y Hermes (mi agente AI).

## 📂 Estructura

| Carpeta | Propósito | ¿Quién escribe? |
|---------|-----------|----------------|
| `Inbox/` | Captura rápida, ideas | Ambos |
| `CGAlpha/` | Documentación del proyecto | Local |
| `Discord-Bot/` | KRK-9 y bots | Local |
| `Trading/` | Conceptos, estrategias | Local |
| `Books/` | Notas de libros y papers | Hermes |
| `Hermes/` | Coordinación con el agente | Ambos |
| `Daily/` | Notas diarias | Local |
| `Reports/` | Reportes automáticos | Hermes (servidor) |

## 🔄 Sincronización

- **Laptop ↔ Servidor**: vía Git (repositorio privado)
- **Hermes local**: lee/escribe directamente en el vault (`file tools`)
- **Hermes servidor**: lee/escribe vía Git pull/push

## 🎯 Workflow Diario

1. Abro Obsidian para tomar notas
2. Hermes consulta el vault cuando trabajo en código
3. Hermes crea notas de descubrimientos automáticamente
4. Git push al final del día
5. El servidor hace pull y puede actuar sobre tareas
