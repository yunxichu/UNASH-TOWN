"""Run the UNASH-TOWN web dashboard."""
from __future__ import annotations

import argparse
import threading
import time

from src.nash_town import NashTown
from src.visualization import TOWN_DATA, run_visualization_server


class SimulationRunner:
    def __init__(self, town: NashTown, agents: int, capital: float, price: float, seed: int | None) -> None:
        self.town = town
        self.agents = agents
        self.capital = capital
        self.price = price
        self.seed = seed
        self.running = False
        self.speed = 1
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.running = False
        self.town = NashTown(self.agents, self.capital, self.price, self.seed, verbose=False)
        TOWN_DATA["town"] = self.town

    def set_speed(self, speed: int) -> None:
        self.speed = max(1, min(16, speed))

    def _loop(self) -> None:
        while self.running:
            self.town.simulate_tick()
            time.sleep(0.18 / self.speed)


def main() -> None:
    parser = argparse.ArgumentParser(description="UNASH-TOWN web dashboard")
    parser.add_argument("--agents", type=int, default=12)
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--price", type=float, default=100.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    town = NashTown(args.agents, args.capital, args.price, args.seed, verbose=False)
    runner = SimulationRunner(town, args.agents, args.capital, args.price, args.seed)
    TOWN_DATA["town"] = town
    TOWN_DATA["runner"] = runner

    print(f"UNASH-TOWN dashboard: http://{args.host}:{args.port}")
    run_visualization_server(town, host=args.host, port=args.port, runner=runner)


if __name__ == "__main__":
    main()
