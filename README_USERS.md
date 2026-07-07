# KRK-9: English Practice Room — Guía para Usuarios

## ¿Qué es KRK-9?
Es una **sala de chat con 4 bots de IA** que te ayudan a practicar inglés. Hablas con ellos por Discord o por voz, y te corrigen amablemente.

## ¿Cuánto cuesta?
**$0**. Es gratis. Usa tu propia computadora.

## Instalación (paso a paso)

### 1. Descargar e instalar
Abre una terminal (Git Bash en Windows, Terminal en Mac/Linux) y ejecuta:
```bash
curl -fsSL https://raw.githubusercontent.com/vaseksindelaru/lenguage-room/main/install-krk9.sh | bash
```
Esto descarga e instala todo automáticamente.

### 2. Configurar (wizard)
Durante la instalación, el wizard te preguntará:
- **Discord Bot Token**: Necesitas crear un bot en Discord. [Mira este video](https://www.youtube.com/watch?v=Pbq7FFKYn8) o sigue los pasos abajo.
- **Channel ID y Guild ID**: Son los números de tu canal y servidor de Discord. [Cómo obtenerlos](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-).

### 3. Iniciar
Una vez configurado, ejecuta:
```bash
cd krk9
./start.sh
```
Abre tu navegador en: **http://localhost:8081**

## Cómo usar KRK-9

### Por Discord (texto)
1. Únete al servidor donde configuraste el bot.
2. Escribe un mensaje en el canal.
3. Los 4 bots (Alex, Maya, Jordan, Sam) te responderán.

### Por voz (navegador)
1. Abre **http://localhost:8081** en tu navegador.
2. Haz clic en **"Mantén para hablar"** y habla.
3. Tu voz se enviará a Discord automaticamente.

### Invitar amigos
1. En la página **http://localhost:8081**, haz clic en **"Invitar amigos"**.
2. Copia el enlace y compártelo.

## Solución de problemas

### "No puedo conectar el micrófono"
- Asegúrate de que el navegador tenga permisos de micrófono.
- Usa **Chrome** o **Edge** (tienen mejor soporte de voz).

### "Los bots no me responden"
- Verifica que el bot esté en línea (`./start.sh` debe estar corriendo).
- Revisa el archivo `.pids/bot.log` para ver errores.

### "Ollama no funciona"
- Asegúrate de haber ejecutado: `ollama pull qwen2.5:3b`
- O usa APIs externas (Cerebras, Groq) — son gratuitas y no requieren Ollama.

## Obtener ayuda
- **Issues en GitHub**: [https://github.com/vaseksindelaru/lenguage-room/issues](https://github.com/vaseksindelaru/lenguage-room/issues)
- **Discord**: Únete al servidor de soporte (pide el invite a Vaclav).

---
**¿Te gustaría aprender a modificar los bots?** Mira `README_DEVS.md` para desarrolladores.
