"""`StrategyConfig`: esquema de estrategia (versión 1, MVP spot long).

Un parámetro numérico puede ser un escalar, `{"values": [...]}` o
`{"range": [desde, hasta, paso]}`. `variants.expand` lo resuelve a escalares.
Un config "concreto" (una variante) tiene todos los parámetros como escalares.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wick.data.timeframes import Timeframe

SCHEMA_VERSION = 1


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValuesSpec(_Strict):
    values: list[float] = Field(min_length=1)


class RangeSpec(_Strict):
    range: list[float] = Field(min_length=3, max_length=3)  # [desde, hasta, paso]

    @field_validator("range")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        a, b, step = v
        if step <= 0:
            raise ValueError("El paso del rango tiene que ser mayor que 0.")
        if a > b:
            raise ValueError("En un rango, 'desde' tiene que ser menor o igual que 'hasta'.")
        return v


Param = float | ValuesSpec | RangeSpec

IndicatorType = Literal["sma", "ema", "rsi", "macd", "bbands", "atr"]
PriceSource = Literal["open", "high", "low", "close"]

# Parámetros por indicador: nombre → (valor por defecto, mínimo).
INDICATOR_PARAMS: dict[str, dict[str, tuple[float, float]]] = {
    "sma": {"length": (20, 1)},
    "ema": {"length": (20, 1)},
    "rsi": {"length": (14, 1)},
    "macd": {"fast": (12, 1), "slow": (26, 1), "signal": (9, 1)},
    "bbands": {"length": (20, 1), "mult": (2.0, 0.0)},
    "atr": {"length": (14, 1)},
}

# Series de salida de cada indicador. "" = la serie principal (se referencia por el id).
INDICATOR_OUTPUTS: dict[str, tuple[str, ...]] = {
    "sma": ("",),
    "ema": ("",),
    "rsi": ("",),
    "macd": ("macd", "signal", "hist"),
    "bbands": ("upper", "middle", "lower"),
    "atr": ("",),
}

PRICE_OPERANDS = ("open", "high", "low", "close")


class IndicatorSpec(_Strict):
    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")]
    type: IndicatorType
    params: dict[str, Param] = Field(default_factory=dict)
    source: PriceSource = "close"

    @model_validator(mode="after")
    def _check_params(self) -> IndicatorSpec:
        allowed = INDICATOR_PARAMS[self.type]
        unknown = set(self.params) - set(allowed)
        if unknown:
            raise ValueError(f"Parámetros desconocidos para {self.type}: {sorted(unknown)}")
        for name, (default, _min) in allowed.items():
            self.params.setdefault(name, float(default))
        return self


class NumberOperand(_Strict):
    value: Param


Operator = Literal["crosses_above", "crosses_below", ">", "<"]


class Condition(_Strict):
    left: str
    op: Operator
    right: str | NumberOperand


class Rule(_Strict):
    """Condiciones combinadas con AND."""

    conditions: list[Condition] = Field(min_length=1)


class Entry(_Strict):
    long: Rule
    # En spot no abre shorts: solo se usa como "señal opuesta" para cerrar el long.
    short: Rule | None = None


class StopSpec(_Strict):
    type: Literal["none", "pct", "atr"] = "none"
    pct: Param = 2.0  # % de distancia desde el precio de entrada
    atr_length: Param = 14
    mult: Param = 2.0


class TakeProfitSpec(_Strict):
    type: Literal["none", "pct", "rr"] = "none"
    pct: Param = 4.0
    ratio: Param = 2.0  # relación riesgo/beneficio sobre la distancia al stop


class ExitSpec(_Strict):
    stop: StopSpec = Field(default_factory=StopSpec)
    take_profit: TakeProfitSpec = Field(default_factory=TakeProfitSpec)
    on_opposite_signal: bool = False


class SizingSpec(_Strict):
    mode: Literal["pct_capital"] = "pct_capital"
    value: Param = 100.0  # % de la equity (o del capital inicial sin compuesto)
    compound: bool = True


class CostsSpec(_Strict):
    taker: float = Field(default=0.001, ge=0, le=0.05)
    slippage: float = Field(default=0.0005, ge=0, le=0.05)


class DateRange(_Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: date = Field(alias="from")
    to: date

    @model_validator(mode="after")
    def _order(self) -> DateRange:
        if self.to < self.from_:
            raise ValueError("La fecha 'hasta' es anterior a 'desde'.")
        return self


class StrategyConfig(_Strict):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=120)
    market: Literal["spot"] = "spot"
    symbol: str = Field(pattern=r"^[A-Z0-9]{2,30}$")
    timeframe: Timeframe
    range: DateRange
    capital: float = Field(gt=0)
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    entry: Entry
    exit: ExitSpec = Field(default_factory=ExitSpec)
    sizing: SizingSpec = Field(default_factory=SizingSpec)
    costs: CostsSpec = Field(default_factory=CostsSpec)

    @model_validator(mode="after")
    def _check_refs(self) -> StrategyConfig:
        ids = [i.id for i in self.indicators]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay indicadores con el mismo id.")
        valid = set(PRICE_OPERANDS)
        for ind in self.indicators:
            for out in INDICATOR_OUTPUTS[ind.type]:
                valid.add(ind.id if out == "" else f"{ind.id}.{out}")
        rules = [self.entry.long] + ([self.entry.short] if self.entry.short else [])
        for rule in rules:
            for c in rule.conditions:
                for operand in (c.left, c.right):
                    if isinstance(operand, str) and operand not in valid:
                        raise ValueError(
                            f"La condición usa '{operand}', que no existe. Opciones: {sorted(valid)}"
                        )
        if self.exit.take_profit.type == "rr" and self.exit.stop.type == "none":
            raise ValueError("El take profit por relación riesgo/beneficio necesita un stop.")
        if self.exit.on_opposite_signal and self.entry.short is None:
            raise ValueError("La salida por señal opuesta necesita condiciones de señal opuesta.")
        return self
