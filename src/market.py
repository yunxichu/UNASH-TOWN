"""A compact A-share market environment."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import math
import random


class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


class MarketEvent(Enum):
    NONE = "none"
    EARNINGS = "earnings"
    POLICY = "policy"
    LIQUIDITY = "liquidity"
    SENTIMENT = "sentiment"


class LiquidityTier(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Security:
    code: str
    name: str
    initial_price: float
    liquidity: LiquidityTier
    sector: str


@dataclass
class MarketState:
    price: float
    previous_close: float
    day_open: float
    day_high: float
    day_low: float
    volume: int = 0
    turnover: float = 0.0
    regime: MarketRegime = MarketRegime.SIDEWAYS
    event: MarketEvent = MarketEvent.NONE
    volatility: float = 0.012
    momentum: float = 0.0
    rsi: float = 50.0


class AShareMarket:
    DEFAULT_SECURITIES = [
        Security("000001", "Ping An Bank", 15.00, LiquidityTier.HIGH, "bank"),
        Security("600519", "Kweichow Moutai", 1800.00, LiquidityTier.HIGH, "consumer"),
        Security("300750", "CATL", 200.00, LiquidityTier.MEDIUM, "new_energy"),
        Security("688981", "SMIC", 45.00, LiquidityTier.LOW, "semiconductor"),
    ]

    def __init__(
        self,
        initial_price: float = 100.0,
        seed: Optional[int] = None,
        security: Optional[Security] = None,
    ) -> None:
        self.random = random.Random(seed)
        self.security = security or Security("SIM001", "UNASH Synthetic A", initial_price, LiquidityTier.MEDIUM, "synthetic")
        self.state = MarketState(
            price=self.security.initial_price,
            previous_close=self.security.initial_price,
            day_open=self.security.initial_price,
            day_high=self.security.initial_price,
            day_low=self.security.initial_price,
        )
        self.day = 1
        self.price_history: List[float] = [self.security.initial_price]
        self.volume_history: List[int] = []

    @property
    def limit_up(self) -> float:
        return round(self.state.previous_close * 1.10, 2)

    @property
    def limit_down(self) -> float:
        return round(self.state.previous_close * 0.90, 2)

    def tick(self, net_pressure: float, traded_volume: int = 0) -> MarketState:
        tier_vol = {
            LiquidityTier.HIGH: 0.007,
            LiquidityTier.MEDIUM: 0.012,
            LiquidityTier.LOW: 0.020,
        }[self.security.liquidity]
        regime_drift = {
            MarketRegime.BULL: 0.0008,
            MarketRegime.BEAR: -0.0008,
            MarketRegime.SIDEWAYS: 0.0,
            MarketRegime.VOLATILE: 0.0,
        }[self.state.regime]
        event_drift = {
            MarketEvent.NONE: 0.0,
            MarketEvent.EARNINGS: 0.0015,
            MarketEvent.POLICY: self.random.uniform(-0.002, 0.002),
            MarketEvent.LIQUIDITY: -0.001,
            MarketEvent.SENTIMENT: self.random.uniform(-0.003, 0.003),
        }[self.state.event]

        shock = self.random.gauss(0, tier_vol)
        pressure = max(-1.0, min(1.0, net_pressure)) * tier_vol * 1.8
        change = regime_drift + event_drift + pressure + shock
        if self.state.regime is MarketRegime.VOLATILE:
            change *= 1.8

        new_price = self.state.price * (1 + change)
        new_price = max(self.limit_down, min(self.limit_up, new_price))

        prev = self.state.price
        self.state.price = round(new_price, 2)
        self.state.day_high = max(self.state.day_high, self.state.price)
        self.state.day_low = min(self.state.day_low, self.state.price)
        self.state.volume += traded_volume
        self.state.turnover += traded_volume * self.state.price
        self.state.momentum = (self.state.price - prev) / prev if prev else 0.0
        self.price_history.append(self.state.price)
        self.volume_history.append(traded_volume)
        self._update_indicators()
        return self.state

    def new_day(self) -> None:
        self.day += 1
        self.state.previous_close = self.state.price
        self.state.day_open = self.state.price
        self.state.day_high = self.state.price
        self.state.day_low = self.state.price
        self.state.volume = 0
        self.state.turnover = 0.0
        self.state.event = self._sample_event()
        self._maybe_switch_regime()

    def _sample_event(self) -> MarketEvent:
        return self.random.choices(
            list(MarketEvent),
            weights=[0.78, 0.06, 0.06, 0.04, 0.06],
        )[0]

    def _maybe_switch_regime(self) -> None:
        if self.random.random() < 0.22:
            self.state.regime = self.random.choices(
                list(MarketRegime),
                weights=[0.25, 0.22, 0.35, 0.18],
            )[0]

    def _update_indicators(self) -> None:
        if len(self.price_history) < 3:
            return
        returns = [
            (self.price_history[i] - self.price_history[i - 1]) / self.price_history[i - 1]
            for i in range(max(1, len(self.price_history) - 20), len(self.price_history))
            if self.price_history[i - 1] > 0
        ]
        if returns:
            mean = sum(returns) / len(returns)
            variance = sum((value - mean) ** 2 for value in returns) / len(returns)
            self.state.volatility = math.sqrt(variance)

        changes = [self.price_history[i] - self.price_history[i - 1] for i in range(max(1, len(self.price_history) - 14), len(self.price_history))]
        gains = sum(change for change in changes if change > 0)
        losses = -sum(change for change in changes if change < 0)
        if losses == 0:
            self.state.rsi = 100.0 if gains > 0 else 50.0
        else:
            rs = gains / losses
            self.state.rsi = 100 - 100 / (1 + rs)

    def get_market_summary(self) -> Dict:
        change = self.state.price - self.state.previous_close
        change_pct = change / self.state.previous_close * 100 if self.state.previous_close else 0.0
        return {
            "code": self.security.code,
            "name": self.security.name,
            "price": self.state.price,
            "previous_close": self.state.previous_close,
            "day_open": self.state.day_open,
            "day_high": self.state.day_high,
            "day_low": self.state.day_low,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": self.state.volume,
            "turnover": round(self.state.turnover, 2),
            "regime": self.state.regime.value,
            "event": self.state.event.value,
            "volatility": round(self.state.volatility, 4),
            "momentum": round(self.state.momentum, 4),
            "rsi": round(self.state.rsi, 2),
            "limit_up": self.limit_up,
            "limit_down": self.limit_down,
        }

    def get_technical_analysis(self) -> Dict:
        return {
            "rsi": self.state.rsi,
            "momentum": self.state.momentum,
            "volatility": self.state.volatility,
            "trend_strength": self._trend_strength(),
            "macd": self._moving_average(8) - self._moving_average(21),
            "signal_line": self._moving_average(9),
        }

    def _moving_average(self, period: int) -> float:
        values = self.price_history[-period:]
        return sum(values) / len(values)

    def _trend_strength(self) -> float:
        if len(self.price_history) < 10:
            return 0.0
        base = self.price_history[-10]
        return (self.state.price - base) / base if base else 0.0
