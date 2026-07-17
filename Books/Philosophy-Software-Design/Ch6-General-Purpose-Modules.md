---
source: "A Philosophy of Software Design, 2nd Edition"
author: "John K. Ousterhout"
chapter: 6
title: "General-Purpose Modules are Deeper"
---

# General-Purpose Modules are Deeper

## 🎯 Principio Fundamental

> *"The sweet spot is to implement modules that are somewhat general-purpose. The module's functionality should reflect your current needs, but its interface should be general enough to support multiple uses."*

Un módulo con interfaz **general-purpose** es más profundo que uno con interfaz especializada.

## ✅ Ejemplo del Libro: Editor de Texto

**Enfoque Especializado (superficial):**
```java
void backspace(Cursor cursor);     // Solo borra un carácter
void delete(Cursor cursor);        // Solo elimina selección
```

**Enfoque General-Purpose (profundo):**
```java
void insert(Position position, String newText);
void delete(Position start, Position end);
```
→ Con `delete(cursor, cursor+1)` logras lo mismo que `backspace`, pero la interfaz sirve para mucho más.

## 🔑 Preguntas Clave para Diseñar

Al diseñar un módulo, preguntarse:

1. **¿Cuál es la interfaz más simple que cubre todas mis necesidades actuales?**
   - Si reduces métodos, la interfaz es más simple
   - Si cada método es general-purpose, necesitas menos métodos

2. **¿En cuántas situaciones se usará este método?**
   - Si solo en UNA → probablemente es demasiado especializado

3. **¿Esta API es cómoda de usar para mis necesidades actuales?**
   - No sacrifiques usabilidad por generalidad excesiva

## 🔴 Red Flag: Métodos Demasiado Especializados

> 🚩 Si un método tiene un nombre muy específico como `backtestWith5MinBtcusd()` → debería ser `backtest(symbol, timeframe)`.

## 📋 Checklist

- [ ] ¿La interfaz sirve para más casos de uso que el actual?
- [ ] ¿Puedo eliminar métodos especializados reemplazándolos por uno general?
- [ ] ¿El nombre del método describe QUÉ hace, no CUÁNDO se usa?
- [ ] ¿Hay constantes hardcodeadas que deberían ser parámetros?