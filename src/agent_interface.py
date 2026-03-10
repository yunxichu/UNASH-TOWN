"""
智能体抽象接口层 - 定义统一的智能体接口，支持本地和远程智能体
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import time


class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DISCONNECTED = "disconnected"


class AgentType(Enum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.ACTIVE
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


@dataclass
class MarketData:
    price: float
    volume: int
    timestamp: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open_price: Optional[float] = None
    phase: str = "continuous"
    event: str = "none"
    
    def to_dict(self) -> Dict:
        return {
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "bid": self.bid,
            "ask": self.ask,
            "high": self.high,
            "low": self.low,
            "open_price": self.open_price,
            "phase": self.phase,
            "event": self.event,
        }


@dataclass
class TechnicalIndicators:
    rsi: float = 50.0
    macd: float = 0.0
    signal_line: float = 0.0
    momentum: float = 0.0
    trend_strength: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "rsi": self.rsi,
            "macd": self.macd,
            "signal_line": self.signal_line,
            "momentum": self.momentum,
            "trend_strength": self.trend_strength,
            "bollinger_upper": self.bollinger_upper,
            "bollinger_middle": self.bollinger_middle,
            "bollinger_lower": self.bollinger_lower,
        }


@dataclass
class AgentState:
    capital: float
    position: int
    avg_cost: float
    unrealized_pnl: float
    realized_pnl: float
    total_value: float
    return_rate: float
    
    def to_dict(self) -> Dict:
        return {
            "capital": self.capital,
            "position": self.position,
            "avg_cost": self.avg_cost,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_value": self.total_value,
            "return_rate": self.return_rate,
        }


@dataclass
class TradingContext:
    market_data: MarketData
    technical: TechnicalIndicators
    agent_state: AgentState
    order_book_depth: Dict[str, List]
    timestamp: int
    
    def to_dict(self) -> Dict:
        return {
            "market_data": self.market_data.to_dict(),
            "technical": self.technical.to_dict(),
            "agent_state": self.agent_state.to_dict(),
            "order_book_depth": self.order_book_depth,
            "timestamp": self.timestamp,
        }


@dataclass
class TradingDecision:
    action: str
    price: Optional[float] = None
    quantity: Optional[int] = None
    order_type: str = "limit"
    confidence: float = 0.5
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "price": self.price,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }
    
    @classmethod
    def no_action(cls) -> "TradingDecision":
        return cls(action="none")
    
    @classmethod
    def buy(cls, price: float, quantity: int, confidence: float = 0.5, reasoning: str = "") -> "TradingDecision":
        return cls(action="buy", price=price, quantity=quantity, confidence=confidence, reasoning=reasoning)
    
    @classmethod
    def sell(cls, price: float, quantity: int, confidence: float = 0.5, reasoning: str = "") -> "TradingDecision":
        return cls(action="sell", price=price, quantity=quantity, confidence=confidence, reasoning=reasoning)


class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str, initial_capital: float = 10000.0):
        self.agent_id = agent_id
        self.name = name
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0
        self.avg_cost = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.trade_history: List[Dict] = []
        self._status = AgentStatus.ACTIVE
        self._last_price = 0.0
    
    @property
    def total_value(self) -> float:
        return self.capital + self.position * self._last_price
    
    @property
    def return_rate(self) -> float:
        return (self.total_value - self.initial_capital) / self.initial_capital
    
    @property
    def status(self) -> AgentStatus:
        return self._status
    
    @status.setter
    def status(self, value: AgentStatus):
        self._status = value
    
    @abstractmethod
    def decide(self, context: TradingContext) -> TradingDecision:
        pass
    
    @abstractmethod
    def get_info(self) -> AgentInfo:
        pass
    
    def update_position(self, is_buy: bool, quantity: int, price: float, fee: float = 0.0):
        if is_buy:
            total_cost = self.avg_cost * self.position + price * quantity
            self.position += quantity
            self.avg_cost = total_cost / self.position if self.position > 0 else 0
            self.capital -= (price * quantity + fee)
        else:
            self.realized_pnl += (price - self.avg_cost) * quantity
            self.position -= quantity
            self.capital += (price * quantity - fee)
            if self.position <= 0:
                self.position = 0
                self.avg_cost = 0.0
        
        self._last_price = price
        self._update_unrealized_pnl()
    
    def _update_unrealized_pnl(self):
        if self.position > 0:
            self.unrealized_pnl = (self._last_price - self.avg_cost) * self.position
        else:
            self.unrealized_pnl = 0.0
    
    def update_price(self, price: float):
        self._last_price = price
        self._update_unrealized_pnl()
    
    def get_state(self) -> AgentState:
        return AgentState(
            capital=self.capital,
            position=self.position,
            avg_cost=self.avg_cost,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self.realized_pnl,
            total_value=self.total_value,
            return_rate=self.return_rate,
        )
    
    def on_trade_executed(self, trade_info: Dict):
        self.trade_history.append(trade_info)
    
    def on_market_event(self, event: str, data: Dict):
        pass
    
    def reset(self, capital: Optional[float] = None):
        self.capital = capital if capital is not None else self.initial_capital
        self.position = 0
        self.avg_cost = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.trade_history = []
        self._last_price = 0.0


class LocalAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        strategy: Callable[[TradingContext], TradingDecision],
        initial_capital: float = 10000.0,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ):
        super().__init__(agent_id, name, initial_capital)
        self._strategy = strategy
        self._capabilities = capabilities or []
        self._metadata = metadata or {}
    
    def decide(self, context: TradingContext) -> TradingDecision:
        return self._strategy(context)
    
    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.LOCAL,
            status=self._status,
            capabilities=self._capabilities,
            metadata=self._metadata,
        )


class RemoteAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        endpoint: str,
        initial_capital: float = 10000.0,
        api_key: Optional[str] = None,
        timeout: float = 5.0
    ):
        super().__init__(agent_id, name, initial_capital)
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._capabilities: List[str] = []
        self._metadata: Dict = {}
    
    def decide(self, context: TradingContext) -> TradingDecision:
        try:
            import urllib.request
            import urllib.error
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = json.dumps({
                "agent_id": self.agent_id,
                "context": context.to_dict()
            }).encode("utf-8")
            
            req = urllib.request.Request(
                f"{self.endpoint}/decide",
                data=payload,
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return TradingDecision(
                    action=result.get("action", "none"),
                    price=result.get("price"),
                    quantity=result.get("quantity"),
                    order_type=result.get("order_type", "limit"),
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("reasoning", ""),
                    metadata=result.get("metadata", {}),
                )
        except Exception as e:
            return TradingDecision.no_action()
    
    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.REMOTE,
            status=self._status,
            capabilities=self._capabilities,
            metadata={"endpoint": self.endpoint, **self._metadata},
        )
    
    def ping(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.endpoint}/health", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except:
            return False


class CallbackAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        initial_capital: float = 10000.0,
        on_decide: Optional[Callable[[TradingContext], TradingDecision]] = None,
        on_trade: Optional[Callable[[Dict], None]] = None,
        on_event: Optional[Callable[[str, Dict], None]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ):
        super().__init__(agent_id, name, initial_capital)
        self._on_decide = on_decide
        self._on_trade = on_trade
        self._on_event = on_event
        self._capabilities = capabilities or []
        self._metadata = metadata or {}
    
    def decide(self, context: TradingContext) -> TradingDecision:
        if self._on_decide:
            return self._on_decide(context)
        return TradingDecision.no_action()
    
    def on_trade_executed(self, trade_info: Dict):
        super().on_trade_executed(trade_info)
        if self._on_trade:
            self._on_trade(trade_info)
    
    def on_market_event(self, event: str, data: Dict):
        if self._on_event:
            self._on_event(event, data)
    
    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.HYBRID,
            status=self._status,
            capabilities=self._capabilities,
            metadata=self._metadata,
        )
