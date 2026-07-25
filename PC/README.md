# PC - Registro de Mantenimiento

---

## Sesión: Limpieza de rendimiento (25 Jul 2026)

### Diagnóstico
- Disco /dev/sda3 al 95% (105G de 117G usados, solo 6.1 GB libres)
- Causa raíz: espacio insuficiente para buffers del SO y navegadores
- RAM: 15G, sinproblemas (9.3 GB disponibles)
- Swap: 2G, 39M usado, OK

### Limpieza ejecutada
1. Cachés de navegadores (Chrome, Brave, Edge): ~3.1 GB
2. npm cache: ~890 MB
3. uv cache: ~890 MB
4. Docker imágenes no usadas (ollama 4.75GB, extras): ~4.7 GB
5. apt clean + journal vacuum: ~50 MB
6. Extensiones VS Code: 3.3 GB
7. Repo mcp-for-beginners: 3.8 GB

### Resultado
- Uso de disco: 95% → 81% (6 GB → 22 GB libres)
- Comandos: rm -rf, npm cache clean --force, apt clean, docker image prune -a -f, journalctl --vacuum-size=100M

### Notas
- Disco es HDD (velocidad ~19 MB/s escritura secuencial)
- Load average ~5.7 en 4 CPUs (dentro de normalidad con browsers abiertos)
- Próximo paso opcional: migrar a SSD para mejora drástica de velocidad
