"""
永不纳什小镇 - A股市场模拟系统
完整的A股交易规则
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import random
import math


class MarketPhase(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


class MarketEvent(Enum):
    NONE = "none"
    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    MERGER_ANNOUNCEMENT = "merger_announcement"
    REGULATORY_NEWS = "regulatory_news"
    MACRO_ECONOMIC = "macro_economic"
    INSIDER_TRADING = "insider_trading"
    SHORT_SQUEEZE = "short_squeeze"
    SPECIAL_DIVIDEND = "special_dividend"


class TradingSession(Enum):
    PRE_MARKET = "pre_market"
    OPENING_CALL = "opening_call"
    MORNING_CONTINUOUS = "morning_continuous"
    LUNCH_BREAK = "lunch_break"
    AFTERNOON_CONTINUOUS = "afternoon_continuous"
    CLOSING_CALL = "closing_call"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


@dataclass
class MarketState:
    current_price: float = 100.0
    previous_price: float = 100.0
    day_open: float = 100.0
    day_high: float = 100.0
    day_low: float = 100.0
    volume: int = 0
    turnover: float = 0.0
    phase: MarketPhase = MarketPhase.SIDEWAYS
    event: MarketEvent = MarketEvent.NONE
    volatility: float = 0.02
    trend_strength: float = 0.0
    momentum: float = 0.0
    rsi: float = 50.0
    macd: float = 0.0
    signal_line: float = 0.0


@dataclass
class PriceCandle:
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    timestamp: int


class PriceGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.long_term_trend = 0.0001
        self.trend_cycle_position = 0.0
        self.trend_cycle_length = 252
        
        self.short_term_volatility = 0.01
        self.medium_term_volatility = 0.02
        
        self.mean_reversion_strength = 0.1
        self.fair_value = 100.0
        
        self.volatility_cluster = 1.0
        self.volatility_persistence = 0.95
    
    def update_long_term_trend(self, day: int):
        self.trend_cycle_position = (day % self.trend_cycle_length) / self.trend_cycle_length
        cycle_factor = math.sin(2 * math.pi * self.trend_cycle_position)
        
        self.long_term_trend = 0.0003 * cycle_factor
        
        if random.random() < 0.01:
            self.long_term_trend += random.uniform(-0.0005, 0.0005)
    
    def generate_price_change(
        self,
        current_price: float,
        phase: MarketPhase,
        event: MarketEvent,
        tick_count: int
    ) -> tuple:
        self._update_volatility_cluster()
        
        long_term_change = self.long_term_trend
        
        medium_term_change = self._generate_medium_term_change(phase)
        short_term_change = self._generate_short_term_change()
        
        deviation = (current_price - self.fair_value) / self.fair_value
        mean_reversion = -self.mean_reversion_strength * deviation
        
        event_impact = self._get_event_impact(event)
        
        total_change = (
            long_term_change +
            medium_term_change +
            short_term_change +
            mean_reversion +
            event_impact
        )
        
        phase_multiplier = self._get_phase_multiplier(phase)
        total_change *= phase_multiplier
        total_change *= self.volatility_cluster
        
        new_price = current_price * (1 + total_change)
        new_price = max(1.0, new_price)
        
        actual_volatility = abs(total_change)
        
        return new_price, actual_volatility
    
    def _generate_medium_term_change(self, phase: MarketPhase) -> float:
        base_vol = self.medium_term_volatility
        
        if phase == MarketPhase.BULL:
            return random.gauss(0.001, base_vol * 0.8)
        elif phase == MarketPhase.BEAR:
            return random.gauss(-0.001, base_vol * 0.8)
        elif phase == MarketPhase.VOLATILE:
            return random.gauss(0, base_vol * 1.5)
        else:
            return random.gauss(0, base_vol)
    
    def _generate_short_term_change(self) -> float:
        return random.gauss(0, self.short_term_volatility)
    
    def _update_volatility_cluster(self):
        if random.random() < 0.1:
            self.volatility_cluster = random.uniform(0.5, 2.0)
        else:
            self.volatility_cluster = (
                self.volatility_persistence * self.volatility_cluster +
                (1 - self.volatility_persistence) * 1.0
            )
    
    def _get_event_impact(self, event: MarketEvent) -> float:
        impacts = {
            MarketEvent.NONE: 0.0,
            MarketEvent.EARNINGS_BEAT: random.uniform(0.02, 0.05),
            MarketEvent.EARNINGS_MISS: random.uniform(-0.05, -0.02),
            MarketEvent.MERGER_ANNOUNCEMENT: random.uniform(-0.1, 0.1),
            MarketEvent.REGULATORY_NEWS: random.uniform(-0.08, 0.08),
            MarketEvent.MACRO_ECONOMIC: random.uniform(-0.05, 0.05),
            MarketEvent.INSIDER_TRADING: random.uniform(-0.03, 0.03),
            MarketEvent.SHORT_SQUEEZE: random.uniform(0.05, 0.15),
            MarketEvent.SPECIAL_DIVIDEND: random.uniform(0.02, 0.05),
        }
        return impacts.get(event, 0.0)
    
    def _get_phase_multiplier(self, phase: MarketPhase) -> float:
        multipliers = {
            MarketPhase.BULL: 1.2,
            MarketPhase.BEAR: 1.3,
            MarketPhase.SIDEWAYS: 0.8,
            MarketPhase.VOLATILE: 1.8,
        }
        return multipliers.get(phase, 1.0)


class AShareMarket:
    def __init__(self, initial_price: float = 100.0, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.state = MarketState(current_price=initial_price)
        self.price_history: List[float] = [initial_price]
        self.candle_history: List[PriceCandle] = []
        self.day = 0
        self.hour = 9
        
        self._price_generator = PriceGenerator(seed)
    
    def tick(self, volume: int = 0) -> MarketState:
        new_price, volatility = self._price_generator.generate_price_change(
            self.state.current_price,
            self.state.phase,
            self.state.event,
            len(self.price_history)
        )
        
        self.state.previous_price = self.state.current_price
        self.state.current_price = new_price
        self.state.volatility = volatility
        
        if volume > 0:
            self.state.volume += volume
            self.state.turnover += volume * new_price
        
        if new_price > self.state.day_high:
            self.state.day_high = new_price
        if new_price < self.state.day_low:
            self.state.day_low = new_price
        
        self.price_history.append(new_price)
        self._update_phase()
        
        return self.state
    
    def _update_phase(self):
        if len(self.price_history) < 20:
            return
        
        recent_return = (self.state.current_price - self.price_history[-20]) / self.price_history[-20]
        recent_volatility = self._calculate_recent_volatility(20)
        
        if recent_volatility > 0.03:
            self.state.phase = MarketPhase.VOLATILE
        elif recent_return > 0.05:
            self.state.phase = MarketPhase.BULL
        elif recent_return < -0.05:
            self.state.phase = MarketPhase.BEAR
        else:
            self.state.phase = MarketPhase.SIDEWAYS
    
    def _calculate_recent_volatility(self, period: int) -> float:
        if len(self.price_history) < period + 1:
            return 0.02
        
        returns = []
        for i in range(1, period + 1):
            r = (self.price_history[-i] - self.price_history[-i-1]) / self.price_history[-i-1]
            returns.append(r)
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        
        return math.sqrt(variance)
    
    def get_session(self, hour: int) -> TradingSession:
        if hour < 9:
            return TradingSession.PRE_MARKET
        elif hour == 9:
            return TradingSession.OPENING_CALL
        elif 9 < hour < 11:
            return TradingSession.MORNING_CONTINUOUS
        elif 11 <= hour < 13:
            return TradingSession.LUNCH_BREAK
        elif 13 <= hour < 15:
            return TradingSession.AFTERNOON_CONTINUOUS
        elif hour == 15:
            return TradingSession.CLOSING_CALL
        elif 15 < hour < 18:
            return TradingSession.AFTER_HOURS
        else:
            return TradingSession.CLOSED
    
    def is_trading_hour(self, hour: int) -> bool:
        session = self.get_session(hour)
        return session in [
            TradingSession.OPENING_CALL,
            TradingSession.MORNING_CONTINUOUS,
            TradingSession.AFTERNOON_CONTINUOUS,
            TradingSession.CLOSING_CALL,
        ]
    
    def new_day(self):
        self.day += 1
        self.state.day_open = self.state.current_price
        self.state.day_high = self.state.current_price
        self.state.day_low = self.state.current_price
        self.state.volume = 0
        self.state.turnover = 0.0
        self._price_generator.update_long_term_trend(self.day)
    
    def get_summary(self) -> Dict:
        change = self.state.current_price - self.state.day_open
        change_pct = (change / self.state.day_open) * 100 if self.state.day_open > 0 else 0.0
        
        return {
            "price": round(self.state.current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "day_high": round(self.state.day_high, 2),
            "day_low": round(self.state.day_low, 2),
            "volume": self.state.volume,
            "turnover": round(self.state.turnover, 2),
            "phase": self.state.phase.value,
            "event": self.state.event.value,
            "volatility": round(self.state.volatility, 4),
        }
    
    def get_market_summary(self) -> Dict:
        return self.get_summary()
    
    def get_technical_analysis(self) -> Dict:
        return {
            "rsi": self.state.rsi,
            "macd": self.state.macd,
            "signal_line": self.state.signal_line,
            "momentum": self.state.momentum,
            "trend_strength": self.state.trend_strength,
            "bollinger_upper": self.state.current_price * 1.02,
            "bollinger_middle": self.state.current_price,
            "bollinger_lower": self.state.current_price * 0.98,
        }
