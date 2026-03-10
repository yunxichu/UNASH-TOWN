"""
UNASH-TOWN: 可扩展多智能体股市交易系统
主程序入口
"""
import argparse
import json
import random
import time
import threading
from typing import Dict, Optional

from src.agent_interface import (
    TradingContext, TradingDecision, AgentStatus
)
from src.agent_manager import AgentManager
from src.api_server import APIServer, APIConfig
from src.scalable_exchange import ScalableExchange
from src.trader import TraderType, TRADER_PROFILES


def create_builtin_strategy(trader_type: TraderType):
    def strategy(context: TradingContext) -> TradingDecision:
        market = context.market_data
        technical = context.technical
        state = context.agent_state
        
        if trader_type == TraderType.VALUE_INVESTOR:
            fair_value = market.price * 1.05
            if market.price < fair_value * 0.95:
                return TradingDecision.buy(
                    price=market.price * 0.99,
                    quantity=int(state.capital * 0.2 / market.price),
                    reasoning="Undervalued"
                )
            elif market.price > fair_value * 1.05 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price * 1.01,
                    quantity=min(state.position, 50),
                    reasoning="Overvalued"
                )
        
        elif trader_type == TraderType.MOMENTUM_TRADER:
            if technical.momentum > 0.005:
                return TradingDecision.buy(
                    price=market.price * 1.01,
                    quantity=int(state.capital * 0.15 / market.price),
                    reasoning="Momentum positive"
                )
            elif technical.momentum < -0.005 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price * 0.99,
                    quantity=min(state.position, 30),
                    reasoning="Momentum negative"
                )
        
        elif trader_type == TraderType.MEAN_REVERSION:
            if technical.rsi < 30:
                return TradingDecision.buy(
                    price=market.price * 0.98,
                    quantity=int(state.capital * 0.12 / market.price),
                    reasoning="RSI oversold"
                )
            elif technical.rsi > 70 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price * 1.02,
                    quantity=min(state.position, 40),
                    reasoning="RSI overbought"
                )
        
        elif trader_type == TraderType.NOISE_TRADER:
            if random.random() < 0.3:
                if random.random() < 0.5:
                    return TradingDecision.buy(
                        price=market.price * random.uniform(0.95, 1.0),
                        quantity=random.randint(1, 20),
                        reasoning="Random buy"
                    )
                else:
                    return TradingDecision.sell(
                        price=market.price * random.uniform(1.0, 1.05),
                        quantity=random.randint(1, 20),
                        reasoning="Random sell"
                    )
        
        elif trader_type == TraderType.TECHNICAL_ANALYST:
            signals = 0
            if technical.rsi < 40:
                signals += 1
            elif technical.rsi > 60:
                signals -= 1
            if technical.macd > technical.signal_line:
                signals += 1
            else:
                signals -= 1
            if technical.trend_strength > 0.01:
                signals += 1
            elif technical.trend_strength < -0.01:
                signals -= 1
            
            if signals >= 2:
                return TradingDecision.buy(
                    price=market.price * 1.0,
                    quantity=int(state.capital * 0.18 / market.price),
                    reasoning="Technical bullish"
                )
            elif signals <= -2 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price * 1.0,
                    quantity=min(state.position, 30),
                    reasoning="Technical bearish"
                )
        
        elif trader_type == TraderType.CONTRARIAN:
            if market.phase == "bear" and technical.rsi < 35:
                return TradingDecision.buy(
                    price=market.price * 0.97,
                    quantity=int(state.capital * 0.15 / market.price),
                    reasoning="Contrarian buy in bear market"
                )
            elif market.phase == "bull" and technical.rsi > 65 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price * 1.03,
                    quantity=min(state.position, 40),
                    reasoning="Contrarian sell in bull market"
                )
        
        elif trader_type == TraderType.SENTIMENT_TRADER:
            if market.event in ["earnings_beat", "merger_announcement"]:
                return TradingDecision.buy(
                    price=market.price * 1.02,
                    quantity=int(state.capital * 0.15 / market.price),
                    reasoning="Positive event"
                )
            elif market.event in ["earnings_miss", "regulatory_news"]:
                return TradingDecision.sell(
                    price=market.price * 0.98,
                    quantity=min(state.position, 30),
                    reasoning="Negative event"
                )
        
        elif trader_type == TraderType.ALGORITHMIC:
            score = 0
            if technical.rsi < 30:
                score += 2
            elif technical.rsi > 70:
                score -= 2
            if technical.momentum > 0.003:
                score += 1
            elif technical.momentum < -0.003:
                score -= 1
            
            if score >= 2:
                return TradingDecision.buy(
                    price=market.price,
                    quantity=int(state.capital * 0.12 / market.price),
                    reasoning="Algo buy signal"
                )
            elif score <= -2 and state.position > 0:
                return TradingDecision.sell(
                    price=market.price,
                    quantity=min(state.position, 25),
                    reasoning="Algo sell signal"
                )
        
        return TradingDecision.no_action()
    
    return strategy


