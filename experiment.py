"""Run a reproducible UNASH-TOWN experiment and export CSV files."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.experiment import ExperimentConfig, run_experiment, write_experiment_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run UNASH-TOWN research experiment")
    parser.add_argument("--agents", type=int, default=12)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--price", type=float, default=100.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("runs/default"))
    args = parser.parse_args()

    config = ExperimentConfig(
        agents=args.agents,
        days=args.days,
        initial_capital=args.capital,
        initial_price=args.price,
        seed=args.seed,
    )
    result = run_experiment(config)
    write_experiment_outputs(result, args.out)
    print(f"Wrote experiment outputs to {args.out}")


if __name__ == "__main__":
    main()
