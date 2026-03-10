"""
永不纳什小镇 - 简化版模拟系统
核心：A股交易规则，智能体自主决策
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import random

from .town_agent import TownAgent, create_town_agents
from .trading import OrderBook, Order, OrderType, Trade, TradingRules
from .market import AShareMarket, MarketPhase


@dataclass
class TownStats:
    total_trades: int = 0
    total_volume: int = 0


class NashTown:
    HOURS_PER_DAY = 24
    
    PRICE_LIMIT = 0.10
    
    CALL_AUCTION_OPEN = (9, 15)
    CALL_AUCTION_CLOSE = (9, 25)
    MORNING_TRADING_START = (9, 30)
    MORNING_TRADING_END = (11, 30)
    LUNCH_BREAK_START = (11, 30)
    LUNCH_BREAK_END = (13, 0)
    AFTERNOON_TRADING_START = (13, 0)
    AFTERNOON_TRADING_END = (15, 0)
    CALL_AUCTION_CLOSE_START = (14, 57)
    MARKET_CLOSE = (15, 0)
    
    def __init__(
        self,
        num_agents: int = 10,
        initial_capital: float = 10000.0,
        initial_price: float = 100.0,
        seed: Optional[int] = None,
        verbose: bool = True
    ):
        if seed is not None:
            random.seed(seed)
        
        self.agents = create_town_agents(num_agents, initial_capital)
        self.market = AShareMarket(initial_price, seed)
        self.order_book = OrderBook()
        
        self.current_hour = 9
        self.current_minute = 30
        self.current_day = 1
        
        self.verbose = verbose
        self.stats = TownStats()
        
        self.daily_logs: List[Dict] = []
        self.trade_log: List[Dict] = []
        
        self._tick_count = 0
        self._max_ticks_per_day = 6 * 60 + 30
        
        self._limit_up = initial_price * (1 + self.PRICE_LIMIT)
        self._limit_down = initial_price * (1 - self.PRICE_LIMIT)
    
    def _time_to_minutes(self, hour: int, minute: int) -> int:
        return hour * 60 + minute
    
    def get_market_phase(self) -> str:
        current = self._time_to_minutes(self.current_hour, self.current_minute)
        
        call_open = self._time_to_minutes(*self.CALL_AUCTION_OPEN)
        call_close = self._time_to_minutes(*self.CALL_AUCTION_CLOSE)
        morning_start = self._time_to_minutes(*self.MORNING_TRADING_START)
        morning_end = self._time_to_minutes(*self.MORNING_TRADING_END)
        lunch_start = self._time_to_minutes(*self.LUNCH_BREAK_START)
        lunch_end = self._time_to_minutes(*self.LUNCH_BREAK_END)
        afternoon_start = self._time_to_minutes(*self.AFTERNOON_TRADING_START)
        afternoon_end = self._time_to_minutes(*self.AFTERNOON_TRADING_END)
        close_start = self._time_to_minutes(*self.CALL_AUCTION_CLOSE_START)
        market_close = self._time_to_minutes(*self.MARKET_CLOSE)
        
        if current < call_open:
            return "pre_market"
        elif call_open <= current < call_close:
            return "call_auction_open"
        elif call_close <= current < morning_start:
            return "call_auction_match"
        elif morning_start <= current < morning_end:
            return "morning_continuous"
        elif lunch_start <= current < lunch_end:
            return "lunch_break"
        elif afternoon_start <= current < close_start:
            return "afternoon_continuous"
        elif close_start <= current < afternoon_end:
            return "call_auction_close"
        elif afternoon_end <= current < market_close:
            return "closing"
        else:
            return "closed"
    
    def is_trading_time(self) -> bool:
        phase = self.get_market_phase()
        return phase in ["call_auction_open", "call_auction_match", 
                        "morning_continuous", "afternoon_continuous",
                        "call_auction_close"]
    
    def is_lunch_break(self) -> bool:
        return self.get_market_phase() == "lunch_break"
    
    def simulate_tick(self) -> Dict:
        self._tick_count += 1
        
        if self._tick_count > self._max_ticks_per_day:
            return {"error": "max_ticks_exceeded"}
        
        phase = self.get_market_phase()
        
        tick_result = {
            "day": self.current_day,
            "time": f"{self.current_hour:02d}:{self.current_minute:02d}",
            "phase": phase,
            "trades": [],
            "price": self.market.state.current_price,
        }
        
        for agent in self.agents:
            agent.update_hour(self.current_hour)
        
        if self.is_trading_time():
            trades = self._run_trading_tick(phase)
            tick_result["trades"] = trades
            tick_result["price"] = self.market.state.current_price
        
        self._advance_time()
        
        if self.current_hour == 15 and self.current_minute == 0:
            self._end_day()
            tick_result["day_ended"] = True
        
        return tick_result
    
    def _run_trading_tick(self, phase: str) -> List[Dict]:
        timestamp = self._time_to_minutes(self.current_hour, self.current_minute)
        trades_executed = []
        
        awake_agents = [a for a in self.agents if not a.is_sleeping()]
        
        for agent in awake_agents:
            if not agent.can_trade():
                continue
            
            trade_prob = 0.1 if "call_auction" in phase else 0.05
            
            if random.random() < trade_prob:
                decision = self._get_agent_decision(agent, timestamp)
                
                if decision:
                    order = self._create_order(agent, decision, timestamp)
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
        
        if phase == "call_auction_match":
            trades = self.order_book.match_orders(timestamp)
        elif phase in ["morning_continuous", "afternoon_continuous"]:
            trades = self.order_book.match_orders(timestamp)
        elif phase == "call_auction_close":
            trades = self.order_book.match_orders(timestamp)
        else:
            trades = []
        
        for trade in trades:
            self._execute_trade(trade)
            trades_executed.append({
                "buyer": trade.buyer_id,
                "seller": trade.seller_id,
                "price": trade.price,
                "quantity": trade.quantity
            })
        
        if trades:
            self.market.tick(len(trades))
        
        return trades_executed
    
    def _get_agent_decision(self, agent: TownAgent, timestamp: int):
        from .agent_interface import TradingContext, MarketData, TechnicalIndicators
        
        market_summary = self.market.get_market_summary()
        technical = self.market.get_technical_analysis()
        
        context = TradingContext(
            market_data=MarketData(
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
            ),
            technical=TechnicalIndicators(
                rsi=technical["rsi"],
                macd=technical["macd"],
                signal_line=technical["signal_line"],
            ),
            agent_state=agent.get_state(),
            order_book_depth=self.order_book.get_market_depth(),
            timestamp=timestamp,
        )
        
        return agent.decide(context)
    
    def _create_order(self, agent: TownAgent, decision, timestamp: int) -> Optional[Order]:
        if decision.action == "none":
            return None
        
        current_price = self.market.state.current_price
        
        if self._limit_up and current_price >= self._limit_up:
            if decision.action == "buy":
                return None
        
        if self._limit_down and current_price <= self._limit_down:
            if decision.action == "sell":
                return None
        
        if decision.action == "buy":
            if decision.price is None or decision.quantity is None:
                return None
            
            price = decision.price
            
            if self._limit_up:
                price = min(price, self._limit_up)
            if self._limit_down:
                price = max(price, self._limit_down)
            
            quantity = decision.quantity
            
            max_qty = int(agent.capital / (price * (1 + TradingRules.TRADING_FEE_RATE)))
            quantity = min(quantity, max_qty)
            
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
            
            if self._limit_up:
                price = min(price, self._limit_up)
            if self._limit_down:
                price = max(price, self._limit_down)
            
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
        buyer = next((a for a in self.agents if a.agent_id == trade.buyer_id), None)
        seller = next((a for a in self.agents if a.agent_id == trade.seller_id), None)
        
        fee = TradingRules.calculate_fee(trade.price * trade.quantity)
        
        if buyer:
            buyer.update_position(True, trade.quantity, trade.price, fee)
        
        if seller:
            seller.update_position(False, trade.quantity, trade.price, fee)
        
        self.stats.total_trades += 1
        self.stats.total_volume += trade.quantity
        
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
    
    def _end_day(self):
        daily_log = {
            "day": self.current_day,
            "open": self.market.state.day_open,
            "high": self.market.state.day_high,
            "low": self.market.state.day_low,
            "close": self.market.state.current_price,
            "volume": self.stats.total_volume,
            "trades": self.stats.total_trades,
            "agents": [
                {
                    "name": a.name,
                    "capital": a.capital,
                    "position": a.position,
                    "total_value": a.total_value,
                }
                for a in self.agents
            ]
        }
        self.daily_logs.append(daily_log)
        
        if self.verbose:
            self._print_day_summary()
        
        self.current_day += 1
        self.market.new_day()
        self.stats = TownStats()
        self._tick_count = 0
        
        self._limit_up = self.market.state.day_open * (1 + self.PRICE_LIMIT)
        self._limit_down = self.market.state.day_open * (1 - self.PRICE_LIMIT)
        
        self.current_hour = 9
        self.current_minute = 30
    
    def _print_day_summary(self):
        print(f"\n{'='*60}")
        print(f"📊 第 {self.current_day} 天交易结束")
        print(f"{'='*60}")
        
        summary = self.market.get_market_summary()
        print(f"开盘: {summary.get('day_open', summary['price']):.2f} | "
              f"收盘: {summary['price']:.2f} | "
              f"涨跌: {summary['change_pct']:.2f}%")
        print(f"最高: {summary['day_high']:.2f} | "
              f"最低: {summary['day_low']:.2f} | "
              f"成交量: {self.stats.total_volume}")
        
        sorted_agents = sorted(self.agents, key=lambda a: a.total_value, reverse=True)
        print(f"\n🏆 财富榜 Top 5:")
        for i, agent in enumerate(sorted_agents[:5], 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            print(f"  {medal} {agent.name}: {agent.total_value:,.0f}元")
    
    def simulate_day(self) -> Dict:
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🏘️ 永不纳什小镇 - 第 {self.current_day} 天")
            print(f"{'='*60}")
            print(f"智能体数量: {len(self.agents)}")
        
        start_day = self.current_day
        ticks = 0
        max_ticks = self._max_ticks_per_day + 100
        
        while ticks < max_ticks:
            result = self.simulate_tick()
            ticks += 1
            
            if result.get("day_ended"):
                break
        
        return self.daily_logs[-1] if self.daily_logs else {}
    
    def simulate_days(self, num_days: int) -> List[Dict]:
        logs = []
        for _ in range(num_days):
            day_log = self.simulate_day()
            logs.append(day_log)
        return logs
    
    def get_market_overview(self) -> Dict:
        return {
            "day": self.current_day,
            "time": f"{self.current_hour:02d}:{self.current_minute:02d}",
            "phase": self.get_market_phase(),
            "price": self.market.state.current_price,
            "market": self.market.get_market_summary(),
            "agents": len(self.agents),
        }
    
    def get_available_actions(self, agent_id: str) -> List[str]:
        agent = next((a for a in self.agents if a.agent_id == agent_id), None)
        if not agent:
            return []
        
        actions = []
        
        if agent.is_sleeping():
            return ["sleep"]
        
        if self.is_trading_time():
            if agent.can_trade():
                actions.extend(["buy", "sell", "hold"])
        
        if self.is_lunch_break():
            actions.extend(["rest", "socialize"])
        
        actions.append("wait")
        
        return actions
