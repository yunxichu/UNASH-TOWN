"""
永不纳什小镇 - 完整模拟系统
包含睡眠、社交、交易的综合小镇生活
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random

from .town_agent import TownAgent, create_town_agents
from .life_system import SocialEngine, ActivityType, MoodType
from .trading import OrderBook, Order, OrderType, Trade, TradingRules
from .market import StockMarket


@dataclass
class TownStats:
    total_conversations: int = 0
    total_friendships: int = 0
    total_trades: int = 0


class NashTown:
    HOURS_PER_DAY = 24
    
    TRADING_MORNING_START = 9
    TRADING_MORNING_END = 11
    LUNCH_BREAK_START = 11
    LUNCH_BREAK_END = 13
    TRADING_AFTERNOON_START = 13
    TRADING_AFTERNOON_END = 15
    
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
        self.market = StockMarket(initial_price, seed)
        self.order_book = OrderBook()
        self.social_engine = SocialEngine()
        
        self.current_hour = 0
        self.current_day = 1
        self.total_hours_simulated = 0
        
        self.verbose = verbose
        self.stats = TownStats()
        
        self.daily_logs: List[Dict] = []
    
    def get_time_phase(self, hour: int) -> str:
        phases = {
            (0, 6): "深夜",
            (6, 9): "早晨",
            (9, 12): "上午",
            (12, 14): "中午",
            (14, 18): "下午",
            (18, 22): "傍晚",
            (22, 24): "夜晚",
        }
        for (start, end), phase in phases.items():
            if start <= hour < end:
                return phase
        return "深夜"
    
    def is_trading_hour(self, hour: int) -> bool:
        morning_session = self.TRADING_MORNING_START <= hour < self.TRADING_MORNING_END
        afternoon_session = self.TRADING_AFTERNOON_START <= hour < self.TRADING_AFTERNOON_END
        return morning_session or afternoon_session
    
    def is_lunch_break(self, hour: int) -> bool:
        return self.LUNCH_BREAK_START <= hour < self.LUNCH_BREAK_END
    
    def simulate_hour(self) -> Dict:
        phase = self.get_time_phase(self.current_hour)
        is_trading = self.is_trading_hour(self.current_hour)
        is_lunch = self.is_lunch_break(self.current_hour)
        
        hour_result = {
            "day": self.current_day,
            "hour": self.current_hour,
            "phase": phase,
            "is_trading_hour": is_trading,
            "is_lunch_break": is_lunch,
            "sleeping": [],
            "socializing": [],
            "trading": [],
        }
        
        if self.verbose:
            if is_lunch:
                print(f"\n--- 第{self.current_day}天 {self.current_hour:02d}:00 (午间休市) ---")
            else:
                print(f"\n--- 第{self.current_day}天 {self.current_hour:02d}:00 ({phase}) ---")
        
        for agent in self.agents:
            agent.update_hour(self.current_hour)
            
            if agent.is_sleeping():
                hour_result["sleeping"].append(agent.name)
            elif self.current_hour == agent.wake_time:
                if self.verbose:
                    status = agent.get_status()
                    print(f"  ⏰ {agent.name} 醒来了 (精力:{status['energy']:.0f})")
        
        awake_agents = [a for a in self.agents if not a.is_sleeping()]
        
        for agent in awake_agents:
            if agent.energy.current_energy < 20:
                agent.rest()
                continue
            
            if is_trading and random.random() < 0.3:
                agent._current_activity = ActivityType.TRADING
                agent.go_to("交易所")
                hour_result["trading"].append(agent.name)
            
            elif is_lunch and random.random() < 0.4:
                location = random.choice(["茶馆", "餐厅", "休息室"])
                agent.go_to(location)
                agent.rest()
                if self.verbose and random.random() < 0.3:
                    print(f"  🍜 {agent.name} 在{location}休息用餐")
            
            elif random.random() < 0.2:
                other_agents = [a for a in awake_agents 
                              if a.agent_id != agent.agent_id 
                              and a.can_socialize()]
                
                if other_agents:
                    other = random.choice(other_agents)
                    result = agent.socialize_with(other, self.social_engine)
                    
                    if result["success"]:
                        location = random.choice(["广场", "茶馆", "公园"])
                        agent.go_to(location)
                        other.go_to(location)
                        
                        hour_result["socializing"].append(f"{agent.name} & {other.name}")
                        self.stats.total_conversations += 1
                        
                        if self.verbose:
                            print(f"  💬 {agent.name} 和 {other.name} 在{location}聊天")
                            print(f"     \"{result['greeting']}\"")
        
        if is_trading:
            trades = self._run_trading_session()
            if trades and self.verbose:
                print(f"  📈 交易: 成交 {len(trades)} 笔")
        
        self._advance_time()
        self.total_hours_simulated += 1
        
        return hour_result
    
    def _run_trading_session(self) -> List:
        timestamp = self.current_hour * 60
        trades_executed = []
        
        for agent in self.agents:
            if agent.is_sleeping() or not agent.can_trade():
                continue
            
            if random.random() < 0.15:
                from .agent_interface import TradingContext, MarketData, TechnicalIndicators
                
                market_summary = self.market.get_market_summary()
                technical = self.market.get_technical_analysis()
                
                context = TradingContext(
                    market_data=MarketData(
                        price=market_summary["price"],
                        volume=market_summary["volume"],
                        timestamp=timestamp,
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
                
                decision = agent.decide(context)
                
                if decision.action == "buy" and decision.price and decision.quantity:
                    order = Order(
                        order_id=0,
                        agent_id=agent.agent_id,
                        order_type=OrderType.BUY,
                        price=decision.price,
                        quantity=decision.quantity,
                        timestamp=timestamp
                    )
                    self.order_book.add_order(order)
                
                elif decision.action == "sell" and decision.price and decision.quantity:
                    order = Order(
                        order_id=0,
                        agent_id=agent.agent_id,
                        order_type=OrderType.SELL,
                        price=decision.price,
                        quantity=decision.quantity,
                        timestamp=timestamp
                    )
                    self.order_book.add_order(order)
        
        trades = self.order_book.match_orders(timestamp)
        
        for trade in trades:
            buyer = next((a for a in self.agents if a.agent_id == trade.buyer_id), None)
            seller = next((a for a in self.agents if a.agent_id == trade.seller_id), None)
            
            fee = TradingRules.calculate_fee(trade.price * trade.quantity)
            
            if buyer:
                buyer.update_position(True, trade.quantity, trade.price, fee)
            
            if seller:
                seller.update_position(False, trade.quantity, trade.price, fee)
            
            self.stats.total_trades += 1
            trades_executed.append(trade)
        
        self.market.tick(len(trades))
        return trades_executed
    
    def _advance_time(self):
        self.current_hour += 1
        if self.current_hour >= self.HOURS_PER_DAY:
            self.current_hour = 0
            self.current_day += 1
    
    def simulate_day(self) -> Dict:
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🏘️ 永不纳什小镇 - 第 {self.current_day} 天")
            print(f"{'='*60}")
            
            print(f"\n👥 居民:")
            for agent in self.agents[:3]:
                status = agent.get_status()
                print(f"  {status['name']}: 睡眠 {agent.bedtime}:00-{agent.wake_time}:00")
        
        start_day = self.current_day
        hours_this_day = 0
        
        while hours_this_day < self.HOURS_PER_DAY:
            self.simulate_hour()
            hours_this_day += 1
        
        self._record_daily_log()
        
        if self.verbose:
            self._print_day_summary()
        
        return self.daily_logs[-1] if self.daily_logs else {}
    
    def _record_daily_log(self):
        total_friends = sum(len(a.social.friends) for a in self.agents) // 2
        self.stats.total_friendships = total_friends
        
        daily_log = {
            "day": self.current_day - 1,
            "stats": {
                "conversations": self.stats.total_conversations,
                "friendships": self.stats.total_friendships,
                "trades": self.stats.total_trades,
            },
            "agent_status": [a.get_status() for a in self.agents],
            "market": self.market.get_market_summary(),
        }
        self.daily_logs.append(daily_log)
        self.market.new_day()
    
    def _print_day_summary(self):
        print(f"\n{'='*60}")
        print(f"📊 第 {self.current_day - 1} 天结束")
        print(f"{'='*60}")
        print(f"  💬 对话: {self.stats.total_conversations} 次")
        print(f"  🤝 友谊: {self.stats.total_friendships} 对")
        print(f"  📈 交易: {self.stats.total_trades} 笔")
        
        sorted_agents = sorted(self.agents, key=lambda a: a.total_value, reverse=True)
        print(f"\n🏆 财富榜:")
        for i, agent in enumerate(sorted_agents[:3], 1):
            status = agent.get_status()
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
            print(f"  {medal} {status['name']}: {status['total_value']:,.0f}元 | 精力:{status['energy']:.0f}")
    
    def simulate_days(self, num_days: int) -> List[Dict]:
        logs = []
        for day in range(num_days):
            day_log = self.simulate_day()
            logs.append(day_log)
        return logs
    
    def get_town_overview(self) -> Dict:
        return {
            "day": self.current_day,
            "hour": self.current_hour,
            "population": len(self.agents),
            "sleeping": sum(1 for a in self.agents if a.is_sleeping()),
            "stats": {
                "conversations": self.stats.total_conversations,
                "friendships": self.stats.total_friendships,
                "trades": self.stats.total_trades,
            }
        }
