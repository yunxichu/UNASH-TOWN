"""
永不纳什小镇 - 智能体系统
整合策略探索、学习反馈、风格演化
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import random
import time

from .agent_interface import (
    BaseAgent, AgentInfo, AgentStatus, AgentType,
    TradingContext, TradingDecision
)
from .strategy_explorer import (
    StrategyExplorer, StrategyType, ActionType, MarketView
)
from .energy_system import EnergySystem
from .life_system import EmotionalState, SocialProfile, ActivityType, MoodType
from .personality import Personality, AgentArchetype, ARCHETYPE_PROFILES


class TownAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        initial_capital: float = 10000.0,
        archetype: AgentArchetype = None,
        bedtime: int = 22,
        wake_time: int = 6
    ):
        super().__init__(agent_id, name, initial_capital)
        
        self.archetype = archetype or random.choice(list(AgentArchetype))
        self.personality = Personality(archetype=self.archetype)
        
        initial_tendency = self._get_initial_tendency()
        exploration_rate = 0.3 - self.personality.memory * 0.2
        learning_rate = 0.1 + self.personality.learning * 0.1
        
        self.strategy_explorer = StrategyExplorer(
            initial_tendency=initial_tendency,
            exploration_rate=exploration_rate,
            learning_rate=learning_rate
        )
        
        self.energy = EnergySystem()
        self.emotional = EmotionalState()
        self.social = SocialProfile()
        
        self.bedtime = bedtime
        self.wake_time = wake_time
        self._is_sleeping = False
        self._current_activity = ActivityType.RESTING
        self._current_location = "家"
        
        self.trade_log: List[Dict] = []
        self.daily_pnl: List[float] = []
        self.hours_slept_last_night: float = 8.0
        
        self._last_trade_price: Optional[float] = None
        self._pending_evaluation: Optional[Dict] = None
    
    def _get_initial_tendency(self) -> Dict[str, float]:
        tendency = {}
        
        if self.archetype == AgentArchetype.CONSERVATIVE:
            tendency["value"] = 0.7
            tendency["mean_reversion"] = 0.6
        elif self.archetype == AgentArchetype.GAMBLER:
            tendency["momentum"] = 0.8
            tendency["breakout"] = 0.7
        elif self.archetype == AgentArchetype.TRADER:
            tendency["swing"] = 0.6
            tendency["scalping"] = 0.5
        elif self.archetype == AgentArchetype.LEARNER:
            pass
        elif self.archetype == AgentArchetype.REVENGEFUL:
            tendency["contrarian"] = 0.6
        elif self.archetype == AgentArchetype.OPPORTUNIST:
            tendency["trend_following"] = 0.7
            tendency["momentum"] = 0.6
        
        return tendency
    
    def should_sleep(self, current_hour: int) -> bool:
        if self.bedtime > self.wake_time:
            return current_hour >= self.bedtime or current_hour < self.wake_time
        else:
            return self.bedtime <= current_hour < self.wake_time
    
    def start_sleeping(self):
        self._is_sleeping = True
        self._current_activity = ActivityType.SLEEPING
        self._current_location = "家"
    
    def wake_up(self):
        self._is_sleeping = False
        self._current_activity = ActivityType.RESTING
        
        sleep_hours = self._calculate_sleep_hours()
        self.hours_slept_last_night = sleep_hours
        
        result = self.energy.sleep(sleep_hours)
        
        if sleep_hours >= 8:
            self.emotional.mood = MoodType.REFRESHED
        elif sleep_hours >= 6:
            self.emotional.mood = MoodType.NEUTRAL
        else:
            self.emotional.mood = MoodType.TIRED
            self.emotional.stress = min(100, self.emotional.stress + 10)
    
    def _calculate_sleep_hours(self) -> float:
        if self.bedtime > self.wake_time:
            return 24 - self.bedtime + self.wake_time
        else:
            return self.wake_time - self.bedtime
    
    def is_sleeping(self) -> bool:
        return self._is_sleeping
    
    def can_trade(self) -> bool:
        return (
            not self._is_sleeping and 
            self.energy.can_trade() and
            self.emotional.stress < 80
        )
    
    def update_hour(self, current_hour: int):
        if self.should_sleep(current_hour) and not self._is_sleeping:
            self.start_sleeping()
        elif not self.should_sleep(current_hour) and self._is_sleeping:
            self.wake_up()
            self.energy.new_day_reset()
    
    def decide(self, context: TradingContext) -> TradingDecision:
        if self._is_sleeping:
            return TradingDecision.no_action()
        
        if not self.can_trade():
            return TradingDecision.no_action()
        
        if self._pending_evaluation:
            self._evaluate_pending_trade(context)
        
        market_data = self._build_market_data(context)
        market_view = self.strategy_explorer.analyze_market(market_data)
        
        strategy = self.strategy_explorer.select_strategy(market_view)
        
        agent_state = {
            "capital": self.capital,
            "position": self.position,
            "avg_cost": self.avg_cost,
        }
        
        action, price, quantity = self.strategy_explorer.decide_action(
            strategy, market_view, market_data, agent_state
        )
        
        if action == ActionType.BUY and price and quantity:
            self._pending_evaluation = {
                "strategy": strategy,
                "action": action,
                "entry_price": price,
                "quantity": quantity,
                "timestamp": context.timestamp,
            }
            return TradingDecision.buy(
                price=price,
                quantity=quantity,
                reasoning=f"[{strategy.value}] 买入"
            )
        
        elif action == ActionType.SELL and price and quantity:
            profit = 0.0
            if self.avg_cost > 0:
                profit = (price - self.avg_cost) * quantity
            
            self.strategy_explorer.record_trade_result(
                strategy=strategy,
                action=action,
                profit=profit,
                success=profit > 0
            )
            
            self._record_trade({
                "strategy": strategy.value,
                "action": "sell",
                "price": price,
                "quantity": quantity,
                "profit": profit,
            })
            
            return TradingDecision.sell(
                price=price,
                quantity=quantity,
                reasoning=f"[{strategy.value}] 卖出, 盈亏: {profit:.2f}"
            )
        
        elif action == ActionType.ADD and price and quantity:
            return TradingDecision.buy(
                price=price,
                quantity=quantity,
                reasoning=f"[{strategy.value}] 加仓"
            )
        
        elif action == ActionType.REDUCE and price and quantity:
            return TradingDecision.sell(
                price=price,
                quantity=quantity,
                reasoning=f"[{strategy.value}] 减仓"
            )
        
        return TradingDecision.no_action()
    
    def _build_market_data(self, context: TradingContext) -> Dict:
        market = context.market_data
        technical = context.technical
        
        return {
            "price": market.price,
            "volume": market.volume,
            "rsi": technical.rsi,
            "macd": technical.macd,
            "signal_line": technical.signal_line,
            "ma_short": market.price * (1 - technical.momentum * 0.01),
            "ma_long": market.price * (1 + technical.trend_strength * 0.01),
            "volatility": abs(technical.momentum) if technical.momentum else 0.02,
            "support": market.low,
            "resistance": market.high,
            "price_history": [market.price],
        }
    
    def _evaluate_pending_trade(self, context: TradingContext):
        if not self._pending_evaluation:
            return
        
        current_price = context.market_data.price
        entry_price = self._pending_evaluation["entry_price"]
        strategy = self._pending_evaluation["strategy"]
        
        if self.position > 0:
            unrealized_pnl = (current_price - self.avg_cost) * self.position
            if abs(unrealized_pnl) > self.capital * 0.05:
                self.strategy_explorer.record_trade_result(
                    strategy=strategy,
                    action=ActionType.BUY,
                    profit=unrealized_pnl,
                    success=unrealized_pnl > 0
                )
                self._pending_evaluation = None
    
    def _record_trade(self, trade_info: Dict):
        self.trade_log.append({
            **trade_info,
            "capital": self.capital,
            "position": self.position,
            "timestamp": time.time(),
        })
        
        profit = trade_info.get("profit", 0)
        self.daily_pnl.append(profit)
        if len(self.daily_pnl) > 100:
            self.daily_pnl.pop(0)
        
        if profit > 0:
            self.emotional.trading_effect(True, profit / 100)
        else:
            self.emotional.trading_effect(False, abs(profit) / 100)
    
    def on_trade_executed(self, trade_info: Dict):
        super().on_trade_executed(trade_info)
    
    def get_status(self) -> Dict:
        energy_status = self.energy.get_status()
        strategy_status = self.strategy_explorer.get_status()
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "archetype": self.archetype.value,
            "dominant_style": strategy_status["dominant_style"],
            "current_strategy": strategy_status["current_strategy"],
            "is_sleeping": self._is_sleeping,
            "activity": self._current_activity.value,
            "energy": energy_status["current_energy"],
            "trading_skill": energy_status["trading_skill"],
            "mood": self.emotional.mood.value,
            "stress": round(self.emotional.stress, 1),
            "capital": round(self.capital, 2),
            "position": self.position,
            "total_value": round(self.total_value, 2),
            "return_rate": f"{(self.total_value / 10000 - 1) * 100:.1f}%",
            "total_trades": len(self.trade_log),
            "win_rate": self._calculate_win_rate(),
            "style_params": strategy_status["style"],
        }
    
    def _calculate_win_rate(self) -> str:
        if not self.trade_log:
            return "N/A"
        profits = [t.get("profit", 0) for t in self.trade_log if "profit" in t]
        if not profits:
            return "N/A"
        wins = sum(1 for p in profits if p > 0)
        return f"{wins / len(profits) * 100:.1f}%"
    
    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.LOCAL,
            status=AgentStatus.INACTIVE if self._is_sleeping else AgentStatus.ACTIVE,
            capabilities=["trading", "strategy_exploration"],
            metadata={
                "archetype": self.archetype.value,
                "dominant_style": self.strategy_explorer.get_dominant_style(),
                "personality": {
                    "risk": self.personality.risk,
                    "trust": self.personality.trust,
                    "memory": self.personality.memory,
                    "greed": self.personality.greed,
                    "learning": self.personality.learning,
                }
            }
        )


def create_town_agents(num_agents: int = 10, initial_capital: float = 10000.0) -> List[TownAgent]:
    archetypes = list(AgentArchetype)
    
    names = [
        "小明", "小红", "小华", "小丽", "小强",
        "小芳", "小伟", "小娟", "小军", "小燕",
        "小刚", "小梅", "小勇", "小英", "小杰"
    ]
    
    agents = []
    for i in range(num_agents):
        archetype = archetypes[i % len(archetypes)]
        name = names[i % len(names)]
        bedtime = random.randint(21, 23)
        wake_time = random.randint(5, 7)
        
        agent = TownAgent(
            agent_id=f"town_agent_{i}",
            name=f"{name}_{i}",
            initial_capital=initial_capital,
            archetype=archetype,
            bedtime=bedtime,
            wake_time=wake_time
        )
        
        if i % 3 == 0:
            agent.position = random.randint(50, 100)
            agent.capital = initial_capital * 0.5
        
        agents.append(agent)
    
    return agents