def main():
    parser = argparse.ArgumentParser(description="UNASH-TOWN 可扩展多智能体股市交易系统")
    parser.add_argument("--agents", type=int, default=10, help="初始智能体数量")
    parser.add_argument("--days", type=int, default=3, help="模拟天数")
    parser.add_argument("--capital", type=float, default=10000.0, help="初始资金")
    parser.add_argument("--price", type=float, default=100.0, help="初始股价")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--api", action="store_true", help="启动API服务")
    parser.add_argument("--port", type=int, default=8080, help="API服务端口")
    parser.add_argument("--api-key", type=str, default=None, help="API密钥")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    print("=" * 60)
    print("  UNASH-TOWN: 可扩展多智能体股市交易系统")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  初始智能体: {args.agents}")
    print(f"  模拟天数: {args.days}")
    print(f"  初始资金: {args.capital:,.2f}")
    print(f"  初始股价: {args.price:.2f}")
    print(f"  API服务: {'启用' if args.api else '禁用'}")
    if args.api:
        print(f"  API端口: {args.port}")
    print()
    
    agent_manager = AgentManager(max_agents=1000)
    
    exchange = ScalableExchange(
        agent_manager=agent_manager,
        initial_price=args.price,
        seed=args.seed,
        verbose=not args.quiet
    )
    
    api_server = None
    if args.api:
        api_config = APIConfig(port=args.port, api_key=args.api_key)
        api_server = APIServer(agent_manager, api_config, exchange)
        api_server.start()
        print(f"API服务已启动: {api_server.url}")
        print("\nAPI端点:")
        print("  GET  /api/health           - 健康检查")
        print("  GET  /api/agents           - 列出所有智能体")
        print("  POST /api/agents/register  - 注册新智能体")
        print("  POST /api/agents/unregister- 注销智能体")
        print("  GET  /api/market           - 市场状态")
        print("  GET  /api/leaderboard      - 排行榜")
        print()
    
    print("注册内置智能体...")
    trader_types = list(TraderType)
    names = [
        "Warren", "George", "Jesse", "Jim", "Ray",
        "Paul", "John", "Steve", "Michael", "David"
    ]
    
    for i in range(args.agents):
        trader_type = trader_types[i % len(trader_types)]
        name = f"{names[i % len(names)]}_{i}"
        strategy = create_builtin_strategy(trader_type)
        
        agent_manager.create_local_agent(
            name=name,
            strategy=strategy,
            initial_capital=args.capital,
            capabilities=[trader_type.value],
            metadata={"trader_type": trader_type.value}
        )
    
    print(f"已注册 {agent_manager.agent_count} 个智能体\n")
    
    print("开始模拟...")
    print("=" * 60)
    
    logs = exchange.simulate_days(args.days)
    
    print("\n" + "=" * 60)
    print("模拟结束!")
    print("=" * 60)
    
    leaderboard = agent_manager.get_leaderboard()
    
    print("\n最终排行榜:")
    print("-" * 60)
    for i, entry in enumerate(leaderboard[:10], 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"  {medal} {i}. {entry['name']} ({entry['agent_type']}): "
              f"总资产 {entry['total_value']:,.2f} | 收益率 {entry['return_rate']*100:.2f}%")
    
    overview = exchange.get_market_overview()
    print("\n市场概况:")
    print("-" * 60)
    market = overview["market"]
    print(f"  最终价格: {market['price']:.2f}")
    print(f"  涨跌幅: {market['change_pct']:.2f}%")
    print(f"  市场状态: {market['phase']}")
    print(f"  智能体总数: {overview['agents']['total']}")
    
    if args.output:
        output_data = {
            "config": {
                "initial_agents": args.agents,
                "num_days": args.days,
                "initial_capital": args.capital,
                "initial_price": args.price,
                "seed": args.seed,
            },
            "final_leaderboard": leaderboard,
            "market_summary": market,
            "agent_stats": agent_manager.get_all_stats(),
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {args.output}")
    
    if api_server:
        print("\nAPI服务持续运行中，按 Ctrl+C 停止...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止API服务...")
            api_server.stop()
            print("API服务已停止")
    
    return exchange


if __name__ == "__main__":
    main()
