"""
永不纳什小镇 - 完整博弈智能体
整合人格、记忆、学习、声誉、联盟、信息传播
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import random

from .personality import (
    Personality, AgentArchetype, AgentMemory, MemoryRecord,
    Reputation, SocialGraph, Alliance, Information, InformationNetwork,
    ARCHETYPE_PROFILES
)
from .energy_system import EnergySystem
from .life_system import EmotionalState, MoodType, SocialProfile, ActivityType
from .game_theory import GameAction, GameResult, GameStrategy


class NashAgent:
    def __init__(
        self,
        agent_id: str,
        name: str,
        archetype: AgentArchetype,
        initial_capital: float = 10000.0,
        bedtime: int = 22,
        wake_time: int = 6
    ):
        self.agent_id = agent_id
        self.name = name
        self.archetype = archetype
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.bedtime = bedtime
        self.wake_time = wake_time
        
        self.personality = Personality(archetype=archetype)
        self.memory = AgentMemory()
        self.reputation = Reputation()
        self.social_graph = SocialGraph()
        self.information_network = InformationNetwork()
        
        self.energy = EnergySystem()
        self.emotional = EmotionalState()
        self.social = SocialProfile()
        
        self.strategy = GameStrategy(
            personality={
                "risk": self.personality.risk,
                "trust": self.personality.trust,
                "greed": self.personality.greed,
                "revenge": self.personality.revenge,
            },
            memory=self.memory,
            social_graph=self.social_graph
        )
        
        self.promises_made: Dict[str, Dict] = {}
        self.promises_kept: Dict[str, bool] = {}
        
        self._is_sleeping = False
        self._current_activity = ActivityType.RESTING
        self._current_location = "家"
        self.hours_slept_last_night: float = 8.0
    
    @property
    def total_value(self) -> float:
        return self.capital
    
    @property
    def return_rate(self) -> float:
        return (self.capital - self.initial_capital) / self.initial_capital
    
    def should_sleep(self, current_hour: int) -> bool:
        if self.bedtime > self.wake_time:
            return current_hour >= self.bedtime or current_hour < self.wake_time
        else:
            return self.bedtime <= current_hour < self.wake_time
    
    def start_sleeping(self):
        self._is_sleeping = True
        self._current_activity = ActivityType.SLEEPING
        self._current_location = "家"
    
    def wake_up(self):
        self._is_sleeping = False
        self._current_activity = ActivityType.RESTING
        
        sleep_hours = self._calculate_sleep_hours()
        self.hours_slept_last_night = sleep_hours
        
        self.energy.sleep(sleep_hours)
        
        if sleep_hours >= 8:
            self.emotional.mood = MoodType.REFRESHED
        elif sleep_hours >= 6:
            self.emotional.mood = MoodType.NEUTRAL
        else:
            self.emotional.mood = MoodType.TIRED
            self.emotional.stress = min(100, self.emotional.stress + 10)
    
    def _calculate_sleep_hours(self) -> float:
        if self.bedtime > self.wake_time:
            return 24 - self.bedtime + self.wake_time
        else:
            return self.wake_time - self.bedtime
    
    def is_sleeping(self) -> bool:
        return self._is_sleeping
    
    def can_trade(self) -> bool:
        return (
            not self._is_sleeping and 
            self.energy.can_trade() and
            self.emotional.stress < 80
        )
    
    def can_socialize(self) -> bool:
        return (
            not self._is_sleeping and 
            self.energy.can_socialize()
        )
    
    def get_energy_status(self) -> Dict:
        return self.energy.get_status()
    
    def decide_game_action(self, opponent_id: str, context: Dict) -> GameAction:
        return self.strategy.decide(opponent_id, context)
    
    def update_after_game(self, result: GameResult, my_id: str):
        self.strategy.update_after_game(result, my_id)
        
        my_payoff = result.player1_payoff if result.player1_id == my_id else result.player2_payoff
        
        if my_payoff > 0:
            self.capital += my_payoff
            self.emotional.trading_effect(True, my_payoff)
        else:
            self.capital += my_payoff
            self.emotional.trading_effect(False, abs(my_payoff))
        
        if result.is_betrayal():
            opponent_id = result.player2_id if result.player1_id == my_id else result.player1_id
            self.memory.record_event(MemoryRecord(
                agent_id=opponent_id,
                event_type="betrayal",
                outcome="negative",
                timestamp=result.timestamp,
                importance=0.9
            ))
    
    def share_information(self, info: Information, target_id: str) -> Dict:
        if not self.can_socialize():
            return {"success": False, "reason": "精力不足"}
        
        if not self.energy.spend_energy(self.energy.COST_SOCIALIZE, "socialize"):
            return {"success": False, "reason": "精力耗尽"}
        
        is_truthful = random.random() < self.personality.trust
        
        if self.archetype == AgentArchetype.MANIPULATOR:
            is_truthful = random.random() < 0.3
        
        return {
            "success": True,
            "info_id": info.info_id,
            "content": info.content,
            "is_truthful": is_truthful,
            "source": self.name,
            "target": target_id,
        }
    
    def propose_alliance(self, target_id: str, day: int) -> Optional[Alliance]:
        if not self.can_socialize():
            return None
        
        trust = self.social_graph.get_trust(target_id)
        if trust < 40:
            return None
        
        if self.social_graph.is_enemy(target_id):
            return None
        
        alliance = Alliance(
            members={self.agent_id, target_id},
            formed_day=day,
            strength=trust / 100
        )
        
        self.social_graph.alliances.append(alliance)
        self.social_graph.add_ally(target_id)
        
        return alliance
    
    def break_alliance(self, alliance: Alliance):
        alliance.remove_member(self.agent_id)
        
        for member in alliance.members:
            if member != self.agent_id:
                self.social_graph.record_relationship_event(
                    member, "alliance_broken"
                )
    
    def make_promise(self, target_id: str, promise_type: str, details: Dict) -> str:
        promise_id = f"promise_{len(self.promises_made)}"
        self.promises_made[promise_id] = {
            "target": target_id,
            "type": promise_type,
            "details": details,
            "kept": None
        }
        return promise_id
    
    def keep_promise(self, promise_id: str) -> bool:
        if promise_id not in self.promises_made:
            return False
        
        self.promises_made[promise_id]["kept"] = True
        self.promises_kept[promise_id] = True
        self.reputation.update_cooperation()
        
        return True
    
    def break_promise(self, promise_id: str) -> bool:
        if promise_id not in self.promises_made:
            return False
        
        self.promises_made[promise_id]["kept"] = False
        self.promises_kept[promise_id] = False
        
        target_id = self.promises_made[promise_id]["target"]
        self.social_graph.add_enemy(target_id)
        self.reputation.update_betrayal()
        
        return True
    
    def learn_from_experience(self):
        learning_rate = self.personality.learning
        
        recent_results = self.memory.records[-10:] if self.memory.records else []
        
        if not recent_results:
            return
        
        betrayals = sum(1 for r in recent_results if r.event_type == "betrayal")
        cooperations = sum(1 for r in recent_results if r.event_type == "cooperation")
        
        if betrayals > cooperations:
            self.personality.adjust("trust", -0.05 * learning_rate)
            self.personality.adjust("revenge", 0.03 * learning_rate)
        else:
            self.personality.adjust("trust", 0.03 * learning_rate)
        
        if self.capital < self.initial_capital * 0.8:
            self.personality.adjust("risk", -0.05 * learning_rate)
        elif self.capital > self.initial_capital * 1.2:
            self.personality.adjust("greed", 0.03 * learning_rate)
    
    def rest(self):
        if self.energy.spend_energy(self.energy.COST_REST, "rest"):
            self._current_activity = ActivityType.RESTING
            self.energy.recover_energy(10)
    
    def go_to(self, location: str):
        if location != self._current_location:
            self.energy.spend_energy(self.energy.COST_WALK, "walk")
        self._current_location = location
    
    def get_status(self) -> Dict:
        energy_status = self.energy.get_status()
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "archetype": self.archetype.value,
            "description": self.personality.get_description(),
            "is_sleeping": self._is_sleeping,
            "activity": self._current_activity.value,
            "location": self._current_location,
            "energy": energy_status["current_energy"],
            "max_energy": energy_status["max_energy"],
            "energy_level": energy_status["energy_level"],
            "trading_skill": energy_status["trading_skill"],
            "social_count": energy_status["social_today"],
            "trade_count": energy_status["trades_today"],
            "mood": self.emotional.mood.value,
            "happiness": round(self.emotional.happiness, 1),
            "stress": round(self.emotional.stress, 1),
            "friends": len(self.social_graph.friends),
            "enemies": len(self.social_graph.enemies),
            "allies": len(self.social_graph.allies),
            "reputation": self.reputation.get_reputation_level(),
            "trust_score": round(self.reputation.trust_score, 1),
            "capital": round(self.capital, 2),
            "total_value": round(self.total_value, 2),
            "return_rate": f"{self.return_rate*100:.1f}%",
            "sleep_debt": round(self.energy.sleep_debt, 1),
            "hours_slept": round(self.hours_slept_last_night, 1),
        }


def create_nash_agents(num_agents: int = 10, initial_capital: float = 10000.0) -> List[NashAgent]:
    archetypes = list(AgentArchetype)
    
    names = [
        "小明", "小红", "小华", "小丽", "小强",
        "小芳", "小伟", "小娟", "小军", "小燕",
    ]
    
    agents = []
    for i in range(num_agents):
        archetype = archetypes[i % len(archetypes)]
        name = names[i % len(names)]
        bedtime = random.randint(21, 23)
        wake_time = random.randint(5, 7)
        
        agent = NashAgent(
            agent_id=f"nash_agent_{i}",
            name=f"{name}_{i}",
            archetype=archetype,
            initial_capital=initial_capital,
            bedtime=bedtime,
            wake_time=wake_time
        )
        agents.append(agent)
    
    return agents
