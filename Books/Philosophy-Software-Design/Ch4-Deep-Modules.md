---
source: "A Philosophy of Software Design, 2nd Edition"
author: "John K. Ousterhout"
chapter: 4
title: "Modules Should Be Deep"
---

# Modules Should Be Deep

## 🎯 Principio Fundamental

> *"The best modules are those that provide powerful functionality yet have simple interfaces."*

Un **módulo profundo** (deep module) = mucha funcionalidad oculta tras una interfaz simple.  
Un **módulo superficial** (shallow module) = interfaz compleja para poca funcionalidad.

```
Módulo PROFUNDO:        Módulo SUPERFICIAL:
┌──────────────┐        ┌──────┐
│  Interfaz    │        │Interf│ 
│  simple      │        │comple│
├──────────────┤        ├──────┤
│              │        │      │
│  MUCHA       │        │ poca │
│  funcional.  │        │ func │
│              │        │      │
└──────────────┘        └──────┘
```

## ✅ Ejemplo: Unix I/O (Módulo Profundo)

Solo **5 syscalls** con firmas simples, pero miles de líneas de implementación:

```c
int open(const char* path, int flags, mode_t permissions);
ssize_t read(int fd, void* buffer, size_t count);
ssize_t write(int fd, const void* buffer, size_t count);
off_t lseek(int fd, off_t offset, int referencePosition);
int close(int fd);
```

La implementación maneja: filesystems, permisos, caching, scheduling, dispositivos...

## ❌ Ejemplo: Método Superficial

```java
private void addNullValueForAttribute(String attribute) {
    data.put(attribute, null);
}
```

Este método **empeora** la complejidad:
- No oculta nada (toda la funcionalidad visible en la interfaz)
- Agrega una interfaz nueva que aprender
- No da ningún beneficio compensatorio

> 🚩 **Red Flag:** Si el Javadoc es más largo que el código del método, es módulo superficial.

## 🔑 Conceptos Clave

- **Interfaz formal**: firmas, tipos, parámetros (el lenguaje las fuerza)
- **Interfaz informal**: comportamiento de alto nivel, restricciones, orden de llamadas (requiere comentarios)
- **Abstracción**: vista simplificada que omite detalles NO importantes
- **Falsa abstracción**: omite detalles que SÍ son importantes → oscuridad

## 📋 Checklist de Diagnóstico

Para evaluar si un módulo es profundo o superficial:

- [ ] ¿La interfaz es significativamente más simple que la implementación?
- [ ] ¿Puedo cambiar la implementación sin tocar la interfaz?
- [ ] ¿Los usuarios necesitan saber poco para usar el módulo?
- [ ] ¿El módulo oculta decisiones de diseño complejas?
- [ ] ¿La documentación necesaria es menor que el código implementado?