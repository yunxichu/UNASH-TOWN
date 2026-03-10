"""
股市交易系统模块 - 订单簿、交易撮合、价格发现
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict
import random
import math


class OrderType(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    order_id: int
    agent_id: int
    order_type: OrderType
    price: float
    quantity: int
    timestamp: int
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


@dataclass
class Trade:
    trade_id: int
    buy_order_id: int
    sell_order_id: int
    buyer_id: int
    seller_id: int
    price: float
    quantity: int
    timestamp: int


class OrderBook:
    def __init__(self):
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.trade_history: List[Trade] = []
        self.order_counter = 0
        self.trade_counter = 0
    
    def add_order(self, order: Order) -> Order:
        order.order_id = self.order_counter
        self.order_counter += 1
        
        if order.order_type == OrderType.BUY:
            self.buy_orders.append(order)
            self.buy_orders.sort(key=lambda x: (-x.price, x.timestamp))
        else:
            self.sell_orders.append(order)
            self.sell_orders.sort(key=lambda x: (x.price, x.timestamp))
        
        return order
    
    def cancel_order(self, order_id: int) -> bool:
        for order_list in [self.buy_orders, self.sell_orders]:
            for i, order in enumerate(order_list):
                if order.order_id == order_id and order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.CANCELLED
                    order_list.pop(i)
                    return True
        return False
    
    def get_best_bid(self) -> Optional[Order]:
        for order in self.buy_orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                return order
        return None
    
    def get_best_ask(self) -> Optional[Order]:
        for order in self.sell_orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                return order
        return None
    
    def get_spread(self) -> Tuple[Optional[float], Optional[float], float]:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        bid_price = best_bid.price if best_bid else None
        ask_price = best_ask.price if best_ask else None
        spread = (ask_price - bid_price) if bid_price and ask_price else float('inf')
        return bid_price, ask_price, spread
    
    def get_market_depth(self, levels: int = 5) -> Dict:
        bid_depth = defaultdict(int)
        ask_depth = defaultdict(int)
        
        for order in self.buy_orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                bid_depth[order.price] += order.remaining_quantity()
        
        for order in self.sell_orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                ask_depth[order.price] += order.remaining_quantity()
        
        top_bids = sorted(bid_depth.items(), key=lambda x: -x[0])[:levels]
        top_asks = sorted(ask_depth.items(), key=lambda x: x[0])[:levels]
        
        return {
            "bids": top_bids,
            "asks": top_asks
        }
    
    def match_orders(self, timestamp: int) -> List[Trade]:
        trades = []
        
        while True:
            best_bid = self.get_best_bid()
            best_ask = self.get_best_ask()
            
            if not best_bid or not best_ask:
                break
            
            if best_bid.price < best_ask.price:
                break
            
            trade_price = best_ask.price
            trade_quantity = min(
                best_bid.remaining_quantity(),
                best_ask.remaining_quantity()
            )
            
            trade = Trade(
                trade_id=self.trade_counter,
                buy_order_id=best_bid.order_id,
                sell_order_id=best_ask.order_id,
                buyer_id=best_bid.agent_id,
                seller_id=best_ask.agent_id,
                price=trade_price,
                quantity=trade_quantity,
                timestamp=timestamp
            )
            self.trade_counter += 1
            trades.append(trade)
            self.trade_history.append(trade)
            
            best_bid.filled_quantity += trade_quantity
            best_ask.filled_quantity += trade_quantity
            best_bid.filled_price = (
                (best_bid.filled_price * (best_bid.filled_quantity - trade_quantity) + 
                 trade_price * trade_quantity) / best_bid.filled_quantity
            )
            best_ask.filled_price = best_bid.filled_price
            
            if best_bid.remaining_quantity() == 0:
                best_bid.status = OrderStatus.FILLED
                self.buy_orders.remove(best_bid)
            else:
                best_bid.status = OrderStatus.PARTIAL
            
            if best_ask.remaining_quantity() == 0:
                best_ask.status = OrderStatus.FILLED
                self.sell_orders.remove(best_ask)
            else:
                best_ask.status = OrderStatus.PARTIAL
        
        return trades
    
    def get_agent_orders(self, agent_id: int) -> List[Order]:
        orders = []
        for order in self.buy_orders + self.sell_orders:
            if order.agent_id == agent_id:
                orders.append(order)
        return orders


class MarketMaker:
    def __init__(
        self,
        agent_id: int,
        base_spread: float = 0.02,
        min_quantity: int = 10,
        max_quantity: int = 100,
        inventory_limit: int = 500
    ):
        self.agent_id = agent_id
        self.base_spread = base_spread
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
        self.inventory_limit = inventory_limit
        self.inventory = 0
        self.total_volume = 0
    
    def calculate_quotes(self, mid_price: float, volatility: float) -> Tuple[Order, Order]:
        spread_adjustment = volatility * 0.5
        inventory_skew = self.inventory / self.inventory_limit if self.inventory_limit > 0 else 0
        
        bid_spread = self.base_spread + spread_adjustment - inventory_skew * 0.01
        ask_spread = self.base_spread + spread_adjustment + inventory_skew * 0.01
        
        bid_price = round(mid_price * (1 - bid_spread / 2), 2)
        ask_price = round(mid_price * (1 + ask_spread / 2), 2)
        
        if self.inventory > self.inventory_limit * 0.5:
            quantity = self.min_quantity
        else:
            quantity = random.randint(self.min_quantity, self.max_quantity)
        
        buy_order = Order(
            order_id=0,
            agent_id=self.agent_id,
            order_type=OrderType.BUY,
            price=bid_price,
            quantity=quantity,
            timestamp=0
        )
        
        sell_order = Order(
            order_id=0,
            agent_id=self.agent_id,
            order_type=OrderType.SELL,
            price=ask_price,
            quantity=quantity,
            timestamp=0
        )
        
        return buy_order, sell_order
    
    def update_inventory(self, quantity: int, is_buy: bool):
        if is_buy:
            self.inventory += quantity
        else:
            self.inventory -= quantity
        self.total_volume += quantity


class TradingRules:
    MIN_ORDER_QUANTITY = 1
    MAX_ORDER_QUANTITY = 1000
    MIN_PRICE_INCREMENT = 0.01
    PRICE_BAND_PERCENTAGE = 0.10
    TRADING_FEE_RATE = 0.001
    MIN_CAPITAL = 100.0
    
    @classmethod
    def validate_order(
        cls,
        price: float,
        quantity: int,
        reference_price: float,
        agent_capital: float,
        agent_holdings: int
    ) -> Tuple[bool, str]:
        if quantity < cls.MIN_ORDER_QUANTITY:
            return False, f"最小下单数量为 {cls.MIN_ORDER_QUANTITY}"
        
        if quantity > cls.MAX_ORDER_QUANTITY:
            return False, f"最大下单数量为 {cls.MAX_ORDER_QUANTITY}"
        
        if price <= 0:
            return False, "价格必须大于0"
        
        price_band_upper = reference_price * (1 + cls.PRICE_BAND_PERCENTAGE)
        price_band_lower = reference_price * (1 - cls.PRICE_BAND_PERCENTAGE)
        
        if price > price_band_upper or price < price_band_lower:
            return False, f"价格超出涨跌停限制 ({price_band_lower:.2f} - {price_band_upper:.2f})"
        
        required_capital = price * quantity * (1 + cls.TRADING_FEE_RATE)
        if required_capital > agent_capital:
            return False, f"资金不足，需要 {required_capital:.2f}"
        
        return True, "订单有效"
    
    @classmethod
    def calculate_fee(cls, value: float) -> float:
        return value * cls.TRADING_FEE_RATE
