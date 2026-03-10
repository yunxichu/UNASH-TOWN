"""
智能体管理器 - 动态注册、注销、管理智能体
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import uuid
import time
import threading
from collections import defaultdict

from .agent_interface import (
    BaseAgent, LocalAgent, RemoteAgent, CallbackAgent,
    AgentInfo, AgentStatus, AgentType, TradingContext, TradingDecision
)


class AgentEvent(Enum):
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    TRADE_EXECUTED = "trade_executed"
    ERROR = "error"


@dataclass
class AgentRegistryEntry:
    agent: BaseAgent
    registered_at: float
    last_decision_time: float = 0.0
    total_decisions: int = 0
    total_trades: int = 0
    errors: List[str] = field(default_factory=list)


class AgentManager:
    def __init__(self, max_agents: int = 100):
        self._agents: Dict[str, AgentRegistryEntry] = {}
        self._max_agents = max_agents
        self._lock = threading.RLock()
        self._event_handlers: Dict[AgentEvent, List[Callable]] = defaultdict(list)
        self._agent_id_counter = 0
    
    def register_agent(
        self,
        agent: BaseAgent,
        auto_activate: bool = True
    ) -> str:
        with self._lock:
            if len(self._agents) >= self._max_agents:
                raise ValueError(f"Maximum number of agents ({self._max_agents}) reached")
            
            agent_id = agent.agent_id
            if agent_id in self._agents:
                raise ValueError(f"Agent with ID {agent_id} already registered")
            
            if auto_activate:
                agent.status = AgentStatus.ACTIVE
            
            entry = AgentRegistryEntry(
                agent=agent,
                registered_at=time.time()
            )
            self._agents[agent_id] = entry
            
            self._emit_event(AgentEvent.REGISTERED, {
                "agent_id": agent_id,
                "agent_info": agent.get_info().to_dict()
            })
            
            return agent_id
    
    def unregister_agent(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            entry = self._agents.pop(agent_id)
            entry.agent.status = AgentStatus.INACTIVE
            
            self._emit_event(AgentEvent.UNREGISTERED, {
                "agent_id": agent_id,
                "agent_info": entry.agent.get_info().to_dict()
            })
            
            return True
    
    def create_local_agent(
        self,
        name: str,
        strategy: Callable[[TradingContext], TradingDecision],
        initial_capital: float = 10000.0,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        agent_id = self._generate_agent_id()
        agent = LocalAgent(
            agent_id=agent_id,
            name=name,
            strategy=strategy,
            initial_capital=initial_capital,
            capabilities=capabilities,
            metadata=metadata
        )
        return self.register_agent(agent)
    
    def create_remote_agent(
        self,
        name: str,
        endpoint: str,
        initial_capital: float = 10000.0,
        api_key: Optional[str] = None
    ) -> str:
        agent_id = self._generate_agent_id()
        agent = RemoteAgent(
            agent_id=agent_id,
            name=name,
            endpoint=endpoint,
            initial_capital=initial_capital,
            api_key=api_key
        )
        return self.register_agent(agent)
    
    def create_callback_agent(
        self,
        name: str,
        initial_capital: float = 10000.0,
        on_decide: Optional[Callable[[TradingContext], TradingDecision]] = None,
        on_trade: Optional[Callable[[Dict], None]] = None,
        on_event: Optional[Callable[[str, Dict], None]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        agent_id = self._generate_agent_id()
        agent = CallbackAgent(
            agent_id=agent_id,
            name=name,
            initial_capital=initial_capital,
            on_decide=on_decide,
            on_trade=on_trade,
            on_event=on_event,
            capabilities=capabilities,
            metadata=metadata
        )
        return self.register_agent(agent)
    
    def _generate_agent_id(self) -> str:
        self._agent_id_counter += 1
        return f"agent_{self._agent_id_counter}_{uuid.uuid4().hex[:8]}"
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        with self._lock:
            entry = self._agents.get(agent_id)
            return entry.agent if entry else None
    
    def get_all_agents(self, status: Optional[AgentStatus] = None) -> List[BaseAgent]:
        with self._lock:
            agents = [entry.agent for entry in self._agents.values()]
            if status:
                agents = [a for a in agents if a.status == status]
            return agents
    
    def get_active_agents(self) -> List[BaseAgent]:
        return self.get_all_agents(status=AgentStatus.ACTIVE)
    
    def activate_agent(self, agent_id: str) -> bool:
        with self._lock:
            entry = self._agents.get(agent_id)
            if not entry:
                return False
            
            entry.agent.status = AgentStatus.ACTIVE
            self._emit_event(AgentEvent.ACTIVATED, {"agent_id": agent_id})
            return True
    
    def deactivate_agent(self, agent_id: str) -> bool:
        with self._lock:
            entry = self._agents.get(agent_id)
            if not entry:
                return False
            
            entry.agent.status = AgentStatus.INACTIVE
            self._emit_event(AgentEvent.DEACTIVATED, {"agent_id": agent_id})
            return True
    
    def suspend_agent(self, agent_id: str, reason: str = "") -> bool:
        with self._lock:
            entry = self._agents.get(agent_id)
            if not entry:
                return False
            
            entry.agent.status = AgentStatus.SUSPENDED
            if reason:
                entry.errors.append(f"Suspended: {reason}")
            
            self._emit_event(AgentEvent.SUSPENDED, {
                "agent_id": agent_id,
                "reason": reason
            })
            return True
    
    def resume_agent(self, agent_id: str) -> bool:
        with self._lock:
            entry = self._agents.get(agent_id)
            if not entry:
                return False
            
            entry.agent.status = AgentStatus.ACTIVE
            self._emit_event(AgentEvent.RESUMED, {"agent_id": agent_id})
            return True
    
    def record_decision(self, agent_id: str):
        with self._lock:
            entry = self._agents.get(agent_id)
            if entry:
                entry.total_decisions += 1
                entry.last_decision_time = time.time()
    
    def record_trade(self, agent_id: str):
        with self._lock:
            entry = self._agents.get(agent_id)
            if entry:
                entry.total_trades += 1
    
    def record_error(self, agent_id: str, error: str):
        with self._lock:
            entry = self._agents.get(agent_id)
            if entry:
                entry.errors.append(f"{time.time()}: {error}")
                self._emit_event(AgentEvent.ERROR, {
                    "agent_id": agent_id,
                    "error": error
                })
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict]:
        with self._lock:
            entry = self._agents.get(agent_id)
            if not entry:
                return None
            
            return {
                "agent_id": agent_id,
                "registered_at": entry.registered_at,
                "last_decision_time": entry.last_decision_time,
                "total_decisions": entry.total_decisions,
                "total_trades": entry.total_trades,
                "error_count": len(entry.errors),
                "agent_state": entry.agent.get_state().to_dict(),
            }
    
    def get_all_stats(self) -> List[Dict]:
        return [self.get_agent_stats(aid) for aid in self._agents.keys()]
    
    def on_event(self, event_type: AgentEvent, handler: Callable):
        self._event_handlers[event_type].append(handler)
    
    def _emit_event(self, event_type: AgentEvent, data: Dict):
        for handler in self._event_handlers[event_type]:
            try:
                handler(event_type, data)
            except Exception:
                pass
    
    def broadcast_market_event(self, event: str, data: Dict):
        with self._lock:
            for entry in self._agents.values():
                try:
                    entry.agent.on_market_event(event, data)
                except Exception:
                    pass
    
    def get_leaderboard(self) -> List[Dict]:
        with self._lock:
            leaderboard = []
            for entry in self._agents.values():
                agent = entry.agent
                state = agent.get_state()
                leaderboard.append({
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "agent_type": agent.get_info().agent_type.value,
                    "total_value": state.total_value,
                    "return_rate": state.return_rate,
                    "total_trades": entry.total_trades,
                })
            
            return sorted(leaderboard, key=lambda x: x["total_value"], reverse=True)
    
    def reset_all(self, capital: Optional[float] = None):
        with self._lock:
            for entry in self._agents.values():
                entry.agent.reset(capital)
                entry.total_decisions = 0
                entry.total_trades = 0
                entry.errors = []
    
    @property
    def agent_count(self) -> int:
        return len(self._agents)
    
    @property
    def active_count(self) -> int:
        return len(self.get_active_agents())
