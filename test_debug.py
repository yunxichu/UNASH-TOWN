from src.nash_town import NashTown


def test_simulation_produces_daily_snapshot():
    town = NashTown(num_agents=6, seed=3, verbose=False)

    snapshot = town.simulate_day()

    assert snapshot["day"] == 1
    assert snapshot["market"]["price"] > 0
    assert len(snapshot["agents"]) == 6
    assert "total_trades" in snapshot["stats"]


def test_agent_status_exposes_research_fields():
    town = NashTown(num_agents=4, seed=5, verbose=False)
    for _ in range(10):
        town.simulate_tick()

    status = town.get_town_overview()["agents"][0]

    assert {"archetype", "dominant_style", "risk", "position_size", "return_rate"} <= set(status)
    assert isinstance(status["return_rate"], float)
