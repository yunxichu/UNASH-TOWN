"""
永不纳什小镇 - 开放式策略探索系统
智能体自主探索交易策略，通过反馈学习调整风格
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random
import math


class StrategyType(Enum):
    VALUE = "value"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    CONTRARIAN = "contrarian"
    TREND_FOLLOWING = "trend_following"


class ActionType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REDUCE = "reduce"
    ADD = "add"


@dataclass
class StrategyBelief:
    strategy: StrategyType
    confidence: float
    success_count: int = 0
    fail_count: int = 0
    total_profit: float = 0.0
    recent_results: List[float] = field(default_factory=list)
    
    def expected_value(self) -> float:
        if self.success_count + self.fail_count == 0:
            return 0.0
        success_rate = self.success_count / (self.success_count + self.fail_count)
        avg_profit = self.total_profit / max(1, self.success_count + self.fail_count)
        return success_rate * avg_profit
    
    def update(self, profit: float, success: bool):
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        self.total_profit += profit
        self.recent_results.append(profit)
        if len(self.recent_results) > 20:
            self.recent_results.pop(0)
        self._adjust_confidence()
    
    def _adjust_confidence(self):
        if len(self.recent_results) >= 5:
            recent_avg = sum(self.recent_results[-5:]) / 5
            if recent_avg > 0:
                self.confidence = min(1.0, self.confidence + 0.05)
            else:
                self.confidence = max(0.1, self.confidence - 0.05)


@dataclass
class MarketView:
    trend: str = "neutral"
    strength: float = 0.0
    volatility: float = 0.02
    overbought: bool = False
    oversold: bool = False
    support: float = 0.0
    resistance: float = 0.0
    

@dataclass
class TradingStyle:
    risk_tolerance: float = 0.5
    position_size: float = 0.1
    hold_period: int = 5
    stop_loss: float = 0.05
    take_profit: float = 0.10
    entry_aggression: float = 0.5
    exit_patience: float = 0.5
    
    def mutate(self, rate: float = 0.1):
        if random.random() < rate:
            self.risk_tolerance = max(0.1, min(0.9, self.risk_tolerance + random.uniform(-0.1, 0.1)))
        if random.random() < rate:
            self.position_size = max(0.05, min(0.3, self.position_size + random.uniform(-0.05, 0.05)))
        if random.random() < rate:
            self.stop_loss = max(0.02, min(0.15, self.stop_loss + random.uniform(-0.02, 0.02)))
        if random.random() < rate:
            self.take_profit = max(0.05, min(0.20, self.take_profit + random.uniform(-0.02, 0.02)))


class StrategyExplorer:
    def __init__(
        self,
        initial_tendency: Dict[str, float] = None,
        exploration_rate: float = 0.2,
        learning_rate: float = 0.1
    ):
        self.beliefs: Dict[StrategyType, StrategyBelief] = {}
        self.exploration_rate = exploration_rate
        self.learning_rate = learning_rate
        
        for strategy in StrategyType:
            initial_confidence = 0.5
            if initial_tendency:
                if strategy == StrategyType.VALUE and initial_tendency.get("value", 0) > 0.5:
                    initial_confidence = 0.7
                elif strategy == StrategyType.MOMENTUM and initial_tendency.get("momentum", 0) > 0.5:
                    initial_confidence = 0.7
                elif strategy == StrategyType.MEAN_REVERSION and initial_tendency.get("mean_reversion", 0) > 0.5:
                    initial_confidence = 0.7
            
            self.beliefs[strategy] = StrategyBelief(
                strategy=strategy,
                confidence=initial_confidence
            )
        
        self.style = TradingStyle()
        self.current_strategy: Optional[StrategyType] = None
        self.trade_history: List[Dict] = []
        self.style_history: List[TradingStyle] = []
        
        self._recent_pnl: List[float] = []
        self._strategy_switches: int = 0
    
    def analyze_market(self, market_data: Dict) -> MarketView:
        view = MarketView()
        
        price = market_data.get("price", 100)
        ma_short = market_data.get("ma_short", price)
        ma_long = market_data.get("ma_long", price)
        rsi = market_data.get("rsi", 50)
        volatility = market_data.get("volatility", 0.02)
        
        if ma_short > ma_long:
            view.trend = "up"
            view.strength = min(1.0, (ma_short - ma_long) / ma_long * 10)
        elif ma_short < ma_long:
            view.trend = "down"
            view.strength = min(1.0, (ma_long - ma_short) / ma_long * 10)
        
        view.volatility = volatility
        
        if rsi > 70:
            view.overbought = True
        elif rsi < 30:
            view.oversold = True
        
        prices = market_data.get("price_history", [price])
        if len(prices) > 20:
            view.support = min(prices[-20:])
            view.resistance = max(prices[-20:])
        
        return view
    
    def select_strategy(self, market_view: MarketView) -> StrategyType:
        if random.random() < self.exploration_rate:
            return self._explore_new_strategy()
        
        scores = {}
        for strategy_type, belief in self.beliefs.items():
            base_score = belief.confidence * (1 + belief.expected_value())
            context_score = self._context_match(strategy_type, market_view)
            scores[strategy_type] = base_score * (0.7 + 0.3 * context_score)
        
        if self.current_strategy:
            scores[self.current_strategy] *= 1.1
        
        best_strategy = max(scores, key=scores.get)
        
        if best_strategy != self.current_strategy:
            self._strategy_switches += 1
            self.current_strategy = best_strategy
        
        return best_strategy
    
    def _explore_new_strategy(self) -> StrategyType:
        weights = [b.confidence for b in self.beliefs.values()]
        total = sum(weights)
        if total == 0:
            return random.choice(list(StrategyType))
        
        weights = [w / total for w in weights]
        return random.choices(list(StrategyType), weights=weights)[0]
    
    def _context_match(self, strategy: StrategyType, view: MarketView) -> float:
        match_score = 0.5
        
        if strategy == StrategyType.MOMENTUM:
            if view.trend in ["up", "down"] and view.strength > 0.3:
                match_score = 0.8
            else:
                match_score = 0.3
        
        elif strategy == StrategyType.MEAN_REVERSION:
            if view.overbought or view.oversold:
                match_score = 0.9
            elif view.volatility > 0.03:
                match_score = 0.7
            else:
                match_score = 0.4
        
        elif strategy == StrategyType.BREAKOUT:
            if view.volatility > 0.025:
                match_score = 0.7
            else:
                match_score = 0.4
        
        elif strategy == StrategyType.VALUE:
            if view.oversold:
                match_score = 0.8
            else:
                match_score = 0.5
        
        elif strategy == StrategyType.CONTRARIAN:
            if view.overbought:
                match_score = 0.8
            elif view.oversold:
                match_score = 0.7
            else:
                match_score = 0.3
        
        elif strategy == StrategyType.TREND_FOLLOWING:
            if view.trend != "neutral" and view.strength > 0.2:
                match_score = 0.8
            else:
                match_score = 0.3
        
        elif strategy == StrategyType.SCALPING:
            if view.volatility < 0.02:
                match_score = 0.7
            else:
                match_score = 0.4
        
        elif strategy == StrategyType.SWING:
            match_score = 0.6
        
        return match_score
    
    def decide_action(
        self,
        strategy: StrategyType,
        market_view: MarketView,
        market_data: Dict,
        agent_state: Dict
    ) -> Tuple[ActionType, Optional[float], Optional[int]]:
        price = market_data.get("price", 100)
        capital = agent_state.get("capital", 10000)
        position = agent_state.get("position", 0)
        avg_cost = agent_state.get("avg_cost", price)
        
        action = ActionType.HOLD
        action_price = None
        quantity = None
        
        if strategy == StrategyType.VALUE:
            action, action_price, quantity = self._value_strategy(
                market_view, price, capital, position
            )
        
        elif strategy == StrategyType.MOMENTUM:
            action, action_price, quantity = self._momentum_strategy(
                market_view, price, capital, position
            )
        
        elif strategy == StrategyType.MEAN_REVERSION:
            action, action_price, quantity = self._mean_reversion_strategy(
                market_view, price, capital, position
            )
        
        elif strategy == StrategyType.BREAKOUT:
            action, action_price, quantity = self._breakout_strategy(
                market_view, price, capital, position, market_data
            )
        
        elif strategy == StrategyType.SCALPING:
            action, action_price, quantity = self._scalping_strategy(
                market_view, price, capital, position
            )
        
        elif strategy == StrategyType.SWING:
            action, action_price, quantity = self._swing_strategy(
                market_view, price, capital, position, avg_cost
            )
        
        elif strategy == StrategyType.CONTRARIAN:
            action, action_price, quantity = self._contrarian_strategy(
                market_view, price, capital, position
            )
        
        elif strategy == StrategyType.TREND_FOLLOWING:
            action, action_price, quantity = self._trend_following_strategy(
                market_view, price, capital, position
            )
        
        if action == ActionType.BUY and quantity:
            quantity = int(min(quantity, capital / (price * 1.001)))
            if quantity <= 0:
                action = ActionType.HOLD
                quantity = None
        
        elif action == ActionType.SELL and quantity:
            quantity = min(quantity, position)
            if quantity <= 0:
                action = ActionType.HOLD
                quantity = None
        
        return action, action_price, quantity
    
    def _value_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if view.oversold and position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.BUY, price * 0.995, qty
        elif view.overbought and position > 0:
            return ActionType.SELL, price * 1.005, position
        elif position == 0 and random.random() < 0.1 * self.style.risk_tolerance:
            qty = int(capital * self.style.position_size * 0.5 / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        elif position > 0 and random.random() < 0.05:
            return ActionType.SELL, price * random.uniform(0.998, 1.002), int(position * 0.3)
        return ActionType.HOLD, None, None
    
    def _momentum_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if view.trend == "up" and view.strength > 0.3:
            if position == 0:
                qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
                return ActionType.BUY, price * 1.002, qty
            else:
                qty = int(capital * self.style.position_size * 0.5 / price)
                return ActionType.ADD, price * 1.001, qty
        elif view.trend == "down" and position > 0:
            return ActionType.SELL, price * 0.999, int(position * 0.5)
        elif position == 0 and random.random() < 0.15 * self.style.risk_tolerance:
            qty = int(capital * self.style.position_size / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        return ActionType.HOLD, None, None
    
    def _mean_reversion_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if view.overbought and position > 0:
            return ActionType.SELL, price * 0.998, position
        elif view.oversold and position == 0:
            qty = int(capital * self.style.position_size / price)
            return ActionType.BUY, price * 1.002, qty
        elif position == 0 and random.random() < 0.1:
            qty = int(capital * self.style.position_size * 0.5 / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        return ActionType.HOLD, None, None
    
    def _breakout_strategy(self, view, price, capital, position, market_data) -> Tuple[ActionType, Optional[float], Optional[int]]:
        resistance = market_data.get("resistance", price * 1.05)
        support = market_data.get("support", price * 0.95)
        
        if price > resistance * 0.99 and position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.BUY, price * 1.003, qty
        elif price < support * 1.01 and position > 0:
            return ActionType.SELL, price * 0.997, position
        elif position == 0 and random.random() < 0.1 * self.style.risk_tolerance:
            qty = int(capital * self.style.position_size / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        return ActionType.HOLD, None, None
    
    def _scalping_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if position == 0:
            qty = int(capital * self.style.position_size * 0.5 / price)
            return ActionType.BUY, price * 0.998, qty
        elif position > 0:
            return ActionType.SELL, price * 1.002, position
        return ActionType.HOLD, None, None
    
    def _swing_strategy(self, view, price, capital, position, avg_cost) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        else:
            profit_pct = (price - avg_cost) / avg_cost if avg_cost > 0 else 0
            if profit_pct > self.style.take_profit:
                return ActionType.SELL, price * 0.998, position
            elif profit_pct < -self.style.stop_loss:
                return ActionType.SELL, price * 0.998, int(position * 0.5)
            elif random.random() < 0.1:
                return ActionType.SELL, price * random.uniform(0.998, 1.002), int(position * 0.3)
        return ActionType.HOLD, None, None
    
    def _contrarian_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if view.overbought and position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.SELL, price * 0.998, qty
        elif view.oversold and position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.BUY, price * 1.002, qty
        elif position == 0 and random.random() < 0.1:
            qty = int(capital * self.style.position_size * 0.5 / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        elif position > 0 and random.random() < 0.1:
            return ActionType.SELL, price * random.uniform(0.998, 1.002), int(position * 0.5)
        return ActionType.HOLD, None, None
    
    def _trend_following_strategy(self, view, price, capital, position) -> Tuple[ActionType, Optional[float], Optional[int]]:
        if view.trend == "up" and position == 0:
            qty = int(capital * self.style.position_size * self.style.risk_tolerance / price)
            return ActionType.BUY, price * 1.001, qty
        elif view.trend == "down" and position > 0:
            return ActionType.SELL, price * 0.999, position
        elif position == 0 and random.random() < 0.1 * self.style.risk_tolerance:
            qty = int(capital * self.style.position_size / price)
            return ActionType.BUY, price * random.uniform(0.995, 1.005), qty
        elif position > 0 and random.random() < 0.05:
            return ActionType.SELL, price * random.uniform(0.998, 1.002), int(position * 0.3)
        return ActionType.HOLD, None, None
    
    def record_trade_result(
        self,
        strategy: StrategyType,
        action: ActionType,
        profit: float,
        success: bool
    ):
        self.beliefs[strategy].update(profit, success)
        
        self._recent_pnl.append(profit)
        if len(self._recent_pnl) > 50:
            self._recent_pnl.pop(0)
        
        self.trade_history.append({
            "strategy": strategy.value,
            "action": action.value,
            "profit": profit,
            "success": success
        })
        
        self._adapt_style()
    
    def _adapt_style(self):
        if len(self._recent_pnl) < 10:
            return
        
        recent_avg = sum(self._recent_pnl[-10:]) / 10
        recent_vol = self._calculate_volatility(self._recent_pnl[-10:])
        
        if recent_avg < 0:
            self.style.risk_tolerance = max(0.1, self.style.risk_tolerance - 0.02)
            self.style.position_size = max(0.05, self.style.position_size - 0.01)
        elif recent_avg > 0 and recent_vol < 0.02:
            self.style.risk_tolerance = min(0.9, self.style.risk_tolerance + 0.01)
            self.style.position_size = min(0.25, self.style.position_size + 0.005)
        
        if recent_vol > 0.03:
            self.style.stop_loss = max(0.02, self.style.stop_loss - 0.005)
        else:
            self.style.stop_loss = min(0.10, self.style.stop_loss + 0.002)
        
        self.style_history.append(TradingStyle(
            risk_tolerance=self.style.risk_tolerance,
            position_size=self.style.position_size,
            hold_period=self.style.hold_period,
            stop_loss=self.style.stop_loss,
            take_profit=self.style.take_profit,
            entry_aggression=self.style.entry_aggression,
            exit_patience=self.style.exit_patience
        ))
    
    def _calculate_volatility(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)
    
    def get_dominant_style(self) -> str:
        if not self.trade_history:
            return "探索中"
        
        recent_strategies = [t["strategy"] for t in self.trade_history[-20:]]
        if not recent_strategies:
            return "探索中"
        
        from collections import Counter
        counts = Counter(recent_strategies)
        dominant = counts.most_common(1)[0][0]
        
        style_names = {
            "value": "价值投资者",
            "momentum": "动量交易者",
            "mean_reversion": "均值回归者",
            "breakout": "突破交易者",
            "scalping": "短线客",
            "swing": "波段交易者",
            "contrarian": "逆向投资者",
            "trend_following": "趋势跟随者"
        }
        return style_names.get(dominant, "混合型")
    
    def get_status(self) -> Dict:
        return {
            "current_strategy": self.current_strategy.value if self.current_strategy else None,
            "dominant_style": self.get_dominant_style(),
            "exploration_rate": round(self.exploration_rate, 2),
            "style": {
                "risk_tolerance": round(self.style.risk_tolerance, 2),
                "position_size": round(self.style.position_size, 2),
                "stop_loss": round(self.style.stop_loss, 2),
                "take_profit": round(self.style.take_profit, 2),
            },
            "strategy_confidence": {
                s.value: round(b.confidence, 2) 
                for s, b in self.beliefs.items()
            },
            "total_trades": len(self.trade_history),
            "strategy_switches": self._strategy_switches,
            "recent_pnl": round(sum(self._recent_pnl[-10:]), 2) if self._recent_pnl else 0,
        }
