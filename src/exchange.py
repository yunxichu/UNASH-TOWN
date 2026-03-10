"""
交易所小镇模块 - 股市交易模拟主系统
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import random

from .trader import TraderAgent, TraderType, create_traders
from .trading import OrderBook, Order, OrderType, Trade, TradingRules
from .market import StockMarket, MarketPhase, MarketEvent


class TradingSession(Enum):
    PRE_MARKET = "pre_market"
    OPENING = "opening"
    CONTINUOUS = "continuous"
    CLOSING = "closing"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


@dataclass
class SessionStats:
    trades: int = 0
    volume: int = 0
    turnover: float = 0.0
    buy_volume: int = 0
    sell_volume: int = 0
    avg_price: float = 0.0
    price_range: tuple = (0.0, 0.0)


class ExchangeTown:
    def __init__(
        self,
        num_traders: int = 10,
        initial_capital: float = 10000.0,
        initial_price: float = 100.0,
        seed: Optional[int] = None,
        verbose: bool = True
    ):
        if seed is not None:
            random.seed(seed)
        
        self.traders = create_traders(num_traders, initial_capital)
        self.market = StockMarket(initial_price, seed)
        self.order_book = OrderBook()
        
        self.current_hour = 9
        self.current_minute = 0
        self.current_day = 1
        
        self.verbose = verbose
        self.session_stats = SessionStats()
        
        self.daily_logs: List[Dict] = []
        self.trade_log: List[Dict] = []
    
    def get_session(self, hour: int, minute: int) -> TradingSession:
        if hour < 9:
            return TradingSession.PRE_MARKET
        elif hour == 9 and minute < 30:
            return TradingSession.OPENING
        elif hour == 9 and minute >= 30 or (9 < hour < 15):
            return TradingSession.CONTINUOUS
        elif hour == 15:
            return TradingSession.CLOSING
        elif 15 < hour < 18:
            return TradingSession.AFTER_HOURS
        else:
            return TradingSession.CLOSED
    
    def simulate_tick(self) -> Dict:
        session = self.get_session(self.current_hour, self.current_minute)
        
        tick_result = {
            "time": f"{self.current_hour:02d}:{self.current_minute:02d}",
            "session": session.value,
            "trades": [],
            "price_change": 0.0,
        }
        
        if session == TradingSession.CONTINUOUS:
            tick_result = self._run_continuous_trading(tick_result)
        elif session == TradingSession.OPENING:
            tick_result = self._run_opening_auction(tick_result)
        elif session == TradingSession.CLOSING:
            tick_result = self._run_closing_auction(tick_result)
        elif session == TradingSession.AFTER_HOURS:
            tick_result = self._run_after_hours(tick_result)
        
        self._advance_time()
        
        if self.current_hour == 0 and self.current_minute == 0:
            self._end_trading_day()
        
        return tick_result
    
    def _run_continuous_trading(self, tick_result: Dict) -> Dict:
        market_state = self.market.get_market_summary()
        technical = self.market.get_technical_analysis()
        timestamp = self.current_hour * 60 + self.current_minute
        
        for trader in self.traders:
            trader.update_position_value(market_state["price"])
            
            if random.random() < 0.3:
                order = trader.decide_order(
                    self.order_book,
                    market_state,
                    technical,
                    timestamp
                )
                
                if order:
                    valid, msg = TradingRules.validate_order(
                        order.price,
                        order.quantity,
                        market_state["price"],
                        trader.capital,
                        trader.position.quantity
                    )
                    
                    if valid:
                        self.order_book.add_order(order)
                        trader.pending_orders.append(order.order_id)
        
        trades = self.order_book.match_orders(timestamp)
        
        for trade in trades:
            self._execute_trade(trade)
            tick_result["trades"].append({
                "buyer": trade.buyer_id,
                "seller": trade.seller_id,
                "price": trade.price,
                "quantity": trade.quantity
            })
        
        self.market.tick(len(trades))
        
        new_price = self.market.state.current_price
        tick_result["price_change"] = new_price - market_state["price"]
        tick_result["market_state"] = self.market.get_market_summary()
        
        if self.verbose and trades:
            print(f"  [{tick_result['time']}] 成交 {len(trades)} 笔, "
                  f"价格: {new_price:.2f}, "
                  f"成交量: {sum(t.quantity for t in trades)}")
        
        return tick_result
    
    def _run_opening_auction(self, tick_result: Dict) -> Dict:
        market_state = self.market.get_market_summary()
        technical = self.market.get_technical_analysis()
        timestamp = self.current_hour * 60 + self.current_minute
        
        for trader in self.traders:
            if random.random() < 0.5:
                order = trader.decide_order(
                    self.order_book,
                    market_state,
                    technical,
                    timestamp
                )
                if order:
                    self.order_book.add_order(order)
        
        if self.current_minute == 29:
            trades = self.order_book.match_orders(timestamp)
            for trade in trades:
                self._execute_trade(trade)
            
            self.market.tick(len(trades))
            tick_result["trades"] = [{"price": t.price, "quantity": t.quantity} for t in trades]
            
            if self.verbose:
                print(f"  [开盘集合竞价] 成交 {len(trades)} 笔")
        
        return tick_result
    
    def _run_closing_auction(self, tick_result: Dict) -> Dict:
        market_state = self.market.get_market_summary()
        timestamp = self.current_hour * 60 + self.current_minute
        
        for trader in self.traders:
            if trader.position.quantity > 0 and random.random() < 0.3:
                price = market_state["price"]
                order = Order(
                    order_id=0,
                    agent_id=trader.id,
                    order_type=OrderType.SELL,
                    price=price * 0.99,
                    quantity=min(trader.position.quantity, 50),
                    timestamp=timestamp
                )
                self.order_book.add_order(order)
        
        trades = self.order_book.match_orders(timestamp)
        for trade in trades:
            self._execute_trade(trade)
        
        self.market.tick(len(trades))
        tick_result["trades"] = [{"price": t.price, "quantity": t.quantity} for t in trades]
        
        if self.verbose and trades:
            print(f"  [收盘集合竞价] 成交 {len(trades)} 笔")
        
        return tick_result
    
    def _run_after_hours(self, tick_result: Dict) -> Dict:
        for trader in self.traders:
            for order_id in trader.pending_orders[:]:
                if self.order_book.cancel_order(order_id):
                    trader.pending_orders.remove(order_id)
        
        if self.verbose and self.current_hour == 16 and self.current_minute == 0:
            print(f"  [盘后] 清理未成交订单")
        
        return tick_result
    
    def _execute_trade(self, trade: Trade):
        buyer = next((t for t in self.traders if t.id == trade.buyer_id), None)
        seller = next((t for t in self.traders if t.id == trade.seller_id), None)
        
        if buyer:
            fee = TradingRules.calculate_fee(trade.price * trade.quantity)
            buyer.execute_trade(True, trade.quantity, trade.price, fee)
        
        if seller:
            fee = TradingRules.calculate_fee(trade.price * trade.quantity)
            seller.execute_trade(False, trade.quantity, trade.price, fee)
        
        self.session_stats.trades += 1
        self.session_stats.volume += trade.quantity
        self.session_stats.turnover += trade.price * trade.quantity
        
        self.trade_log.append({
            "day": self.current_day,
            "time": f"{self.current_hour:02d}:{self.current_minute:02d}",
            "buyer": trade.buyer_id,
            "seller": trade.seller_id,
            "price": trade.price,
            "quantity": trade.quantity,
        })
    
    def _advance_time(self):
        self.current_minute += 1
        if self.current_minute >= 60:
            self.current_minute = 0
            self.current_hour += 1
            
            if self.current_hour >= 24:
                self.current_hour = 0
    
    def _end_trading_day(self):
        daily_summary = {
            "day": self.current_day,
            "open": self.market.state.day_open,
            "high": self.market.state.day_high,
            "low": self.market.state.day_low,
            "close": self.market.state.current_price,
            "volume": self.session_stats.volume,
            "turnover": self.session_stats.turnover,
            "trades": self.session_stats.trades,
            "trader_status": [t.get_status() for t in self.traders],
        }
        self.daily_logs.append(daily_summary)
        
        if self.verbose:
            self._print_daily_summary()
        
        self.current_day += 1
        self.market.new_day()
        self.session_stats = SessionStats()
    
    def _print_daily_summary(self):
        print(f"\n{'='*60}")
        print(f"第 {self.current_day} 天交易结束")
        print(f"{'='*60}")
        
        summary = self.market.get_market_summary()
        print(f"开盘: {summary['price'] + summary['change']:.2f} | "
              f"收盘: {summary['price']:.2f} | "
              f"涨跌: {summary['change_pct']:.2f}%")
        print(f"最高: {summary['day_high']:.2f} | "
              f"最低: {summary['day_low']:.2f} | "
              f"成交量: {summary['volume']}")
        print(f"市场状态: {summary['phase']} | RSI: {summary['rsi']:.1f}")
        
        sorted_traders = sorted(self.traders, key=lambda t: t.total_value, reverse=True)
        
        print(f"\n交易者排行榜:")
        print("-" * 60)
        for i, trader in enumerate(sorted_traders, 1):
            status = trader.get_status()
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            print(f"  {medal} {i}. {status['name']} ({status['type']}): "
                  f"总资产 {status['total_value']:.2f} | 收益率 {status['return_rate']}")
    
    def simulate_day(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"第 {self.current_day} 天交易开始")
        print(f"{'='*60}")
        
        while not (self.current_hour == 0 and self.current_minute == 0 and self.daily_logs):
            self.simulate_tick()
        
        return self.daily_logs[-1] if self.daily_logs else {}
    
    def simulate_days(self, num_days: int) -> List[Dict]:
        logs = []
        for _ in range(num_days):
            day_log = self.simulate_day()
            logs.append(day_log)
        return logs
    
    def get_leaderboard(self) -> List[Dict]:
        return sorted(
            [t.get_status() for t in self.traders],
            key=lambda x: float(x["total_value"]),
            reverse=True
        )
    
    def get_market_overview(self) -> Dict:
        return {
            "market": self.market.get_market_summary(),
            "technical": self.market.get_technical_analysis(),
            "order_book": self.order_book.get_market_depth(),
            "spread": self.order_book.get_spread(),
        }
