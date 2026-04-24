# UNASH-TOWN

UNASH-TOWN（永不纳什小镇）是一个面向 A 股市场行为研究的多智能体交易仿真原型。

项目保留“小镇居民”的叙事外壳，但核心不是角色扮演，而是在具有 A 股约束的市场环境里观察异质交易者如何下单、成交、持仓、反馈学习，并逐步形成稳定或失效的行为风格。

## 设计参考

重塑时参考了几类相近项目的常见做法：

- Agent-based simulation 项目通常把环境、智能体、撮合机制、指标快照拆开，方便替换实验组件。
- Market simulation 项目强调交易规则、成本、撮合顺序和可重复随机种子，否则结果难以解释。
- Community/town 可视化项目更适合做“观察台”，让用户看到状态、关系和事件，而不是把所有逻辑塞进页面。

因此当前版本把代码收敛成五个核心层次：

1. 市场环境：价格、regime、事件、波动、涨跌停。
2. 交易规则：限价单、价格优先/时间优先、手续费、印花税、T+1 可卖仓。
3. 异质智能体：价值、动量、套利、波动、对冲、噪声、成长、逆向、量化、学习型。
4. 仿真引擎：按交易日分钟推进，记录订单、成交、收益和每日快照。
5. 可视化入口：Flask dashboard 展示市场、排行榜和智能体状态。

## 快速开始

```bash
pip install -r requirements.txt
python main.py --agents 12 --days 5 --seed 42
```

输出 JSON：

```bash
python main.py --agents 20 --days 30 --output results.json
```

导出研究数据：

```bash
python experiment.py --agents 20 --days 30 --out runs/baseline
```

这会生成：

```text
runs/baseline/summary.json
runs/baseline/market.csv
runs/baseline/agents.csv
```

启动可视化：

```bash
python visualize.py --agents 16 --port 5000
```

然后打开：

```text
http://127.0.0.1:5000
```

## 代码结构

```text
src/
  market.py          # A 股市场环境：regime、事件、涨跌停、技术指标
  trading.py         # 订单、成交、撮合、手续费、印花税、T+1 约束
  experiment.py      # 可重复实验与 CSV/JSON 导出
  personality.py     # 交易者原型与初始偏好
  town_agent.py      # 异质交易智能体与行为反馈
  nash_town.py       # 仿真主循环与研究快照
  visualization.py   # Flask dashboard
main.py              # 命令行实验入口
experiment.py        # 批量研究数据导出入口
visualize.py         # 可视化启动入口
```

## 核心思想

“永不纳什”表达的是：真实市场很少静止在某个单一均衡里。参与者在变，信息在变，流动性在变，策略也在相互适应。

本项目关心的不是谁在某次交易里赚最多，而是：

- 不同类型交易者会形成哪些可观察的行为模式；
- 这些模式如何随市场 regime 变化而迁移、收敛或失效；
- 多智能体交互如何共同塑造价格、成交量、波动和拥挤度；
- A 股约束如何改变策略有效性和风险暴露。

## 当前能力

- 可重复仿真：支持随机种子。
- A 股基础约束：涨跌停、最小交易单位、T+1 可卖仓、手续费、印花税。
- 异质交易者：十类原型拥有不同风险偏好、仓位尺度和信号权重。
- 市场反馈：订单簿不平衡和成交压力会影响下一步价格。
- 行为记录：每日市场快照、智能体收益、成交日志和排行榜。
- Web dashboard：可启动、暂停、单步推进和调速。

## 下一步计划

- 增加多标的组合和行业轮动。
- 将智能体策略反馈升级为更明确的 Q-learning 或 bandit 模块。
- 输出行为聚类指标，例如换手率、持仓周期、回撤、风格漂移。
- 增加实验配置文件，方便批量跑不同市场 regime。
- 给 dashboard 增加订单簿深度、价格曲线和单个智能体详情页。

## 许可证

MIT
