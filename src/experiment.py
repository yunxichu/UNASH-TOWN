"""Experiment helpers for reproducible simulation runs."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List
import csv
import json

from .nash_town import NashTown


@dataclass
class ExperimentConfig:
    agents: int = 12
    days: int = 20
    initial_capital: float = 100000.0
    initial_price: float = 100.0
    seed: int = 42


def run_experiment(config: ExperimentConfig) -> Dict:
    town = NashTown(
        num_agents=config.agents,
        initial_capital=config.initial_capital,
        initial_price=config.initial_price,
        seed=config.seed,
        verbose=False,
    )
    daily_logs = town.simulate_days(config.days)
    return {
        "config": asdict(config),
        "daily_logs": daily_logs,
        "overview": town.get_town_overview(),
    }


def write_experiment_outputs(result: Dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_market_csv(result["daily_logs"], output_dir / "market.csv")
    _write_agents_csv(result["daily_logs"], output_dir / "agents.csv")


def _write_market_csv(daily_logs: List[Dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "day",
                "price",
                "change_pct",
                "volume",
                "turnover",
                "regime",
                "event",
                "trades",
            ],
        )
        writer.writeheader()
        for log in daily_logs:
            market = log["market"]
            stats = log["stats"]
            writer.writerow(
                {
                    "day": log["day"],
                    "price": market["price"],
                    "change_pct": market["change_pct"],
                    "volume": market["volume"],
                    "turnover": market["turnover"],
                    "regime": market["regime"],
                    "event": market["event"],
                    "trades": stats["total_trades"],
                }
            )


def _write_agents_csv(daily_logs: List[Dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "day",
                "agent_id",
                "name",
                "archetype",
                "style",
                "total_value",
                "return_rate",
                "position",
                "trade_count",
                "win_rate",
            ],
        )
        writer.writeheader()
        for log in daily_logs:
            for agent in log["agents"]:
                writer.writerow(
                    {
                        "day": log["day"],
                        "agent_id": agent["agent_id"],
                        "name": agent["name"],
                        "archetype": agent["archetype"],
                        "style": agent["dominant_style"],
                        "total_value": agent["total_value"],
                        "return_rate": agent["return_rate"],
                        "position": agent["position"],
                        "trade_count": agent["trade_count"],
                        "win_rate": agent["win_rate"],
                    }
                )
