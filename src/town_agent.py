"""Heterogeneous trader agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from .personality import AgentArchetype, Personality
from .trading import OrderType, TradingRules


@dataclass
class TradingDecision:
    action: str = "hold"
    price: Optional[float] = None
    quantity: int = 0
    reason: str = ""

    @classmethod
    def hold(cls, reason: str = "") -> "TradingDecision":
        return cls(action="hold", reason=reason)


@dataclass
class TownAgent:
    agent_id: str
    name: str
    initial_capital: float
    archetype: AgentArchetype
    seed: Optional[int] = None
    capital: float = field(init=False)
    position: int = 0
    today_bought: int = 0
    avg_cost: float = 0.0
    realized_pnl: float = 0.0
    total_fees: float = 0.0
    initial_equity: float = field(init=False)
    trade_count: int = 0
    wins: int = 0
    losses: int = 0
    personality: Personality = field(init=False)
    memory: List[Dict] = field(default_factory=list)
    strategy_weights: Dict[str, float] = field(init=False)

    def __post_init__(self) -> None:
        self.random = random.Random(self.seed)
        self.personality = Personality(self.archetype)
        self.capital = self.initial_capital * self.personality.cash_scale
        self.initial_equity = self.capital
        self.strategy_weights = self._initial_strategy_weights()

    @property
    def available_position(self) -> int:
        return max(0, self.position - self.today_bought)

    def total_value(self, price: float) -> float:
        return self.capital + self.position * price

    def return_rate(self, price: float) -> float:
        base = self.initial_equity
        return (self.total_value(price) - base) / base if base else 0.0

    def decide(self, context: Dict) -> TradingDecision:
        price = float(context["price"])
        rsi = float(context["rsi"])
        momentum = float(context["momentum"])
        volatility = float(context["volatility"])
        imbalance = float(context["imbalance"])
        regime = str(context["regime"])

        signal = self._score_market(rsi, momentum, volatility, imbalance, regime)
        risk_budget = self.capital * self.personality.position_size * (0.45 + self.personality.risk)
        quantity = TradingRules.round_lot(int(risk_budget / max(price, 0.01)))

        if self.position > 0:
            pnl_pct = (price - self.avg_cost) / self.avg_cost if self.avg_cost else 0.0
            stop_loss = 0.03 + (1 - self.personality.risk) * 0.05
            take_profit = 0.04 + self.personality.risk * 0.10
            if pnl_pct <= -stop_loss:
                return TradingDecision("sell", TradingRules.round_price(price * 0.998), self.available_position, "risk stop")
            if pnl_pct >= take_profit and self.random.random() > self.personality.patience:
                return TradingDecision("sell", TradingRules.round_price(price * 1.001), self.available_position, "take profit")

        threshold = 0.30 + (1 - self.personality.risk) * 0.18
        if signal > threshold and quantity >= TradingRules.MIN_LOT:
            limit = price * (1 + 0.002 * self.personality.risk)
            return TradingDecision("buy", TradingRules.round_price(limit), quantity, "positive composite signal")

        if signal < -threshold and self.available_position >= TradingRules.MIN_LOT:
            sell_qty = TradingRules.round_lot(max(TradingRules.MIN_LOT, int(self.available_position * (0.4 + self.personality.risk * 0.4))))
            return TradingDecision("sell", TradingRules.round_price(price * 0.998), min(sell_qty, self.available_position), "negative composite signal")

        if self.archetype is AgentArchetype.NOISE and self.random.random() < 0.06:
            if self.position > 0 and self.random.random() < 0.5:
                return TradingDecision("sell", TradingRules.round_price(price), self.available_position, "noise liquidity")
            if quantity >= TradingRules.MIN_LOT:
                return TradingDecision("buy", TradingRules.round_price(price), quantity, "noise liquidity")

        return TradingDecision.hold("no edge")

    def _initial_strategy_weights(self) -> Dict[str, float]:
        weights = {"value": 0.0, "momentum": 0.0, "mean_reversion": 0.0, "liquidity": 0.0}
        if self.archetype in {AgentArchetype.VALUE, AgentArchetype.CONTRARIAN, AgentArchetype.HEDGING}:
            weights["value"] += 0.45
            weights["mean_reversion"] += 0.35
        if self.archetype in {AgentArchetype.MOMENTUM, AgentArchetype.GROWTH, AgentArchetype.VOLATILITY}:
            weights["momentum"] += 0.55
            weights["liquidity"] += 0.15
        if self.archetype in {AgentArchetype.ARBITRAGE, AgentArchetype.QUANTITATIVE}:
            weights["mean_reversion"] += 0.45
            weights["liquidity"] += 0.25
        if self.archetype is AgentArchetype.NOISE:
            weights["liquidity"] += 0.65
        if self.archetype is AgentArchetype.LEARNING:
            weights = {key: 0.25 for key in weights}
        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}

    def _score_market(self, rsi: float, momentum: float, volatility: float, imbalance: float, regime: str) -> float:
        value_score = (50 - rsi) / 50
        momentum_score = max(-1.0, min(1.0, momentum * 80))
        mean_reversion_score = 0.0
        if rsi < 35:
            mean_reversion_score = 0.65
        elif rsi > 68:
            mean_reversion_score = -0.65
        liquidity_score = imbalance * 0.4 - volatility * 4
        regime_bias = {"bull": 0.18, "bear": -0.18, "volatile": -0.05, "sideways": 0.0}.get(regime, 0.0)

        score = (
            self.strategy_weights["value"] * value_score
            + self.strategy_weights["momentum"] * momentum_score
            + self.strategy_weights["mean_reversion"] * mean_reversion_score
            + self.strategy_weights["liquidity"] * liquidity_score
            + regime_bias
        )
        return max(-1.0, min(1.0, score))

    def apply_buy(self, quantity: int, price: float, fee: float) -> None:
        value = quantity * price
        previous_cost = self.avg_cost * self.position
        self.capital -= value + fee
        self.position += quantity
        self.today_bought += quantity
        self.avg_cost = (previous_cost + value) / self.position if self.position else 0.0
        self.total_fees += fee
        self.trade_count += 1

    def apply_sell(self, quantity: int, price: float, fee: float, stamp_duty: float) -> None:
        quantity = min(quantity, self.position)
        pnl = (price - self.avg_cost) * quantity - fee - stamp_duty
        self.capital += quantity * price - fee - stamp_duty
        self.position -= quantity
        self.realized_pnl += pnl
        self.total_fees += fee + stamp_duty
        self.trade_count += 1
        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
        if self.position == 0:
            self.avg_cost = 0.0
        self.personality.adapt(pnl)
        self.memory.append({"type": "sell", "pnl": round(pnl, 2), "price": price, "quantity": quantity})
        if len(self.memory) > 50:
            self.memory.pop(0)

    def end_day(self) -> None:
        self.today_bought = 0

    def get_status(self, price: float = 0.0) -> Dict:
        value = self.total_value(price)
        return_rate = self.return_rate(price)
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "archetype": self.archetype.value,
            "label": self.personality.label,
            "capital": round(self.capital, 2),
            "position": self.position,
            "available_position": self.available_position,
            "avg_cost": round(self.avg_cost, 2),
            "total_value": round(value, 2),
            "return_rate": round(return_rate * 100, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees": round(self.total_fees, 2),
            "trade_count": self.trade_count,
            "win_rate": round(self.wins / max(1, self.wins + self.losses) * 100, 2),
            "risk": round(self.personality.risk, 2),
            "position_size": round(self.personality.position_size, 2),
            "dominant_style": max(self.strategy_weights, key=self.strategy_weights.get),
        }


def create_town_agents(
    num_agents: int,
    initial_capital: float,
    seed: Optional[int] = None,
    initial_price: float = 100.0,
) -> List[TownAgent]:
    rng = random.Random(seed)
    archetypes = list(AgentArchetype)
    names = ["Aster", "Beryl", "Cedar", "Dune", "Echo", "Flux", "Gale", "Halo", "Iris", "Jade"]
    agents: List[TownAgent] = []
    for index in range(num_agents):
        archetype = archetypes[index % len(archetypes)]
        agent = TownAgent(
            agent_id=f"agent_{index:03d}",
            name=f"{names[index % len(names)]}-{index + 1}",
            initial_capital=initial_capital,
            archetype=archetype,
            seed=rng.randint(0, 10_000_000),
        )
        if index % 3 == 0:
            quantity = TradingRules.round_lot(int((agent.capital * 0.28) / initial_price))
            agent.position = quantity
            agent.avg_cost = initial_price
            agent.capital -= quantity * initial_price
            agent.initial_equity = agent.capital + quantity * initial_price
        agents.append(agent)
    return agents
