from src.nash_town import NashTown

town = NashTown(num_agents=5, verbose=True)

print("\n" + "="*60)
print("智能体初始状态:")
print("="*60)
for agent in town.agents:
    status = agent.get_status()
    print(f"  {status['name']} [{status['archetype']}]:")
    print(f"    初始风格: {status['dominant_style']}")
    print(f"    风险偏好: {status['style_params']['risk_tolerance']:.2f}")

print("\n" + "="*60)
print("开始模拟 3 天...")
print("="*60)

for day in range(3):
    result = town.simulate_day()
    
    print(f"\n--- 第 {day+1} 天后智能体状态 ---")
    for agent in town.agents:
        status = agent.get_status()
        print(f"  {status['name']}: 风格={status['dominant_style']}, "
              f"收益率={status['return_rate']}, 交易次数={status['total_trades']}, "
              f"胜率={status['win_rate']}")

print("\n" + "="*60)
print("最终风格分析:")
print("="*60)
for agent in town.agents:
    status = agent.get_status()
    strategy_status = agent.strategy_explorer.get_status()
    print(f"\n{status['name']} [{status['archetype']}]:")
    print(f"  主导风格: {status['dominant_style']}")
    print(f"  当前策略: {status['current_strategy']}")
    print(f"  风格参数: 风险={status['style_params']['risk_tolerance']:.2f}, "
          f"仓位={status['style_params']['position_size']:.2f}")
    print(f"  策略置信度: {strategy_status['strategy_confidence']}")
    print(f"  总交易: {status['total_trades']}, 胜率: {status['win_rate']}")
    print(f"  最终资产: {status['total_value']}元, 收益率: {status['return_rate']}")
