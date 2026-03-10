"""
交易者智能体模块 - 不同交易策略的智能体
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random
import math

from .trading import Order, OrderType, OrderBook, TradingRules, MarketMaker


class TraderType(Enum):
    VALUE_INVESTOR = "value_investor"
    MOMENTUM_TRADER = "momentum_trader"
    MEAN_REVERSION = "mean_reversion"
    MARKET_MAKER = "market_maker"
    NOISE_TRADER = "noise_trader"
    ARBITRAGEUR = "arbitrageur"
    SENTIMENT_TRADER = "sentiment_trader"
    TECHNICAL_ANALYST = "technical_analyst"
    CONTRARIAN = "contrarian"
    ALGORITHMIC = "algorithmic"


TRADER_PROFILES = {
    TraderType.VALUE_INVESTOR: {
        "risk_tolerance": 0.3,
        "holding_period": "long",
        "position_size": 0.2,
        "stop_loss": 0.15,
        "take_profit": 0.30,
        "patience": 0.8,
    },
    TraderType.MOMENTUM_TRADER: {
        "risk_tolerance": 0.7,
        "holding_period": "short",
        "position_size": 0.15,
        "stop_loss": 0.05,
        "take_profit": 0.10,
        "patience": 0.3,
    },
    TraderType.MEAN_REVERSION: {
        "risk_tolerance": 0.5,
        "holding_period": "medium",
        "position_size": 0.12,
        "stop_loss": 0.08,
        "take_profit": 0.12,
        "patience": 0.6,
    },
    TraderType.MARKET_MAKER: {
        "risk_tolerance": 0.4,
        "holding_period": "very_short",
        "position_size": 0.1,
        "stop_loss": 0.02,
        "take_profit": 0.01,
        "patience": 0.2,
    },
    TraderType.NOISE_TRADER: {
        "risk_tolerance": 0.6,
        "holding_period": "random",
        "position_size": 0.1,
        "stop_loss": 0.10,
        "take_profit": 0.10,
        "patience": 0.1,
    },
    TraderType.ARBITRAGEUR: {
        "risk_tolerance": 0.2,
        "holding_period": "very_short",
        "position_size": 0.25,
        "stop_loss": 0.01,
        "take_profit": 0.02,
        "patience": 0.9,
    },
    TraderType.SENTIMENT_TRADER: {
        "risk_tolerance": 0.5,
        "holding_period": "medium",
        "position_size": 0.15,
        "stop_loss": 0.07,
        "take_profit": 0.15,
        "patience": 0.4,
    },
    TraderType.TECHNICAL_ANALYST: {
        "risk_tolerance": 0.6,
        "holding_period": "medium",
        "position_size": 0.18,
        "stop_loss": 0.06,
        "take_profit": 0.12,
        "patience": 0.5,
    },
    TraderType.CONTRARIAN: {
        "risk_tolerance": 0.5,
        "holding_period": "medium",
        "position_size": 0.15,
        "stop_loss": 0.10,
        "take_profit": 0.20,
        "patience": 0.7,
    },
    TraderType.ALGORITHMIC: {
        "risk_tolerance": 0.5,
        "holding_period": "variable",
        "position_size": 0.12,
        "stop_loss": 0.04,
        "take_profit": 0.08,
        "patience": 0.6,
    },
}


@dataclass
class Position:
    quantity: int = 0
    avg_cost: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def update(self, trade_quantity: int, trade_price: float, is_buy: bool):
        if is_buy:
            total_cost = self.avg_cost * self.quantity + trade_price * trade_quantity
            self.quantity += trade_quantity
            self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
        else:
            realized = (trade_price - self.avg_cost) * trade_quantity
            self.realized_pnl += realized
            self.quantity -= trade_quantity
            if self.quantity <= 0:
                self.quantity = 0
                self.avg_cost = 0.0
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        if self.quantity <= 0:
            self.unrealized_pnl = 0.0
        else:
            self.unrealized_pnl = (current_price - self.avg_cost) * self.quantity
        return self.unrealized_pnl
    
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl


@dataclass
class TraderAgent:
    id: int
    name: str
    trader_type: TraderType
    capital: float = 10000.0
    initial_capital: float = 10000.0
    position: Position = field(default_factory=Position)
    profile: Dict = field(default_factory=dict)
    pending_orders: List[int] = field(default_factory=list)
    trade_history: List[Dict] = field(default_factory=list)
    market_maker: Optional[MarketMaker] = None
    
    confidence: float = 0.5
    fear: float = 0.0
    greed: float = 0.5
    
    def __post_init__(self):
        self.profile = TRADER_PROFILES[self.trader_type].copy()
        self.initial_capital = self.capital
        
        if self.trader_type == TraderType.MARKET_MAKER:
            self.market_maker = MarketMaker(self.id)
    
    @property
    def total_value(self) -> float:
        return self.capital + self.position.quantity * getattr(self, '_last_price', 0)
    
    @property
    def total_pnl(self) -> float:
        return self.total_value - self.initial_capital
    
    @property
    def return_rate(self) -> float:
        return (self.total_value - self.initial_capital) / self.initial_capital
    
    def decide_order(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        self._update_emotions(market_state, technical)
        
        if self.trader_type == TraderType.MARKET_MAKER:
            return self._market_maker_strategy(order_book, market_state, timestamp)
        elif self.trader_type == TraderType.VALUE_INVESTOR:
            return self._value_strategy(order_book, market_state, technical, timestamp)
        elif self.trader_type == TraderType.MOMENTUM_TRADER:
            return self._momentum_strategy(order_book, market_state, technical, timestamp)
        elif self.trader_type == TraderType.MEAN_REVERSION:
            return self._mean_reversion_strategy(order_book, market_state, technical, timestamp)
        elif self.trader_type == TraderType.NOISE_TRADER:
            return self._noise_strategy(order_book, market_state, timestamp)
        elif self.trader_type == TraderType.SENTIMENT_TRADER:
            return self._sentiment_strategy(order_book, market_state, timestamp)
        elif self.trader_type == TraderType.TECHNICAL_ANALYST:
            return self._technical_strategy(order_book, market_state, technical, timestamp)
        elif self.trader_type == TraderType.CONTRARIAN:
            return self._contrarian_strategy(order_book, market_state, technical, timestamp)
        elif self.trader_type == TraderType.ALGORITHMIC:
            return self._algorithmic_strategy(order_book, market_state, technical, timestamp)
        else:
            return self._noise_strategy(order_book, market_state, timestamp)
    
    def _update_emotions(self, market_state: Dict, technical: Dict):
        pnl_rate = self.return_rate
        
        if pnl_rate > 0.1:
            self.greed = min(1.0, self.greed + 0.1)
            self.fear = max(0.0, self.fear - 0.05)
        elif pnl_rate < -0.1:
            self.fear = min(1.0, self.fear + 0.1)
            self.greed = max(0.0, self.greed - 0.05)
        
        if technical["rsi"] > 70:
            self.confidence = max(0.2, self.confidence - 0.1)
        elif technical["rsi"] < 30:
            self.confidence = min(0.8, self.confidence + 0.1)
        
        volatility = market_state.get("volatility", 0.02)
        if volatility > 0.03:
            self.fear = min(1.0, self.fear + 0.05)
    
    def _market_maker_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        timestamp: int
    ) -> Optional[Order]:
        if not self.market_maker:
            return None
        
        mid_price = market_state["price"]
        volatility = market_state.get("volatility", 0.02)
        
        buy_order, sell_order = self.market_maker.calculate_quotes(mid_price, volatility)
        buy_order.timestamp = timestamp
        sell_order.timestamp = timestamp
        
        if self.capital >= buy_order.price * buy_order.quantity:
            return buy_order if random.random() < 0.5 else sell_order
        
        return sell_order
    
    def _value_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        current_price = market_state["price"]
        fair_value = current_price * (1 + random.uniform(-0.1, 0.1))
        
        if current_price < fair_value * 0.95 and self.confidence > 0.4:
            return self._create_buy_order(current_price, order_book, timestamp)
        elif current_price > fair_value * 1.05 and self.position.quantity > 0:
            return self._create_sell_order(current_price, order_book, timestamp)
        
        return None
    
    def _momentum_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        momentum = technical.get("momentum", 0)
        trend = technical.get("trend_strength", 0)
        
        if momentum > 0.005 and trend > 0:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif momentum < -0.005 and self.position.quantity > 0:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _mean_reversion_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        rsi = technical.get("rsi", 50)
        
        if rsi < 30:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif rsi > 70 and self.position.quantity > 0:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _noise_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        timestamp: int
    ) -> Optional[Order]:
        if random.random() > 0.3:
            return None
        
        if random.random() < 0.5:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        else:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
    
    def _sentiment_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        timestamp: int
    ) -> Optional[Order]:
        phase = market_state.get("phase", "sideways")
        event = market_state.get("event", "none")
        
        bullish_events = ["earnings_beat", "merger_announcement"]
        bearish_events = ["earnings_miss", "regulatory_news"]
        
        if phase == "bull" or event in bullish_events:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif phase == "bear" or event in bearish_events:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _technical_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        rsi = technical.get("rsi", 50)
        macd_signal = technical.get("macd_signal", "bearish")
        trend = technical.get("trend_strength", 0)
        
        signals = 0
        if rsi < 40:
            signals += 1
        elif rsi > 60:
            signals -= 1
        
        if macd_signal == "bullish":
            signals += 1
        else:
            signals -= 1
        
        if trend > 0.01:
            signals += 1
        elif trend < -0.01:
            signals -= 1
        
        if signals >= 2:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif signals <= -2 and self.position.quantity > 0:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _contrarian_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        phase = market_state.get("phase", "sideways")
        rsi = technical.get("rsi", 50)
        
        if phase == "bear" and rsi < 35:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif phase == "bull" and rsi > 65 and self.position.quantity > 0:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _algorithmic_strategy(
        self,
        order_book: OrderBook,
        market_state: Dict,
        technical: Dict,
        timestamp: int
    ) -> Optional[Order]:
        score = 0
        
        rsi = technical.get("rsi", 50)
        if rsi < 30:
            score += 2
        elif rsi < 40:
            score += 1
        elif rsi > 70:
            score -= 2
        elif rsi > 60:
            score -= 1
        
        momentum = technical.get("momentum", 0)
        if momentum > 0.003:
            score += 1
        elif momentum < -0.003:
            score -= 1
        
        trend = technical.get("trend_strength", 0)
        if trend > 0.02:
            score += 1
        elif trend < -0.02:
            score -= 1
        
        if score >= 2:
            return self._create_buy_order(market_state["price"], order_book, timestamp)
        elif score <= -2 and self.position.quantity > 0:
            return self._create_sell_order(market_state["price"], order_book, timestamp)
        
        return None
    
    def _create_buy_order(
        self,
        current_price: float,
        order_book: OrderBook,
        timestamp: int
    ) -> Optional[Order]:
        position_size = self.profile["position_size"] * self.capital
        
        best_bid, best_ask, spread = order_book.get_spread()
        
        if spread < 0.01 and best_ask:
            price = best_ask
        else:
            price = current_price * random.uniform(0.98, 1.0)
        
        price = round(price, 2)
        quantity = int(position_size / price) if price > 0 else 0
        quantity = max(1, min(quantity, TradingRules.MAX_ORDER_QUANTITY))
        
        if self.capital < price * quantity * (1 + TradingRules.TRADING_FEE_RATE):
            quantity = int(self.capital / (price * (1 + TradingRules.TRADING_FEE_RATE)))
        
        if quantity <= 0:
            return None
        
        return Order(
            order_id=0,
            agent_id=self.id,
            order_type=OrderType.BUY,
            price=price,
            quantity=quantity,
            timestamp=timestamp
        )
    
    def _create_sell_order(
        self,
        current_price: float,
        order_book: OrderBook,
        timestamp: int
    ) -> Optional[Order]:
        if self.position.quantity <= 0:
            return None
        
        best_bid, best_ask, spread = order_book.get_spread()
        
        if spread < 0.01 and best_bid:
            price = best_bid
        else:
            price = current_price * random.uniform(1.0, 1.02)
        
        price = round(price, 2)
        quantity = min(
            self.position.quantity,
            int(self.profile["position_size"] * self.capital / price)
        )
        quantity = max(1, quantity)
        
        return Order(
            order_id=0,
            agent_id=self.id,
            order_type=OrderType.SELL,
            price=price,
            quantity=quantity,
            timestamp=timestamp
        )
    
    def execute_trade(
        self,
        is_buy: bool,
        quantity: int,
        price: float,
        fee: float
    ):
        if is_buy:
            total_cost = price * quantity + fee
            if self.capital >= total_cost:
                self.capital -= total_cost
                self.position.update(quantity, price, True)
                self.trade_history.append({
                    "type": "buy",
                    "quantity": quantity,
                    "price": price,
                    "fee": fee
                })
        else:
            revenue = price * quantity - fee
            self.capital += revenue
            self.position.update(quantity, price, False)
            self.trade_history.append({
                "type": "sell",
                "quantity": quantity,
                "price": price,
                "fee": fee
            })
        
        self._last_price = price
    
    def update_position_value(self, current_price: float):
        self._last_price = current_price
        self.position.calculate_unrealized_pnl(current_price)
    
    def get_status(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.trader_type.value,
            "capital": round(self.capital, 2),
            "position": self.position.quantity,
            "avg_cost": round(self.position.avg_cost, 2),
            "unrealized_pnl": round(self.position.unrealized_pnl, 2),
            "realized_pnl": round(self.position.realized_pnl, 2),
            "total_value": round(self.total_value, 2),
            "return_rate": f"{self.return_rate*100:.2f}%",
            "trades": len(self.trade_history),
            "confidence": round(self.confidence, 2),
            "fear": round(self.fear, 2),
            "greed": round(self.greed, 2),
        }


def create_traders(num_traders: int = 10, initial_capital: float = 10000.0) -> List[TraderAgent]:
    trader_types = list(TraderType)
    
    names = [
        "Warren", "George", "Jesse", "Jim", "Ray",
        "Paul", "John", "Steve", "Michael", "David",
        "Peter", "Bill", "Carl", "Mark", "Tom"
    ]
    
    traders = []
    for i in range(num_traders):
        trader_type = trader_types[i % len(trader_types)]
        name = names[i % len(names)]
        
        trader = TraderAgent(
            id=i,
            name=f"{name}_{i}",
            trader_type=trader_type,
            capital=initial_capital
        )
        traders.append(trader)
    
    return traders
