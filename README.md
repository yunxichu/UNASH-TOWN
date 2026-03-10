# UNASH-TOWN 🏘️📈🤖

**可扩展多智能体股市交易系统**

一个支持动态增减智能体、API接入的多智能体博弈模拟系统，具有完整的订单簿、做市机制、技术指标和价格波动模型。

## 🎮 项目简介

UNASH-TOWN 是一个可扩展的多智能体股市交易模拟系统，支持：
- **动态智能体管理**: 运行时动态注册/注销智能体
- **API接入**: 外部智能体通过HTTP API接入
- **多种智能体类型**: 本地智能体、远程智能体、回调智能体
- **完整交易机制**: 订单簿、撮合引擎、做市商

### 核心特性

- **可扩展架构**: 支持1000+智能体同时在线
- **API服务**: RESTful API供外部智能体接入
- **10种交易策略**: 价值投资、动量交易、均值回归、做市商等
- **完整订单簿**: 买卖盘深度、价格撮合、成交记录
- **动态价格模型**: 长期有规律、短期多波动
- **技术指标系统**: RSI、MACD、布林带等

## 📦 安装

```bash
git clone https://github.com/yunxichu/UNASH-TOWN.git
cd UNASH-TOWN
```

项目仅使用 Python 标准库，无需额外依赖。

## 🚀 快速开始

```bash
# 基本运行
python main.py --days 3 --agents 10

# 启动API服务
python main.py --api --port 8080

# 完整参数
python main.py --agents 10 --days 5 --capital 10000 --api --port 8080 --api-key your_key
```

## 🔌 API接口

启动API服务后，可通过以下接口接入：

### 智能体管理

```bash
# 注册新智能体
POST /api/agents/register
{
    "type": "callback",
    "name": "MyAgent",
    "initial_capital": 10000,
    "capabilities": ["trading"]
}

# 注销智能体
POST /api/agents/unregister
{
    "agent_id": "agent_1_xxx"
}

# 列出所有智能体
GET /api/agents

# 获取智能体详情
GET /api/agents/{agent_id}
```

### 市场数据

```bash
# 市场状态
GET /api/market

# 排行榜
GET /api/leaderboard

# 健康检查
GET /api/health
```

### 交易决策

```bash
# 提交决策
POST /api/decide
{
    "agent_id": "agent_1_xxx",
    "context": {
        "market_data": {...},
        "technical": {...},
        "agent_state": {...}
    }
}
```

## 🤖 智能体类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| **LocalAgent** | 本地策略智能体 | 内置策略、快速测试 |
| **RemoteAgent** | 远程API智能体 | 外部AI模型接入 |
| **CallbackAgent** | 回调智能体 | 自定义逻辑、事件驱动 |

## 📖 开发指南

### 创建自定义智能体

```python
from src.agent_interface import BaseAgent, TradingContext, TradingDecision

class MyAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str):
        super().__init__(agent_id, name, initial_capital=10000)
    
    def decide(self, context: TradingContext) -> TradingDecision:
        # 你的交易逻辑
        if context.market_data.price < 90:
            return TradingDecision.buy(
                price=context.market_data.price,
                quantity=10,
                reasoning="Price is low"
            )
        return TradingDecision.no_action()
    
    def get_info(self):
        from src.agent_interface import AgentInfo, AgentType, AgentStatus
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.LOCAL,
            status=self.status
        )
```

### 注册智能体

```python
from src.agent_manager import AgentManager

manager = AgentManager(max_agents=1000)

# 方式1: 直接注册
agent = MyAgent("my_agent_1", "MyAgent")
agent_id = manager.register_agent(agent)

# 方式2: 创建本地智能体
agent_id = manager.create_local_agent(
    name="MyAgent",
    strategy=my_strategy_function,
    initial_capital=10000
)

# 方式3: 创建远程智能体
agent_id = manager.create_remote_agent(
    name="RemoteAgent",
    endpoint="http://your-ai-service:8000",
    initial_capital=10000
)
```

### 使用API接入

```python
import requests

# 注册智能体
response = requests.post("http://localhost:8080/api/agents/register", json={
    "type": "callback",
    "name": "ExternalAgent",
    "initial_capital": 10000
})
agent_id = response.json()["agent_id"]

# 获取市场数据
market = requests.get("http://localhost:8080/api/market").json()

# 提交交易决策
decision = requests.post("http://localhost:8080/api/decide", json={
    "agent_id": agent_id,
    "context": {...}
}).json()
```

## 🏗️ 项目结构

```
UNASH-TOWN/
├── main.py                 # 主程序入口
├── README.md               # 项目说明
└── src/
    ├── __init__.py         # 包初始化
    ├── agent_interface.py  # 智能体抽象接口
    ├── agent_manager.py    # 智能体管理器
    ├── api_server.py       # API服务层
    ├── trader.py           # 交易者智能体
    ├── trading.py          # 交易系统（订单簿、撮合）
    ├── market.py           # 市场模块（价格生成、技术指标）
    └── scalable_exchange.py # 可扩展交易所
```

## 🔧 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--agents` | 初始智能体数量 | 10 |
| `--days` | 模拟天数 | 3 |
| `--capital` | 初始资金 | 10000.0 |
| `--price` | 初始股价 | 100.0 |
| `--seed` | 随机种子 | None |
| `--api` | 启动API服务 | False |
| `--port` | API端口 | 8080 |
| `--api-key` | API密钥 | None |
| `--quiet` | 静默模式 | False |
| `--output` | 输出文件 | None |

## 🎯 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      API Server                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ /agents │  │ /market │  │ /decide │  │ /stats  │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        v            v            v            v
┌─────────────────────────────────────────────────────────────┐
│                    Agent Manager                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Registry (支持1000+智能体)                     │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │  │
│  │  │Local   │ │Remote  │ │Callback│ │Custom  │        │  │
│  │  │Agent   │ │Agent   │ │Agent   │ │Agent   │        │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────┐
│                   Scalable Exchange                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Order Book  │  │   Market    │  │  Matching   │        │
│  │             │  │   Engine    │  │   Engine    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
