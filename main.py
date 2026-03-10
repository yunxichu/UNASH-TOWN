"""
UNASH-TOWN: 股市交易小镇
多智能体股市交易模拟系统 - 主程序入口
"""
import argparse
import json
import random
from datetime import datetime

from src.exchange import ExchangeTown
from src.trader import TraderType


def main():
    parser = argparse.ArgumentParser(description="UNASH-TOWN 股市交易小镇模拟")
    parser.add_argument("--traders", type=int, default=10, help="交易者数量")
    parser.add_argument("--days", type=int, default=3, help="模拟天数")
    parser.add_argument("--capital", type=float, default=10000.0, help="初始资金")
    parser.add_argument("--price", type=float, default=100.0, help="初始股价")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  UNASH-TOWN: 股市交易小镇模拟系统")
    print("=" * 60)
    print(f"\n配置:")
    print(f"  交易者数量: {args.traders}")
    print(f"  模拟天数: {args.days}")
    print(f"  初始资金: {args.capital:,.2f}")
    print(f"  初始股价: {args.price:.2f}")
    print(f"  随机种子: {args.seed if args.seed else '随机'}")
    print()
    
    town = ExchangeTown(
        num_traders=args.traders,
        initial_capital=args.capital,
        initial_price=args.price,
        seed=args.seed,
        verbose=not args.quiet
    )
    
    print("\n初始交易者状态:")
    print("-" * 60)
    for trader in town.traders:
        print(f"  {trader.name}: {trader.trader_type.value}")
        print(f"    资金: {trader.capital:,.2f} | 风险偏好: {trader.profile['risk_tolerance']:.1f}")
    
    print("\n开始模拟...")
    print("=" * 60)
    
    logs = town.simulate_days(args.days)
    
    print("\n" + "=" * 60)
    print("模拟结束!")
    print("=" * 60)
    
    leaderboard = town.get_leaderboard()
    
    print("\n最终排行榜:")
    print("-" * 60)
    for i, status in enumerate(leaderboard, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"  {medal} {i}. {status['name']} ({status['type']}): "
              f"总资产 {status['total_value']:,.2f} | 收益率 {status['return_rate']}")
    
    market_overview = town.get_market_overview()
    print("\n市场概况:")
    print("-" * 60)
    market = market_overview["market"]
    print(f"  最终价格: {market['price']:.2f}")
    print(f"  涨跌幅: {market['change_pct']:.2f}%")
    print(f"  市场状态: {market['phase']}")
    print(f"  总成交量: {market['volume']:,}")
    
    if args.output:
        output_data = {
            "config": {
                "num_traders": args.traders,
                "num_days": args.days,
                "initial_capital": args.capital,
                "initial_price": args.price,
                "seed": args.seed,
            },
            "final_leaderboard": leaderboard,
            "market_summary": market,
            "daily_logs": [
                {
                    "day": log["day"],
                    "open": log["open"],
                    "high": log["high"],
                    "low": log["low"],
                    "close": log["close"],
                    "volume": log["volume"],
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
