"""
市场模块 - 股票价格波动、市场状态、长期规律与短期波动
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import random


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


@dataclass
class PriceCandle:
    timestamp: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    
    @property
    def body_size(self) -> float:
        return abs(self.close_price - self.open_price)
    
    @property
    def range_size(self) -> float:
        return self.high_price - self.low_price
    
    @property
    def is_bullish(self) -> bool:
        return self.close_price > self.open_price


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


class PriceGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.long_term_trend = 0.0001
        self.trend_cycle_position = 0.0
        self.trend_cycle_length = 252
        
        self.short_term_volatility = 0.01
        self.medium_term_volatility = 0.02
        self.long_term_volatility = 0.005
        
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
        market_phase: MarketPhase,
        event: MarketEvent,
        timestamp: int
    ) -> Tuple[float, float]:
        self._update_volatility_cluster()
        
        long_term_change = self.long_term_trend
        
        medium_term_change = self._generate_medium_term_change(market_phase)
        
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
        
        phase_multiplier = self._get_phase_multiplier(market_phase)
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
            MarketEvent.MERGER_ANNOUNCEMENT: random.uniform(-0.03, 0.08),
            MarketEvent.REGULATORY_NEWS: random.uniform(-0.08, 0.02),
            MarketEvent.MACRO_ECONOMIC: random.uniform(-0.04, 0.04),
            MarketEvent.INSIDER_TRADING: random.uniform(-0.02, 0.02),
            MarketEvent.SHORT_SQUEEZE: random.uniform(0.05, 0.15),
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
    
    def update_fair_value(self, new_value: float):
        self.fair_value = 0.95 * self.fair_value + 0.05 * new_value


class TechnicalIndicators:
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[float, float]:
        if len(prices) < slow_period:
            return 0.0, 0.0
        
        ema_fast = TechnicalIndicators._calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators._calculate_ema(prices, slow_period)
        
        macd = ema_fast - ema_slow
        
        macd_history = []
        for i in range(slow_period, len(prices)):
            fast = TechnicalIndicators._calculate_ema(prices[:i+1], fast_period)
            slow = TechnicalIndicators._calculate_ema(prices[:i+1], slow_period)
            macd_history.append(fast - slow)
        
        signal = TechnicalIndicators._calculate_ema(macd_history, signal_period) if len(macd_history) >= signal_period else 0.0
        
        return macd, signal
    
    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> float:
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        if len(prices) < period:
            last = prices[-1] if prices else 100.0
            return last, last, last
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std = math.sqrt(variance)
        
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        
        return upper, sma, lower


class StockMarket:
    def __init__(self, initial_price: float = 100.0, seed: Optional[int] = None):
        self.state = MarketState(current_price=initial_price)
        self.price_generator = PriceGenerator(seed)
        self.price_history: List[float] = [initial_price]
        self.candle_history: List[PriceCandle] = []
        self.day = 0
        self.hour = 9
        
        self._update_phase()
    
    def tick(self, volume: int = 0) -> MarketState:
        new_price, volatility = self.price_generator.generate_price_change(
            self.state.current_price,
            self.state.phase,
            self.state.event,
            len(self.price_history)
        )
        
        self.state.previous_price = self.state.current_price
        self.state.current_price = new_price
        self.state.volatility = volatility
        
        self.state.day_high = max(self.state.day_high, new_price)
        self.state.day_low = min(self.state.day_low, new_price)
        
        self.state.volume += volume
        self.state.turnover += volume * new_price
        
        self.price_history.append(new_price)
        self.price_generator.update_fair_value(new_price)
        
        self._update_indicators()
        self._update_momentum()
        
        if random.random() < 0.05:
            self._update_phase()
        
        if random.random() < 0.02:
            self._trigger_event()
        elif self.state.event != MarketEvent.NONE:
            if random.random() < 0.8:
                self.state.event = MarketEvent.NONE
        
        return self.state
    
    def _update_indicators(self):
        self.state.rsi = TechnicalIndicators.calculate_rsi(self.price_history)
        self.state.macd, self.state.signal_line = TechnicalIndicators.calculate_macd(self.price_history)
    
    def _update_momentum(self):
        if len(self.price_history) >= 2:
            recent_change = (self.price_history[-1] - self.price_history[-2]) / self.price_history[-2]
            self.state.momentum = 0.9 * self.state.momentum + 0.1 * recent_change
        
        if len(self.price_history) >= 10:
            short_ma = sum(self.price_history[-5:]) / 5
            long_ma = sum(self.price_history[-10:]) / 10
            self.state.trend_strength = (short_ma - long_ma) / long_ma
    
    def _update_phase(self):
        if len(self.price_history) < 20:
            return
        
        recent_return = (self.price_history[-1] - self.price_history[-20]) / self.price_history[-20]
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
    
    def _trigger_event(self):
        events = list(MarketEvent)
        events.remove(MarketEvent.NONE)
        self.state.event = random.choice(events)
    
    def new_day(self):
        self.day += 1
        self.hour = 9
        
        candle = PriceCandle(
            timestamp=len(self.candle_history),
            open_price=self.state.day_open,
            high_price=self.state.day_high,
            low_price=self.state.day_low,
            close_price=self.state.current_price,
            volume=self.state.volume
        )
        self.candle_history.append(candle)
        
        self.state.day_open = self.state.current_price
        self.state.day_high = self.state.current_price
        self.state.day_low = self.state.current_price
        self.state.volume = 0
        self.state.turnover = 0.0
        
        self.price_generator.update_long_term_trend(self.day)
        self._update_phase()
    
    def get_market_summary(self) -> Dict:
        change = self.state.current_price - self.state.day_open
        change_pct = (change / self.state.day_open) * 100 if self.state.day_open > 0 else 0
        
        return {
            "price": round(self.state.current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "day_high": round(self.state.day_high, 2),
            "day_low": round(self.state.day_low, 2),
            "volume": self.state.volume,
            "phase": self.state.phase.value,
            "event": self.state.event.value,
            "volatility": round(self.state.volatility, 4),
            "rsi": round(self.state.rsi, 1),
            "momentum": round(self.state.momentum, 4),
        }
    
    def get_technical_analysis(self) -> Dict:
        upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(self.price_history)
        
        return {
            "rsi": round(self.state.rsi, 1),
            "macd": round(self.state.macd, 4),
            "signal_line": round(self.state.signal_line, 4),
            "macd_signal": "bullish" if self.state.macd > self.state.signal_line else "bearish",
            "bollinger_upper": round(upper, 2),
            "bollinger_middle": round(middle, 2),
            "bollinger_lower": round(lower, 2),
            "trend_strength": round(self.state.trend_strength, 4),
            "momentum": round(self.state.momentum, 4),
        }
