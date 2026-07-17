---
applies_to: "CGAlpha v3"
source_book: "A Philosophy of Software Design"
diagnosed_by: "Hermes Agent"
date: "2026-07-16"
---

# Diagnóstico: Aplicando Ousterhout a CGAlpha

## 🔍 Problema 1: Método Shallow → `get_active_trade_count()`

**Código actual (shadow_trader.py:429-431):**
```python
def get_active_trade_count(self) -> int:
    """Returns count of currently open shadow trades."""
    return len(self.order_manager.active_positions)
```

### 📖 Lo que dice Ousterhout (Cap 4):

> *"A shallow module is one whose interface is relatively complex in comparison to the functionality that it provides."*

> 🚩 **Red Flag:** El Javadoc/docstring es más largo que el cuerpo del método.

### 🔴 Diagnóstico:

Este método **no oculta nada**. La funcionalidad completa es visible en su interfaz. El caller necesita saber que existe `order_manager.active_positions` para entender qué hace. Es igual de simple para el caller hacer `len(trader.order_manager.active_positions)` que llamar a este método.

**Costo:** Agrega 1 método más a la interfaz pública de `ShadowTrader` sin beneficio compensatorio.

### ✅ Solución propuesta:

**Opción A (recomendada):** Eliminar el método. El caller usa `len(trader.order_manager.active_positions)`.

**Opción B:** Si `order_manager` es privado, entonces el método SÍ tiene sentido porque oculta la implementación interna. En ese caso, renombrar `order_manager` a `_order_manager`.

---

## 🔍 Problema 2: Constantes Hardcodeadas → `TAKER_FEE_ROUND_TRIP`

**Código actual (shadow_trader.py:18):**
```python
TAKER_FEE_ROUND_TRIP = 0.0012
REQUIRED_EDGE_BY_LABEL = {
    "BOUNCE_STRONG": 0.5,
    "BOUNCE_WEAK": 0.3,
}
```

### 📖 Lo que dice Ousterhout (Cap 6):

> *"General-purpose modules are deeper. The module's interface should be general enough to support multiple uses."*

> 🚩 **Red Flag:** Valores hardcodeados que cambian por exchange o por condición de mercado.

### 🔴 Diagnóstico:

1. `TAKER_FEE_ROUND_TRIP` varía por exchange (Binance ≠ Bybit ≠ FTX). Si CGAlpha algún día opera en otro exchange, este valor está mal.
2. `REQUIRED_EDGE_BY_LABEL` son umbrales que pueden necesitar ajuste sin cambiar código.

### ✅ Solución propuesta:

```python
@dataclass
class FeeSchedule:
    taker_fee_round_trip: float = 0.0012  # Binance default
    maker_fee_round_trip: float = 0.0004  # Si usas límite
    
@dataclass  
class EdgeThresholds:
    bounce_strong: float = 0.5
    bounce_weak: float = 0.3

# En la configuración del pipeline:
config = TradingConfig(
    fees=FeeSchedule(),
    edges=EdgeThresholds(),
    ...
)
```

---

## 🔍 Problema 3: Código Duplicado → `_write_bridge_entry` / `_write_rejected_bridge_entry`

**Código actual (shadow_trader.py:315, 371):** Dos métodos que hacen casi lo mismo (escribir JSONL) pero con estructuras ligeramente diferentes.

### 📖 Lo que dice Ousterhout (Cap 9):

> *"Bring together if information is shared. If two pieces of code depend on the same information, they should probably be in the same module."*

> 🚩 **Red Flag:** Dos métodos que difieren solo en el contenido del diccionario que serializan.

### 🔴 Diagnóstico:

Ambos métodos:
1. Crean `Path(BRIDGE_JSONL_PATH).parent.mkdir(parents=True, exist_ok=True)`
2. Abren archivo en modo `"a"`
3. Escriben `json.dumps(entry, default=str) + "\n"`

La única diferencia es qué campos incluye `entry`.

### ✅ Solución propuesta:

```python
def _write_bridge_event(self, event_type: str, **fields) -> None:
    """Single method for all bridge events. Cap 9: Bring together shared logic."""
    entry = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    Path(BRIDGE_JSONL_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(BRIDGE_JSONL_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

# Uso:
self._write_bridge_event("trade_open", trade_id=..., price=..., ...)
self._write_bridge_event("trade_rejected", reason=..., signal=..., ...)
```

**Beneficio:** Un solo método general-purpose en vez de dos especializados. Si necesitas un tercer tipo de evento, no creas un tercer método.

---

## 🔍 Problema 4: Módulo con Muchos Métodos Públicos → ShadowTrader

**Interfaz actual de ShadowTrader (métodos públicos):**
- `open_shadow_trade()`
- `estimate_slippage()`
- `update_shadow_traces()`
- `get_active_trade_count()` ← shallow
- `get_total_pnl()`
- `create_default()`

### 📖 Lo que dice Ousterhout (Cap 5: Information Hiding):

> *"The interface should hide as much of the implementation as possible. Information leakage occurs when a design decision is reflected in multiple modules."*

### 🔴 Diagnóstico:

`get_active_trade_count()` y `get_total_pnl()` exponen `self.order_manager` indirectamente. Si cambias `order_manager` por otra implementación, estos métodos también cambian → **change amplification**.

### ✅ Solución propuesta:

Crear una **interfaz profunda** que oculte `order_manager`:

```python
class ShadowTrader(BaseComponentV3):
    """Deep module: hides order_manager behind simple stats interface."""
    
    # Interfaz pública (la que el resto del sistema ve)
    def open_trade(self, ...) -> TradeResult: ...
    def get_stats(self) -> TradeStats: ...       # ← Reemplaza a los 2 métodos
    def update_market(self, price: float) -> None: ...
    
    # TradeStats es un value object inmutable
    @dataclass(frozen=True)
    class TradeStats:
        active_count: int
        total_pnl_pct: float
        win_rate: float
```

---

## 📊 Resumen: Impacto de Aplicar el Libro

| Problema | Principio de Ousterhout | Gravedad | Solución |
|----------|------------------------|----------|----------|
| `get_active_trade_count()` | Cap 4: Shallow Module | 🟡 Media | Eliminar o hacer privado `order_manager` |
| `TAKER_FEE` hardcodeado | Cap 6: General-Purpose | 🟡 Media | Mover a configuración |
| `_write_bridge_entry` duplicado | Cap 9: Bring Together | 🟡 Media | Unificar en método general |
| Muchos métodos públicos | Cap 5: Information Hiding | 🟢 Baja | Consolidar en `TradeStats` |

---

## 🔗 Referencias Cruzadas

- [[Ch4-Deep-Modules]] — Principio de módulos profundos
- [[Ch6-General-Purpose-Modules]] — Generalidad en interfaces
- [[ShadowTrader-Refactor]] — Plan de refactor propuesto