"""Command line entry point for UNASH-TOWN."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.nash_town import NashTown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UNASH-TOWN: heterogeneous A-share trader simulation"
    )
    parser.add_argument("--agents", type=int, default=12, help="number of trader agents")
    parser.add_argument("--days", type=int, default=5, help="simulation days")
    parser.add_argument("--capital", type=float, default=100000.0, help="initial capital per agent")
    parser.add_argument("--price", type=float, default=100.0, help="initial synthetic security price")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--quiet", action="store_true", help="suppress daily summaries")
    parser.add_argument("--output", type=Path, help="write full JSON result")
    return parser


def main() -> NashTown:
    args = build_parser().parse_args()
    town = NashTown(
        num_agents=args.agents,
        initial_capital=args.capital,
        initial_price=args.price,
        seed=args.seed,
        verbose=not args.quiet,
    )

    print("UNASH-TOWN")
    print(f"agents={args.agents} days={args.days} capital={args.capital:,.0f} seed={args.seed}")
    print()

    logs = town.simulate_days(args.days)
    overview = town.get_town_overview()
    final_snapshot = logs[-1] if logs else overview
    agents = sorted(final_snapshot["agents"], key=lambda item: item["total_value"], reverse=True)

    print("Final market")
    market = final_snapshot["market"]
    print(
        f"  {market['name']} close={market['price']:.2f} "
        f"change={market['change_pct']:+.2f}% regime={market['regime']} event={market['event']}"
    )
    print("Leaderboard")
    for index, agent in enumerate(agents[:10], 1):
        print(
            f"  {index:>2}. {agent['name']:<10} {agent['label']:<12} "
            f"value={agent['total_value']:>10,.0f} return={agent['return_rate']:>7.2f}% "
            f"style={agent['dominant_style']}"
        )

    if args.output:
        payload = {
            "config": vars(args) | {"output": str(args.output)},
            "daily_logs": logs,
            "overview": overview,
        }
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote {args.output}")

    return town


if __name__ == "__main__":
    main()
