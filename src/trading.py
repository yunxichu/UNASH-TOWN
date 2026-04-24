"""Order book and A-share trading rules."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OrderType(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    order_id: int
    agent_id: str
    order_type: OrderType
    price: float
    quantity: int
    timestamp: int
    status: OrderStatus = OrderStatus.OPEN
    filled_quantity: int = 0

    @property
    def remaining(self) -> int:
        return self.quantity - self.filled_quantity


@dataclass
class Trade:
    trade_id: int
    buy_order_id: int
    sell_order_id: int
    buyer_id: str
    seller_id: str
    price: float
    quantity: int
    timestamp: int
    buyer_fee: float
    seller_fee: float
    stamp_duty: float


class TradingRules:
    MIN_LOT = 100
    MAX_ORDER_QUANTITY = 10000
    PRICE_LIMIT = 0.10
    COMMISSION_RATE = 0.0003
    STAMP_DUTY_RATE = 0.0005
    MIN_COMMISSION = 5.0
    TICK_SIZE = 0.01

    @classmethod
    def round_price(cls, price: float) -> float:
        return round(round(price / cls.TICK_SIZE) * cls.TICK_SIZE, 2)

    @classmethod
    def round_lot(cls, quantity: int) -> int:
        return max(0, int(quantity // cls.MIN_LOT) * cls.MIN_LOT)

    @classmethod
    def commission(cls, value: float) -> float:
        return max(cls.MIN_COMMISSION, value * cls.COMMISSION_RATE) if value > 0 else 0.0

    @classmethod
    def validate_order(
        cls,
        order_type: OrderType,
        price: float,
        quantity: int,
        reference_price: float,
        capital: float,
        available_position: int,
    ) -> Tuple[bool, str]:
        if quantity < cls.MIN_LOT or quantity % cls.MIN_LOT != 0:
            return False, f"quantity must be a multiple of {cls.MIN_LOT}"
        if quantity > cls.MAX_ORDER_QUANTITY:
            return False, "quantity exceeds max order size"
        if price <= 0:
            return False, "price must be positive"

        lower = reference_price * (1 - cls.PRICE_LIMIT)
        upper = reference_price * (1 + cls.PRICE_LIMIT)
        if price < lower or price > upper:
            return False, "price exceeds daily limit band"

        if order_type is OrderType.BUY:
            required = price * quantity + cls.commission(price * quantity)
            if required > capital:
                return False, "insufficient capital"
        elif quantity > available_position:
            return False, "insufficient T+1 available position"

        return True, "ok"


class OrderBook:
    def __init__(self) -> None:
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.trade_history: List[Trade] = []
        self._next_order_id = 1
        self._next_trade_id = 1

    def add_order(self, order: Order) -> Order:
        order.order_id = self._next_order_id
        self._next_order_id += 1

        if order.order_type is OrderType.BUY:
            self.buy_orders.append(order)
            self.buy_orders.sort(key=lambda item: (-item.price, item.timestamp, item.order_id))
        else:
            self.sell_orders.append(order)
            self.sell_orders.sort(key=lambda item: (item.price, item.timestamp, item.order_id))
        return order

    def match(self, timestamp: int) -> List[Trade]:
        trades: List[Trade] = []
        while self.buy_orders and self.sell_orders:
            bid = self.buy_orders[0]
            ask = self.sell_orders[0]
            if bid.price < ask.price:
                break

            quantity = min(bid.remaining, ask.remaining)
            price = TradingRules.round_price((bid.price + ask.price) / 2)
            value = price * quantity
            trade = Trade(
                trade_id=self._next_trade_id,
                buy_order_id=bid.order_id,
                sell_order_id=ask.order_id,
                buyer_id=bid.agent_id,
                seller_id=ask.agent_id,
                price=price,
                quantity=quantity,
                timestamp=timestamp,
                buyer_fee=TradingRules.commission(value),
                seller_fee=TradingRules.commission(value),
                stamp_duty=value * TradingRules.STAMP_DUTY_RATE,
            )
            self._next_trade_id += 1
            self.trade_history.append(trade)
            trades.append(trade)

            bid.filled_quantity += quantity
            ask.filled_quantity += quantity
            self._refresh_top_order(self.buy_orders)
            self._refresh_top_order(self.sell_orders)
        return trades

    @staticmethod
    def _refresh_top_order(orders: List[Order]) -> None:
        if not orders:
            return
        top = orders[0]
        if top.remaining <= 0:
            top.status = OrderStatus.FILLED
            orders.pop(0)
        else:
            top.status = OrderStatus.PARTIAL

    def spread(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        bid = self.buy_orders[0].price if self.buy_orders else None
        ask = self.sell_orders[0].price if self.sell_orders else None
        spread = ask - bid if bid is not None and ask is not None else None
        return bid, ask, spread

    def depth(self, levels: int = 5) -> Dict[str, List[Tuple[float, int]]]:
        def aggregate(orders: List[Order]) -> Dict[float, int]:
            result: Dict[float, int] = {}
            for order in orders:
                result[order.price] = result.get(order.price, 0) + order.remaining
            return result

        bids = sorted(aggregate(self.buy_orders).items(), key=lambda item: -item[0])[:levels]
        asks = sorted(aggregate(self.sell_orders).items(), key=lambda item: item[0])[:levels]
        return {"bids": bids, "asks": asks}

    def imbalance(self) -> float:
        bid_volume = sum(order.remaining for order in self.buy_orders)
        ask_volume = sum(order.remaining for order in self.sell_orders)
        total = bid_volume + ask_volume
        return (bid_volume - ask_volume) / total if total else 0.0

    def clear(self) -> None:
        self.buy_orders.clear()
        self.sell_orders.clear()
