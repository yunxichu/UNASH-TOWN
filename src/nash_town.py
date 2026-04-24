"""UNASH-TOWN simulation engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import random

from .market import AShareMarket
from .town_agent import TownAgent, create_town_agents
from .trading import Order, OrderBook, OrderType, TradingRules


@dataclass
class TownStats:
    total_orders: int = 0
    total_trades: int = 0
    total_volume: int = 0
    total_turnover: float = 0.0


class NashTown:
    SESSION_MINUTES = list(range(9 * 60 + 30, 11 * 60 + 31)) + list(range(13 * 60, 15 * 60 + 1))

    def __init__(
        self,
        num_agents: int = 10,
        initial_capital: float = 100000.0,
        initial_price: float = 100.0,
        seed: Optional[int] = None,
        verbose: bool = True,
    ) -> None:
        self.random = random.Random(seed)
        self.verbose = verbose
        self.market = AShareMarket(initial_price=initial_price, seed=seed)
        self.order_book = OrderBook()
        self.agents: List[TownAgent] = create_town_agents(num_agents, initial_capital, seed, initial_price)
        self.current_day = 1
        self.current_minute_index = 0
        self.stats = TownStats()
        self.daily_logs: List[Dict] = []
        self.trade_log: List[Dict] = []
        self.last_tick: Dict = {}

    @property
    def current_time_minutes(self) -> int:
        return self.SESSION_MINUTES[self.current_minute_index]

    @property
    def current_hour(self) -> int:
        return self.current_time_minutes // 60

    @property
    def current_minute(self) -> int:
        return self.current_time_minutes % 60

    def get_market_phase(self) -> str:
        minute = self.current_time_minutes
        if minute < 9 * 60 + 30:
            return "opening_call"
        if 9 * 60 + 30 <= minute <= 11 * 60 + 30:
            return "morning_continuous"
        if 11 * 60 + 30 < minute < 13 * 60:
            return "lunch_break"
        if 13 * 60 <= minute < 14 * 60 + 57:
            return "afternoon_continuous"
        if 14 * 60 + 57 <= minute <= 15 * 60:
            return "closing_call"
        return "closed"

    def simulate_tick(self) -> Dict:
        timestamp = self.current_day * 10000 + self.current_time_minutes
        context = self._build_context()
        orders_created = 0

        for agent in self.agents:
            decision = agent.decide(context)
            order = self._decision_to_order(agent, decision, timestamp)
            if order:
                self.order_book.add_order(order)
                orders_created += 1
                self.stats.total_orders += 1

        trades = self.order_book.match(timestamp)
        buy_volume = sum(trade.quantity for trade in trades)
        self._apply_trades(trades)

        imbalance = self.order_book.imbalance()
        net_pressure = imbalance + self._trade_pressure(trades)
        self.market.tick(net_pressure=net_pressure, traded_volume=buy_volume)
        for agent in self.agents:
            pass

        result = {
            "day": self.current_day,
            "time": self.time_label(),
            "phase": self.get_market_phase(),
            "price": self.market.state.price,
            "orders": orders_created,
            "trades": [self._trade_to_dict(trade) for trade in trades],
            "stats": self._stats_dict(),
        }
        self.last_tick = result
        self._advance_clock()
        return result

    def simulate_day(self) -> Dict:
        start_day = self.current_day
        while self.current_day == start_day:
            self.simulate_tick()
        return self.daily_logs[-1]

    def simulate_days(self, num_days: int) -> List[Dict]:
        return [self.simulate_day() for _ in range(num_days)]

    def _build_context(self) -> Dict:
        summary = self.market.get_market_summary()
        technical = self.market.get_technical_analysis()
        return {
            "price": summary["price"],
            "rsi": technical["rsi"],
            "momentum": technical["momentum"],
            "volatility": technical["volatility"],
            "imbalance": self.order_book.imbalance(),
            "regime": summary["regime"],
            "event": summary["event"],
            "phase": self.get_market_phase(),
        }

    def _decision_to_order(self, agent: TownAgent, decision, timestamp: int) -> Optional[Order]:
        if decision.action not in {"buy", "sell"} or not decision.price or decision.quantity <= 0:
            return None
        order_type = OrderType.BUY if decision.action == "buy" else OrderType.SELL
        quantity = TradingRules.round_lot(decision.quantity)
        price = TradingRules.round_price(decision.price)
        valid, _ = TradingRules.validate_order(
            order_type=order_type,
            price=price,
            quantity=quantity,
            reference_price=self.market.state.previous_close,
            capital=agent.capital,
            available_position=agent.available_position,
        )
        if not valid:
            return None
        return Order(0, agent.agent_id, order_type, price, quantity, timestamp)

    def _apply_trades(self, trades) -> None:
        agents = {agent.agent_id: agent for agent in self.agents}
        for trade in trades:
            buyer = agents.get(trade.buyer_id)
            seller = agents.get(trade.seller_id)
            if not buyer or not seller:
                continue
            buyer.apply_buy(trade.quantity, trade.price, trade.buyer_fee)
            seller.apply_sell(trade.quantity, trade.price, trade.seller_fee, trade.stamp_duty)
            self.stats.total_trades += 1
            self.stats.total_volume += trade.quantity
            self.stats.total_turnover += trade.price * trade.quantity
            self.trade_log.append(self._trade_to_dict(trade))

    def _trade_pressure(self, trades) -> float:
        if not trades:
            return 0.0
        buy_value = sum(trade.price * trade.quantity for trade in trades)
        scale = max(1.0, self.market.state.turnover + buy_value)
        return min(0.35, buy_value / scale * 0.08)

    def _advance_clock(self) -> None:
        self.current_minute_index += 1
        if self.current_minute_index >= len(self.SESSION_MINUTES):
            self._end_day()

    def _end_day(self) -> None:
        summary = self.market.get_market_summary()
        snapshot = {
            "day": self.current_day,
            "market": summary,
            "stats": self._stats_dict(),
            "agents": [agent.get_status(summary["price"]) for agent in self.agents],
        }
        self.daily_logs.append(snapshot)
        if self.verbose:
            self._print_day_summary(snapshot)
        for agent in self.agents:
            agent.end_day()
        self.order_book.clear()
        self.market.new_day()
        self.current_day += 1
        self.current_minute_index = 0
        self.stats = TownStats()

    def _print_day_summary(self, snapshot: Dict) -> None:
        market = snapshot["market"]
        leaders = sorted(snapshot["agents"], key=lambda item: item["total_value"], reverse=True)[:3]
        print(f"Day {snapshot['day']} close {market['price']:.2f} ({market['change_pct']:+.2f}%), trades={snapshot['stats']['total_trades']}")
        for rank, agent in enumerate(leaders, 1):
            print(f"  {rank}. {agent['name']} {agent['label']} value={agent['total_value']:.0f} return={agent['return_rate']:+.2f}%")

    def _stats_dict(self) -> Dict:
        return {
            "total_orders": self.stats.total_orders,
            "total_trades": self.stats.total_trades,
            "total_volume": self.stats.total_volume,
            "total_turnover": round(self.stats.total_turnover, 2),
        }

    def _trade_to_dict(self, trade) -> Dict:
        return {
            "trade_id": trade.trade_id,
            "buyer": trade.buyer_id,
            "seller": trade.seller_id,
            "price": trade.price,
            "quantity": trade.quantity,
            "timestamp": trade.timestamp,
        }

    def time_label(self) -> str:
        return f"{self.current_hour:02d}:{self.current_minute:02d}"

    def get_market_overview(self) -> Dict:
        return {
            "day": self.current_day,
            "time": self.time_label(),
            "phase": self.get_market_phase(),
            "market": self.market.get_market_summary(),
            "stats": self._stats_dict(),
            "order_book": self.order_book.depth(),
        }

    def get_town_overview(self) -> Dict:
        price = self.market.state.price
        return {
            **self.get_market_overview(),
            "agents": [agent.get_status(price) for agent in self.agents],
            "recent_trades": self.trade_log[-20:],
        }
