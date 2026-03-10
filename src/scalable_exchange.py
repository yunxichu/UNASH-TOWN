"""
可扩展交易所模块 - 支持动态智能体的股市交易系统
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import random
import time

from .agent_interface import (
    BaseAgent, TradingContext, TradingDecision,
    MarketData, TechnicalIndicators, AgentState
)
from .agent_manager import AgentManager
from .trading import OrderBook, Order, OrderType, Trade, TradingRules
from .market import AShareMarket, MarketPhase, MarketEvent


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


class ScalableExchange:
    def __init__(
        self,
        agent_manager: AgentManager,
        initial_price: float = 100.0,
        seed: Optional[int] = None,
        verbose: bool = True
    ):
        self.agent_manager = agent_manager
        self.market = AShareMarket(initial_price, seed)
        self.order_book = OrderBook()
        
        self.current_hour = 9
        self.current_minute = 0
        self.current_day = 1
        
        self.verbose = verbose
        self.session_stats = SessionStats()
        
        self.daily_logs: List[Dict] = []
        self.trade_log: List[Dict] = []
        self._running = False
    
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
    
    def _build_trading_context(self, agent: BaseAgent, timestamp: int) -> TradingContext:
        market_summary = self.market.get_market_summary()
        technical = self.market.get_technical_analysis()
        depth = self.order_book.get_market_depth()
        
        market_data = MarketData(
            price=market_summary["price"],
            volume=market_summary["volume"],
            timestamp=timestamp,
            bid=self.order_book.get_spread()[0],
            ask=self.order_book.get_spread()[1],
            high=market_summary["day_high"],
            low=market_summary["day_low"],
            open_price=self.market.state.day_open,
            phase=market_summary["phase"],
            event=market_summary["event"],
        )
        
        tech_indicators = TechnicalIndicators(
            rsi=technical["rsi"],
            macd=technical["macd"],
            signal_line=technical["signal_line"],
            momentum=technical["momentum"],
            trend_strength=technical["trend_strength"],
            bollinger_upper=technical["bollinger_upper"],
            bollinger_middle=technical["bollinger_middle"],
            bollinger_lower=technical["bollinger_lower"],
        )
        
        agent_state = agent.get_state()
        
        return TradingContext(
            market_data=market_data,
            technical=tech_indicators,
            agent_state=agent_state,
            order_book_depth=depth,
            timestamp=timestamp,
        )
    
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
        timestamp = self.current_hour * 60 + self.current_minute
        
        agents = self.agent_manager.get_active_agents()
        
        for agent in agents:
            agent.update_price(self.market.state.current_price)
            
            if random.random() < 0.3:
                try:
                    context = self._build_trading_context(agent, timestamp)
                    decision = agent.decide(context)
                    
                    self.agent_manager.record_decision(agent.agent_id)
                    
                    order = self._decision_to_order(agent, decision, timestamp)
                    if order:
                        valid, msg = TradingRules.validate_order(
                            order.price,
                            order.quantity,
                            self.market.state.current_price,
                            agent.capital,
                            agent.position
                        )
                        
                        if valid:
                            self.order_book.add_order(order)
                
                except Exception as e:
                    self.agent_manager.record_error(agent.agent_id, str(e))
        
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
        tick_result["price_change"] = new_price - tick_result.get("market_state", {}).get("price", new_price)
        tick_result["market_state"] = self.market.get_market_summary()
        
        if self.verbose and trades:
            print(f"  [{tick_result['time']}] 成交 {len(trades)} 笔, "
                  f"价格: {new_price:.2f}, "
                  f"成交量: {sum(t.quantity for t in trades)}")
        
        return tick_result
    
    def _run_opening_auction(self, tick_result: Dict) -> Dict:
        timestamp = self.current_hour * 60 + self.current_minute
        
        agents = self.agent_manager.get_active_agents()
        
        for agent in agents:
            if random.random() < 0.5:
                try:
                    context = self._build_trading_context(agent, timestamp)
                    decision = agent.decide(context)
                    order = self._decision_to_order(agent, decision, timestamp)
                    if order:
                        self.order_book.add_order(order)
                except Exception:
                    pass
        
        if self.current_minute == 29:
            trades = self.order_book.match_orders(timestamp)
            for trade in trades:
                self._execute_trade(trade)
            
            self.market.tick(len(trades))
            
            if self.verbose:
                print(f"  [开盘集合竞价] 成交 {len(trades)} 笔")
        
        return tick_result
    
    def _run_closing_auction(self, tick_result: Dict) -> Dict:
        timestamp = self.current_hour * 60 + self.current_minute
        current_price = self.market.state.current_price
        
        agents = self.agent_manager.get_active_agents()
        
        for agent in agents:
            if agent.position > 0 and random.random() < 0.3:
                order = Order(
                    order_id=0,
                    agent_id=agent.agent_id,
                    order_type=OrderType.SELL,
                    price=current_price * 0.99,
                    quantity=min(agent.position, 50),
                    timestamp=timestamp
                )
                self.order_book.add_order(order)
        
        trades = self.order_book.match_orders(timestamp)
        for trade in trades:
            self._execute_trade(trade)
        
        self.market.tick(len(trades))
        
        if self.verbose and trades:
            print(f"  [收盘集合竞价] 成交 {len(trades)} 笔")
        
        return tick_result
    
    def _run_after_hours(self, tick_result: Dict) -> Dict:
        agents = self.agent_manager.get_all_agents()
        
        for agent in agents:
            for order in self.order_book.get_agent_orders(agent.agent_id):
                self.order_book.cancel_order(order.order_id)
        
        if self.verbose and self.current_hour == 16 and self.current_minute == 0:
            print(f"  [盘后] 清理未成交订单")
        
        return tick_result
    
    def _decision_to_order(self, agent: BaseAgent, decision: TradingDecision, timestamp: int) -> Optional[Order]:
        if decision.action == "none":
            return None
        
        if decision.action == "buy":
            if decision.price is None or decision.quantity is None:
                return None
            
            price = decision.price
            quantity = decision.quantity
            
            if agent.capital < price * quantity * (1 + TradingRules.TRADING_FEE_RATE):
                quantity = int(agent.capital / (price * (1 + TradingRules.TRADING_FEE_RATE)))
            
            if quantity <= 0:
                return None
            
            return Order(
                order_id=0,
                agent_id=agent.agent_id,
                order_type=OrderType.BUY,
                price=price,
                quantity=quantity,
                timestamp=timestamp
            )
        
        elif decision.action == "sell":
            if agent.position <= 0:
                return None
            
            price = decision.price or self.market.state.current_price
            quantity = decision.quantity or agent.position
            quantity = min(quantity, agent.position)
            
            if quantity <= 0:
                return None
            
            return Order(
                order_id=0,
                agent_id=agent.agent_id,
                order_type=OrderType.SELL,
                price=price,
                quantity=quantity,
                timestamp=timestamp
            )
        
        return None
    
    def _execute_trade(self, trade: Trade):
        buyer = self.agent_manager.get_agent(str(trade.buyer_id))
        seller = self.agent_manager.get_agent(str(trade.seller_id))
        
        fee = TradingRules.calculate_fee(trade.price * trade.quantity)
        
        if buyer:
            buyer.update_position(True, trade.quantity, trade.price, fee)
            buyer.on_trade_executed({
                "type": "buy",
                "price": trade.price,
                "quantity": trade.quantity,
                "fee": fee,
            })
            self.agent_manager.record_trade(buyer.agent_id)
        
        if seller:
            seller.update_position(False, trade.quantity, trade.price, fee)
            seller.on_trade_executed({
                "type": "sell",
                "price": trade.price,
                "quantity": trade.quantity,
                "fee": fee,
            })
            self.agent_manager.record_trade(seller.agent_id)
        
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
            "leaderboard": self.agent_manager.get_leaderboard(),
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
        print(f"活跃智能体: {self.agent_manager.active_count}/{self.agent_manager.agent_count}")
        
        leaderboard = self.agent_manager.get_leaderboard()[:5]
        print(f"\n交易者排行榜 Top 5:")
        print("-" * 60)
        for i, entry in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            print(f"  {medal} {i}. {entry['name']} ({entry['agent_type']}): "
                  f"总资产 {entry['total_value']:,.2f} | 收益率 {entry['return_rate']*100:.2f}%")
    
    def simulate_day(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"第 {self.current_day} 天交易开始")
        print(f"当前智能体数量: {self.agent_manager.agent_count}")
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
    
    def get_market_overview(self) -> Dict:
        return {
            "market": self.market.get_market_summary(),
            "technical": self.market.get_technical_analysis(),
            "order_book": self.order_book.get_market_depth(),
            "spread": self.order_book.get_spread(),
            "agents": {
                "total": self.agent_manager.agent_count,
                "active": self.agent_manager.active_count,
            }
        }
    
    def start(self):
        self._running = True
    
    def stop(self):
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running
