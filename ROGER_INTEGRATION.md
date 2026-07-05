# Integración Roger — Contrato de Interfaz (Stub)

> **NO implementar aún.** Este documento define el contrato para integración futura.
> Solo se implementa cuando Roger exponga API estable.

---

## Contexto
- **Roger**: Sistema de análisis de mercado en `/home/vaclav/Q/roger/roger-main/`
- **English Bot**: Práctica conversacional con contexto
- **Objetivo**: Roger provee contexto macro/mercado → English Bot usa ese contexto en conversación

---

## Contrato de Interfaz (Stub)

```python
# roger_interface.py — NO IMPLEMENTAR AÚN
class RogerInterface:
    """
    Integración futura con Roger (/home/vaclav/Q/roger/roger-main/).
    
    Roger provee: análisis de mercado, señales, contexto macro.
    English Bot provee: práctica conversacional con ese contexto.
    """
    
    async def get_market_context(self) -> dict:
        """
        Retorna contexto de mercado actual.
        
        Returns:
            dict: {
                'topic': 'BTC',           # Asset principal
                'trend': 'bullish',       # 'bullish' | 'bearish' | 'neutral'
                'key_levels': [60000, 62000, 65000],  # Niveles clave
                'narrative': '...',       # Resumen narrativo 2-3 frases
                'volatility': 'medium',   # 'low' | 'medium' | 'high'
                'timestamp': '2026-07-05T21:30:00'  # ISO format
            }
        """
        raise NotImplementedError
    
    async def inject_context(self, context: str) -> None:
        """
        English Bot envía su contexto conversacional a Roger.
        
        Args:
            context: Resumen de la conversación actual (tema, puntos clave, dudas)
        """
        raise NotImplementedError
    
    async def on_topic_change(self, new_topic: str) -> None:
        """
        Notifica a Roger del cambio de tema en la conversación.
        
        Args:
            new_topic: Nombre del nuevo tema (ej. 'Crypto & Markets')
        """
        raise NotImplementedError


# Punto de integración en English Bot (futuro)
async def maybe_update_roger_context():
    """Llamar periódicamente o al cambiar tema."""
    if ROGER_ENABLED:
        roger = RogerInterface()
        market = await roger.get_market_context()
        # Inyectar en prompt del agente Sam/Maya cuando hablen de mercados
        # ...
```

---

## Flujo de Integración (Futuro)

```
┌─────────────────┐     get_market_context()      ┌─────────────────┐
│   English Bot   │ ─────────────────────────────▶ │      Roger      │
│                 │ ◀───────────────────────────── │  (Market Data)  │
│  Conversación   │     {topic, trend, levels,     │                 │
│  con contexto   │      narrative, volatility}     │  Análisis       │
└─────────────────┘                                └─────────────────┘
         │                                                ▲
         │ inject_context()                               │
         │ "Usuario practicando vocabulario crypto..."    │
         └────────────────────────────────────────────────┘
```

---

## Puntos de Integración en English Bot

| Evento | Acción |
|--------|--------|
| Inicio de sesión | `roger.get_market_context()` → inyectar en prompt de Sam/Maya |
| Cambio de tema `!topic` | `roger.on_topic_change(new_topic)` |
| Usuario menciona "BTC/ETH/market" | Inyectar `market_context` en prompt del siguiente agente |
| Cada 30 min | Refrescar `get_market_context()` |

---

## Reglas de Integración

| Regla | Descripción |
|-------|-------------|
| **No implementar hasta API estable** | Roger debe exponer endpoint REST/WebSocket documentado |
| **Fail-safe** | Si Roger falla → English Bot sigue funcionando sin contexto |
| **Rate limit** | Máx 1 llamada/min a Roger |
| **Timeout** | 5s máximo por llamada |
| **Cache** | Cachear respuesta 5 min para evitar spam |

---

## Próximos Pasos (Cuando Roger esté listo)

1. Roger expone API REST en `http://localhost:XXXX/api/v1/market`
2. Implementar `RogerInterface` real con `httpx.AsyncClient`
3. Añadir `ROGER_ENABLED` y `ROGER_API_URL` a `.env.example`
4. Test de integración: cambiar tema a "Crypto" → verificar inyección
5. Documentar en `ROGER_INTEGRATION.md` los endpoints exacto