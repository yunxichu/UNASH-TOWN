"""
智能体模块 - 定义具有不同初始倾向的智能体
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
import random
import math


class AgentTendency(Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    RISK_TAKING = "risk_taking"
    RISK_AVERSE = "risk_averse"
    ALTRUISTIC = "altruistic"
    SELFISH = "selfish"
    STRATEGIC = "strategic"
    RANDOM = "random"


TENDENCY_TRAITS = {
    AgentTendency.AGGRESSIVE: {
        "aggression": 0.9,
        "cooperation": 0.2,
        "risk_tolerance": 0.8,
        "greed": 0.7,
        "trust": 0.3,
    },
    AgentTendency.CONSERVATIVE: {
        "aggression": 0.2,
        "cooperation": 0.5,
        "risk_tolerance": 0.1,
        "greed": 0.3,
        "trust": 0.6,
    },
    AgentTendency.COOPERATIVE: {
        "aggression": 0.1,
        "cooperation": 0.9,
        "risk_tolerance": 0.4,
        "greed": 0.2,
        "trust": 0.8,
    },
    AgentTendency.COMPETITIVE: {
        "aggression": 0.7,
        "cooperation": 0.1,
        "risk_tolerance": 0.6,
        "greed": 0.8,
        "trust": 0.2,
    },
    AgentTendency.RISK_TAKING: {
        "aggression": 0.5,
        "cooperation": 0.4,
        "risk_tolerance": 0.95,
        "greed": 0.6,
        "trust": 0.5,
    },
    AgentTendency.RISK_AVERSE: {
        "aggression": 0.3,
        "cooperation": 0.6,
        "risk_tolerance": 0.05,
        "greed": 0.4,
        "trust": 0.7,
    },
    AgentTendency.ALTRUISTIC: {
        "aggression": 0.1,
        "cooperation": 0.95,
        "risk_tolerance": 0.3,
        "greed": 0.05,
        "trust": 0.9,
    },
    AgentTendency.SELFISH: {
        "aggression": 0.6,
        "cooperation": 0.1,
        "risk_tolerance": 0.5,
        "greed": 0.95,
        "trust": 0.1,
    },
    AgentTendency.STRATEGIC: {
        "aggression": 0.4,
        "cooperation": 0.5,
        "risk_tolerance": 0.5,
        "greed": 0.5,
        "trust": 0.5,
    },
    AgentTendency.RANDOM: {
        "aggression": 0.5,
        "cooperation": 0.5,
        "risk_tolerance": 0.5,
        "greed": 0.5,
        "trust": 0.5,
    },
}


@dataclass
class AgentMemory:
    interactions: Dict[str, List[Dict]] = field(default_factory=dict)
    outcomes: List[Dict] = field(default_factory=list)
    
    def record_interaction(self, other_id: str, action: str, outcome: Dict):
        if other_id not in self.interactions:
            self.interactions[other_id] = []
        self.interactions[other_id].append({
            "action": action,
            "outcome": outcome,
            "timestamp": len(self.outcomes)
        })
        self.outcomes.append(outcome)
    
    def get_trust_for(self, other_id: str) -> float:
        if other_id not in self.interactions:
            return 0.5
        interactions = self.interactions[other_id]
        if not interactions:
            return 0.5
        positive = sum(1 for i in interactions if i["outcome"].get("beneficial", False))
        return positive / len(interactions)


@dataclass
class Agent:
    id: int
    name: str
    tendency: AgentTendency
    resources: float = 100.0
    traits: Dict[str, float] = field(default_factory=dict)
    memory: AgentMemory = field(default_factory=AgentMemory)
    mood: float = 0.5
    energy: float = 1.0
    
    def __post_init__(self):
        base_traits = TENDENCY_TRAITS[self.tendency].copy()
        for key, value in base_traits.items():
            noise = random.uniform(-0.1, 0.1)
            self.traits[key] = max(0.0, min(1.0, value + noise))
    
    def decide_action(self, opponent: 'Agent', game_state: Dict) -> str:
        if self.tendency == AgentTendency.RANDOM:
            return random.choice(["cooperate", "defect", "compromise"])
        
        trust = self.memory.get_trust_for(opponent.id)
        aggression = self.traits["aggression"]
        cooperation = self.traits["cooperation"]
        risk = self.traits["risk_tolerance"]
        greed = self.traits["greed"]
        
        if self.energy < 0.3:
            return "compromise"
        
        opponent_threat = opponent.traits.get("aggression", 0.5)
        
        cooperate_score = (
            cooperation * 0.4 +
            trust * 0.3 +
            (1 - aggression) * 0.2 +
            (1 - greed) * 0.1
        )
        
        defect_score = (
            aggression * 0.3 +
            greed * 0.3 +
            (1 - trust) * 0.2 +
            risk * 0.2
        )
        
        compromise_score = (
            (1 - abs(aggression - 0.5)) * 0.3 +
            (1 - abs(cooperation - 0.5)) * 0.3 +
            (1 - risk) * 0.2 +
            0.2
        )
        
        scores = {
            "cooperate": cooperate_score,
            "defect": defect_score,
            "compromise": compromise_score
        }
        
        max_score = max(scores.values())
        best_actions = [a for a, s in scores.items() if s == max_score]
        
        return random.choice(best_actions)
    
    def update_after_game(self, outcome: Dict, opponent: 'Agent'):
        resource_change = outcome.get("resource_change", 0)
        self.resources += resource_change
        
        beneficial = resource_change > 0
        self.memory.record_interaction(
            str(opponent.id),
            outcome.get("my_action", "unknown"),
            {"beneficial": beneficial, "resource_change": resource_change}
        )
        
        if beneficial:
            self.mood = min(1.0, self.mood + 0.1)
        else:
            self.mood = max(0.0, self.mood - 0.1)
        
        self.energy = max(0.0, self.energy - 0.1)
    
    def rest(self):
        self.energy = min(1.0, self.energy + 0.3)
        self.mood = 0.5 + (self.resources - 100) / 200 * 0.5
        self.mood = max(0.0, min(1.0, self.mood))
    
    def socialize(self, other: 'Agent') -> Dict:
        trust_gain = random.uniform(0.05, 0.15) * (1 - abs(self.traits["aggression"] - other.traits["aggression"]))
        
        if str(other.id) not in self.memory.interactions:
            self.memory.interactions[str(other.id)] = []
        
        self.mood = min(1.0, self.mood + 0.05)
        
        return {
            "type": "socialize",
            "partner": other.name,
            "trust_change": trust_gain
        }
    
    def __repr__(self):
        return f"Agent({self.id}, {self.name}, {self.tendency.value}, resources={self.resources:.1f})"


def create_diverse_agents(count: int = 10) -> List[Agent]:
    tendencies = list(AgentTendency)
    
    names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve",
        "Frank", "Grace", "Henry", "Ivy", "Jack",
        "Kate", "Leo", "Mia", "Noah", "Olivia"
    ]
    
    agents = []
    for i in range(count):
        tendency = tendencies[i % len(tendencies)]
        name = names[i % len(names)]
        agent = Agent(
            id=i,
            name=f"{name}_{i}",
            tendency=tendency
        )
        agents.append(agent)
    
    return agents
