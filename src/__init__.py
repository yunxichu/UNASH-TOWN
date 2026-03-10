"""
UNASH-TOWN: 可扩展多智能体股市交易系统
"""

from .agent_interface import (
    BaseAgent, LocalAgent, RemoteAgent, CallbackAgent,
    AgentInfo, AgentStatus, AgentType,
    TradingContext, TradingDecision,
    MarketData, TechnicalIndicators, AgentState,
)
from .agent_manager import AgentManager, AgentEvent
from .api_server import APIServer, APIConfig
from .trader import TraderAgent, TraderType, create_traders
from .trading import Order, OrderBook, OrderType, TradingRules, MarketMaker
from .market import AShareMarket, MarketPhase, MarketEvent, TradingSession
from .scalable_exchange import ScalableExchange

__all__ = [
    'BaseAgent', 'LocalAgent', 'RemoteAgent', 'CallbackAgent',
    'AgentInfo', 'AgentStatus', 'AgentType',
    'TradingContext', 'TradingDecision',
    'MarketData', 'TechnicalIndicators', 'AgentState',
    'AgentManager', 'AgentEvent',
    'APIServer', 'APIConfig',
    'TraderAgent', 'TraderType', 'create_traders',
    'Order', 'OrderBook', 'OrderType', 'TradingRules', 'MarketMaker',
    'AShareMarket', 'MarketPhase', 'MarketEvent', 'TradingSession',
    'ScalableExchange',
]
__version__ = '2.0.0'
