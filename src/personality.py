"""
永不纳什小镇 - 智能体人格系统
包含完整的人格参数、记忆、学习和社交网络
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import random


class AgentArchetype(Enum):
    TRADER = "trader"
    GAMBLER = "gambler"
    CONSERVATIVE = "conservative"
    OPPORTUNIST = "opportunist"
    REVENGEFUL = "revengeful"
    SOCIALITE = "socialite"
    HERMIT = "hermit"
    MANIPULATOR = "manipulator"
    LEARNER = "learner"
    CHAOTIC = "chaotic"


ARCHETYPE_PROFILES = {
    AgentArchetype.TRADER: {
        "risk": 0.5, "trust": 0.6, "memory": 0.7, "greed": 0.6,
        "revenge": 0.3, "social": 0.8, "learning": 0.6,
        "description": "喜欢交换信息，建立贸易网络"
    },
    AgentArchetype.GAMBLER: {
        "risk": 0.9, "trust": 0.3, "memory": 0.3, "greed": 0.8,
        "revenge": 0.5, "social": 0.5, "learning": 0.4,
        "description": "高风险高回报，敢于冒险"
    },
    AgentArchetype.CONSERVATIVE: {
        "risk": 0.2, "trust": 0.7, "memory": 0.8, "greed": 0.3,
        "revenge": 0.2, "social": 0.4, "learning": 0.5,
        "description": "稳健策略，避免风险"
    },
    AgentArchetype.OPPORTUNIST: {
        "risk": 0.6, "trust": 0.3, "memory": 0.5, "greed": 0.7,
        "revenge": 0.4, "social": 0.7, "learning": 0.7,
        "description": "看谁强就靠谁，随风倒"
    },
    AgentArchetype.REVENGEFUL: {
        "risk": 0.5, "trust": 0.2, "memory": 0.9, "greed": 0.5,
        "revenge": 0.9, "social": 0.4, "learning": 0.6,
        "description": "记仇，有仇必报"
    },
    AgentArchetype.SOCIALITE: {
        "risk": 0.4, "trust": 0.7, "memory": 0.5, "greed": 0.4,
        "revenge": 0.2, "social": 0.9, "learning": 0.5,
        "description": "频繁社交，建立广泛关系"
    },
    AgentArchetype.HERMIT: {
        "risk": 0.5, "trust": 0.3, "memory": 0.6, "greed": 0.4,
        "revenge": 0.3, "social": 0.1, "learning": 0.7,
        "description": "独来独往，不太社交"
    },
    AgentArchetype.MANIPULATOR: {
        "risk": 0.6, "trust": 0.1, "memory": 0.7, "greed": 0.8,
        "revenge": 0.6, "social": 0.7, "learning": 0.6,
        "description": "散布假消息，操控他人"
    },
    AgentArchetype.LEARNER: {
        "risk": 0.5, "trust": 0.5, "memory": 0.8, "greed": 0.4,
        "revenge": 0.3, "social": 0.6, "learning": 0.9,
        "description": "快速学习，不断调整策略"
    },
    AgentArchetype.CHAOTIC: {
        "risk": 0.5, "trust": 0.5, "memory": 0.2, "greed": 0.5,
        "revenge": 0.5, "social": 0.5, "learning": 0.3,
        "description": "行为随机，不可预测"
    },
}


@dataclass
class Personality:
    risk: float = 0.5
    trust: float = 0.5
    memory: float = 0.5
    greed: float = 0.5
    revenge: float = 0.5
    social: float = 0.5
    learning: float = 0.5
    
    archetype: AgentArchetype = AgentArchetype.CHAOTIC
    
    def __post_init__(self):
        profile = ARCHETYPE_PROFILES.get(self.archetype, {})
        if profile:
            for attr in ["risk", "trust", "memory", "greed", "revenge", "social", "learning"]:
                if hasattr(self, attr):
                    base = profile.get(attr, 0.5)
                    noise = random.uniform(-0.1, 0.1)
                    setattr(self, attr, max(0.0, min(1.0, base + noise)))
    
    def get_description(self) -> str:
        profile = ARCHETYPE_PROFILES.get(self.archetype, {})
        return profile.get("description", "普通居民")
    
    def adjust(self, attr: str, delta: float):
        if hasattr(self, attr):
            current = getattr(self, attr)
            new_value = current + delta * self.learning
            setattr(self, attr, max(0.0, min(1.0, new_value)))


@dataclass
class MemoryRecord:
    agent_id: str
    event_type: str
    outcome: str
    timestamp: int
    details: Dict = field(default_factory=dict)
    importance: float = 0.5


@dataclass
class AgentMemory:
    records: List[MemoryRecord] = field(default_factory=list)
    interactions: Dict[str, List[Dict]] = field(default_factory=dict)
    betrayals: Dict[str, int] = field(default_factory=dict)
    cooperations: Dict[str, int] = field(default_factory=dict)
    
    max_records: int = 100
    
    def record_event(self, record: MemoryRecord):
        self.records.append(record)
        if len(self.records) > self.max_records:
            self.records.pop(0)
    
    def record_interaction(self, agent_id: str, interaction: Dict):
        if agent_id not in self.interactions:
            self.interactions[agent_id] = []
        self.interactions[agent_id].append(interaction)
    
    def record_betrayal(self, agent_id: str):
        self.betrayals[agent_id] = self.betrayals.get(agent_id, 0) + 1
    
    def record_cooperation(self, agent_id: str):
        self.cooperations[agent_id] = self.cooperations.get(agent_id, 0) + 1
    
    def get_trust_score(self, agent_id: str) -> float:
        betrayals = self.betrayals.get(agent_id, 0)
        cooperations = self.cooperations.get(agent_id, 0)
        total = betrayals + cooperations
        
        if total == 0:
            return 0.5
        
        return cooperations / total
    
    def get_interaction_count(self, agent_id: str) -> int:
        return len(self.interactions.get(agent_id, []))
    
    def get_recent_betrayals(self, agent_id: str, lookback: int = 5) -> int:
        if agent_id not in self.interactions:
            return 0
        
        recent = self.interactions[agent_id][-lookback:]
        return sum(1 for i in recent if i.get("type") == "betrayal")
    
    def get_remembered_agents(self) -> Set[str]:
        return set(self.interactions.keys())
    
    def forget_old_memories(self, current_time: int, retention: float = 0.7):
        threshold = current_time - int(100 / retention)
        self.records = [r for r in self.records if r.timestamp > threshold]


@dataclass
class Reputation:
    trust_score: float = 50.0
    betray_count: int = 0
    cooperation_count: int = 0
    rumor_count: int = 0
    alliance_count: int = 0
    
    def update_betrayal(self):
        self.betray_count += 1
        self.trust_score = max(0, self.trust_score - 10)
    
    def update_cooperation(self):
        self.cooperation_count += 1
        self.trust_score = min(100, self.trust_score + 5)
    
    def update_rumor(self, is_true: bool):
        self.rumor_count += 1
        if not is_true:
            self.trust_score = max(0, self.trust_score - 15)
    
    def get_reputation_level(self) -> str:
        if self.trust_score >= 80:
            return "值得信赖"
        elif self.trust_score >= 60:
            return "信誉良好"
        elif self.trust_score >= 40:
            return "一般"
        elif self.trust_score >= 20:
            return "可疑"
        else:
            return "不可信任"


@dataclass
class Alliance:
    members: Set[str] = field(default_factory=set)
    formed_day: int = 0
    strength: float = 0.5
    shared_info: List[Dict] = field(default_factory=list)
    
    def add_member(self, agent_id: str):
        self.members.add(agent_id)
    
    def remove_member(self, agent_id: str):
        self.members.discard(agent_id)
        self.strength = max(0, self.strength - 0.2)
    
    def share_information(self, info: Dict):
        self.shared_info.append(info)
    
    def is_member(self, agent_id: str) -> bool:
        return agent_id in self.members


@dataclass
class SocialGraph:
    friends: Set[str] = field(default_factory=set)
    enemies: Set[str] = field(default_factory=set)
    allies: Set[str] = field(default_factory=set)
    rivals: Set[str] = field(default_factory=set)
    
    alliances: List[Alliance] = field(default_factory=list)
    
    trust_scores: Dict[str, float] = field(default_factory=dict)
    relationship_history: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_friend(self, agent_id: str):
        self.friends.add(agent_id)
        self.enemies.discard(agent_id)
        self._update_trust(agent_id, 10)
    
    def add_enemy(self, agent_id: str):
        self.enemies.add(agent_id)
        self.friends.discard(agent_id)
        self.allies.discard(agent_id)
        self._update_trust(agent_id, -20)
    
    def add_ally(self, agent_id: str):
        self.allies.add(agent_id)
        self._update_trust(agent_id, 15)
    
    def add_rival(self, agent_id: str):
        self.rivals.add(agent_id)
    
    def _update_trust(self, agent_id: str, delta: float):
        current = self.trust_scores.get(agent_id, 50.0)
        self.trust_scores[agent_id] = max(0, min(100, current + delta))
    
    def get_trust(self, agent_id: str) -> float:
        return self.trust_scores.get(agent_id, 50.0)
    
    def is_friend(self, agent_id: str) -> bool:
        return agent_id in self.friends
    
    def is_enemy(self, agent_id: str) -> bool:
        return agent_id in self.enemies
    
    def is_ally(self, agent_id: str) -> bool:
        return agent_id in self.allies
    
    def form_alliance(self, members: Set[str], day: int) -> Alliance:
        alliance = Alliance(members=members, formed_day=day)
        self.alliances.append(alliance)
        for member in members:
            self.add_ally(member)
        return alliance
    
    def record_relationship_event(self, agent_id: str, event: str):
        if agent_id not in self.relationship_history:
            self.relationship_history[agent_id] = []
        self.relationship_history[agent_id].append(event)


@dataclass
class Information:
    info_id: str
    source_id: str
    content: str
    info_type: str
    is_true: bool = True
    spread_count: int = 0
    created_time: int = 0
    target_id: Optional[str] = None
    
    def spread(self):
        self.spread_count += 1


class InformationNetwork:
    def __init__(self):
        self.information_pool: Dict[str, Information] = {}
        self.agent_knowledge: Dict[str, Set[str]] = {}
        self.info_counter = 0
    
    def create_info(
        self, 
        source_id: str, 
        content: str, 
        info_type: str,
        is_true: bool = True,
        target_id: Optional[str] = None,
        timestamp: int = 0
    ) -> Information:
        self.info_counter += 1
        info_id = f"info_{self.info_counter}"
        
        info = Information(
            info_id=info_id,
            source_id=source_id,
            content=content,
            info_type=info_type,
            is_true=is_true,
            created_time=timestamp,
            target_id=target_id
        )
        
        self.information_pool[info_id] = info
        self._add_knowledge(source_id, info_id)
        
        return info
    
    def _add_knowledge(self, agent_id: str, info_id: str):
        if agent_id not in self.agent_knowledge:
            self.agent_knowledge[agent_id] = set()
        self.agent_knowledge[agent_id].add(info_id)
    
    def spread_info(self, info_id: str, from_agent: str, to_agent: str) -> bool:
        if info_id not in self.information_pool:
            return False
        
        info = self.information_pool[info_id]
        
        if to_agent in self.agent_knowledge and info_id in self.agent_knowledge[to_agent]:
            return False
        
        self._add_knowledge(to_agent, info_id)
        info.spread()
        
        return True
    
    def get_agent_knowledge(self, agent_id: str) -> List[Information]:
        if agent_id not in self.agent_knowledge:
            return []
        
        return [
            self.information_pool[info_id]
            for info_id in self.agent_knowledge[agent_id]
            if info_id in self.information_pool
        ]
    
    def get_info_about_agent(self, about_agent: str, known_to: str) -> List[Information]:
        knowledge = self.get_agent_knowledge(known_to)
        return [
            info for info in knowledge
            if info.target_id == about_agent or about_agent in info.content
        ]
