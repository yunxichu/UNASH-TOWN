"""
UNASH-TOWN: 多智能体博弈小镇
主程序入口
"""
import argparse
import json
import random
from datetime import datetime

from src.agent import create_diverse_agents, AgentTendency
from src.town import Town
from src.game import GameEngine


def main():
    parser = argparse.ArgumentParser(description="UNASH-TOWN 多智能体博弈小镇模拟")
    parser.add_argument("--agents", type=int, default=10, help="智能体数量")
    parser.add_argument("--days", type=int, default=3, help="模拟天数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  UNASH-TOWN: 多智能体博弈小镇模拟系统")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  智能体数量: {args.agents}")
    print(f"  模拟天数: {args.days}")
    print(f"  随机种子: {args.seed if args.seed else '随机'}")
    print()
    
    town = Town(
        num_agents=args.agents,
        zero_sum_mode=True,
        random_seed=args.seed,
        verbose=not args.quiet
    )
    
    print("\n初始智能体状态:")
    print("-" * 50)
    for agent in town.agents:
        traits_str = ", ".join(f"{k}:{v:.2f}" for k, v in list(agent.traits.items())[:3])
        print(f"  {agent.name}: {agent.tendency.value}")
        print(f"    特征: {traits_str}...")
    
    print("\n开始模拟...")
    print("=" * 60)
    
    logs = town.simulate_days(args.days)
    
    print("\n" + "=" * 60)
    print("模拟结束!")
    print("=" * 60)
    
    final_status = town.get_agent_status()
    
    print("\n最终排名:")
    print("-" * 50)
    for i, status in enumerate(final_status, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"  {medal} {i}. {status['name']} ({status['tendency']}): {status['resources']:.1f} 资源")
    
    stats = town.game_engine.get_statistics()
    print("\n总体博弈统计:")
    print("-" * 50)
    print(f"  总博弈场次: {stats['total_games']}")
    print(f"  平均收益: {stats['average_payoff']}")
    print(f"  合作率: {stats['cooperation_rate']*100:.1f}%")
    print(f"  背叛率: {stats['defection_rate']*100:.1f}%")
    print(f"  妥协率: {stats['compromise_rate']*100:.1f}%")
    
    if args.output:
        output_data = {
            "config": {
                "num_agents": args.agents,
                "num_days": args.days,
                "seed": args.seed,
            },
            "final_status": final_status,
            "game_statistics": stats,
            "day_summaries": [
                {
                    "day": log.day,
                    "games_played": len(log.game_results),
                    "social_interactions": len(log.social_interactions),
                    "final_resources": log.final_resources
                }
                for log in logs
            ]
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {args.output}")
    
    return town


if __name__ == "__main__":
    main()
