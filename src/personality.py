"""Trader archetypes for UNASH-TOWN.

The project uses a town metaphor, but the agents are market participants.
Each archetype supplies a starting bias; behaviour can still drift through
feedback from the simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict
import random


class AgentArchetype(Enum):
    VALUE = "value"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    VOLATILITY = "volatility"
    HEDGING = "hedging"
    NOISE = "noise"
    GROWTH = "growth"
    CONTRARIAN = "contrarian"
    QUANTITATIVE = "quantitative"
    LEARNING = "learning"


ARCHETYPE_PROFILES: Dict[AgentArchetype, Dict[str, float | int | str]] = {
    AgentArchetype.VALUE: {
        "label": "Value",
        "risk": 0.30,
        "learning": 0.45,
        "position_size": 0.16,
        "cash_scale": 1.20,
        "description": "Looks for discounted prices and tolerates slow feedback.",
    },
    AgentArchetype.MOMENTUM: {
        "label": "Momentum",
        "risk": 0.72,
        "learning": 0.55,
        "position_size": 0.18,
        "cash_scale": 0.90,
        "description": "Follows recent strength and cuts weak positions early.",
    },
    AgentArchetype.ARBITRAGE: {
        "label": "Arbitrage",
        "risk": 0.22,
        "learning": 0.70,
        "position_size": 0.12,
        "cash_scale": 1.30,
        "description": "Prefers small mispricing and lower variance outcomes.",
    },
    AgentArchetype.VOLATILITY: {
        "label": "Volatility",
        "risk": 0.82,
        "learning": 0.50,
        "position_size": 0.14,
        "cash_scale": 0.65,
        "description": "Trades price swings with shorter holding periods.",
    },
    AgentArchetype.HEDGING: {
        "label": "Hedging",
        "risk": 0.25,
        "learning": 0.60,
        "position_size": 0.10,
        "cash_scale": 1.15,
        "description": "Limits drawdown and keeps exposure modest.",
    },
    AgentArchetype.NOISE: {
        "label": "Noise",
        "risk": 0.58,
        "learning": 0.25,
        "position_size": 0.08,
        "cash_scale": 0.55,
        "description": "Adds liquidity and randomness to the market.",
    },
    AgentArchetype.GROWTH: {
        "label": "Growth",
        "risk": 0.66,
        "learning": 0.60,
        "position_size": 0.17,
        "cash_scale": 0.90,
        "description": "Pays up for strong trend and high upside regimes.",
    },
    AgentArchetype.CONTRARIAN: {
        "label": "Contrarian",
        "risk": 0.50,
        "learning": 0.62,
        "position_size": 0.15,
        "cash_scale": 0.95,
        "description": "Buys fear and sells crowd enthusiasm.",
    },
    AgentArchetype.QUANTITATIVE: {
        "label": "Quantitative",
        "risk": 0.36,
        "learning": 0.80,
        "position_size": 0.13,
        "cash_scale": 1.05,
        "description": "Uses strict signals and avoids emotional overtrading.",
    },
    AgentArchetype.LEARNING: {
        "label": "Learning",
        "risk": 0.52,
        "learning": 0.92,
        "position_size": 0.14,
        "cash_scale": 0.90,
        "description": "Adapts quickly when feedback changes.",
    },
}


@dataclass
class Personality:
    archetype: AgentArchetype = AgentArchetype.LEARNING
    risk: float = 0.5
    learning: float = 0.5
    position_size: float = 0.12
    cash_scale: float = 1.0
    patience: float = 0.5
    discipline: float = 0.5

    def __post_init__(self) -> None:
        profile = ARCHETYPE_PROFILES[self.archetype]
        self.risk = self._jitter(float(profile["risk"]), 0.08)
        self.learning = self._jitter(float(profile["learning"]), 0.06)
        self.position_size = self._jitter(float(profile["position_size"]), 0.03, 0.03, 0.35)
        self.cash_scale = self._jitter(float(profile["cash_scale"]), 0.08, 0.3, 2.0)
        self.patience = self._jitter(1.0 - self.risk * 0.55, 0.08)
        self.discipline = self._jitter(0.45 + self.learning * 0.35, 0.08)

    @staticmethod
    def _jitter(value: float, amount: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value + random.uniform(-amount, amount)))

    @property
    def label(self) -> str:
        return str(ARCHETYPE_PROFILES[self.archetype]["label"])

    @property
    def description(self) -> str:
        return str(ARCHETYPE_PROFILES[self.archetype]["description"])

    def adapt(self, reward: float) -> None:
        direction = 1 if reward > 0 else -1
        step = 0.015 * self.learning * direction
        self.risk = max(0.05, min(0.95, self.risk + step))
        self.position_size = max(0.03, min(0.35, self.position_size + step * 0.5))
