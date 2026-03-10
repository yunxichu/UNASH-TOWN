"""
UNASH-TOWN永不纳什小镇 - 多智能体生活博弈模拟小镇
主程序入口
"""
import argparse
import json
import random
import time

from src.nash_town import NashTown


def main():
    parser = argparse.ArgumentParser(description="永不纳什小镇 - 多智能体生活博弈模拟")
    parser.add_argument("--agents", type=int, default=10, help="居民数量")
    parser.add_argument("--days", type=int, default=3, help="模拟天数")
    parser.add_argument("--capital", type=float, default=10000.0, help="初始资金")
    parser.add_argument("--price", type=float, default=100.0, help="初始股价")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    print("=" * 60)
    print("  🏘️ 永不纳什小镇 - 多智能体生活博弈模拟系统")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  居民数量: {args.agents}")
    print(f"  模拟天数: {args.days}")
    print(f"  初始资金: {args.capital:,.2f}元")
    print(f"  初始股价: {args.price:.2f}元")
    print()
    
    town = NashTown(
        num_agents=args.agents,
        initial_capital=args.capital,
        initial_price=args.price,
        seed=args.seed,
        verbose=not args.quiet
    )
    
    print("居民介绍:")
    print("-" * 60)
    for agent in town.agents[:5]:
        status = agent.get_status()
        print(f"  {status['name']}: 睡眠 {agent.bedtime}:00-{agent.wake_time}:00")
        print(f"    兴趣: {', '.join(agent.social.interests)}")
        print(f"    性格: 外向{agent.social.personality_traits['extraversion']:.0%}, "
              f"友善{agent.social.personality_traits['agreeableness']:.0%}")
    
    print(f"\n开始模拟...")
    print("=" * 60)
    
    logs = town.simulate_days(args.days)
    
    print("\n" + "=" * 60)
    print("模拟结束!")
    print("=" * 60)
    
    print("\n最终居民状态:")
    print("-" * 60)
    sorted_agents = sorted(town.agents, key=lambda a: a.total_value, reverse=True)
    
    for i, agent in enumerate(sorted_agents, 1):
        status = agent.get_status()
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"  {medal} {i}. {status['name']}: "
              f"财富 {status['total_value']:,.0f}元 | "
              f"朋友 {status['friends']}个 | "
              f"心情 {status['mood']}")
    
    overview = town.get_town_overview()
    print("\n小镇总结:")
    print("-" * 60)
    print(f"  总对话次数: {overview['stats']['conversations']}")
    print(f"  建立友谊: {overview['stats']['friendships']} 对")
    print(f"  交易次数: {overview['stats']['trades']} 笔")
    
    if args.output:
        output_data = {
            "config": {
                "num_agents": args.agents,
                "num_days": args.days,
                "initial_capital": args.capital,
                "initial_price": args.price,
                "seed": args.seed,
            },
            "final_stats": overview['stats'],
            "agents": [a.get_status() for a in sorted_agents],
            "daily_logs": logs,
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {args.output}")
    
    return town


if __name__ == "__main__":
    main()
