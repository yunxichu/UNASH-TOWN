"""
博弈系统模块 - 实现零和博弈逻辑
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import random
import math

from .agent import Agent
from .environment import EnvironmentState


@dataclass
class GameResult:
    agent1_id: int
    agent2_id: int
    agent1_action: str
    agent2_action: str
    agent1_payoff: float
    agent2_payoff: float
    is_zero_sum: bool = True


class GameEngine:
    PAYOFF_MATRIX = {
        ("cooperate", "cooperate"): (3, 3),
        ("cooperate", "defect"): (-1, 5),
        ("defect", "cooperate"): (5, -1),
        ("defect", "defect"): (-2, -2),
        ("cooperate", "compromise"): (2, 2),
        ("compromise", "cooperate"): (2, 2),
        ("defect", "compromise"): (3, -1),
        ("compromise", "defect"): (-1, 3),
        ("compromise", "compromise"): (1, 1),
    }
    
    def __init__(self, zero_sum_mode: bool = True):
        self.zero_sum_mode = zero_sum_mode
        self.game_history: List[GameResult] = []
        self.total_games = 0
    
    def play_game(
        self, 
        agent1: Agent, 
        agent2: Agent, 
        env_state: EnvironmentState
    ) -> GameResult:
        action1 = agent1.decide_action(agent2, self._get_game_state(agent1, agent2, env_state))
        action2 = agent2.decide_action(agent1, self._get_game_state(agent2, agent1, env_state))
        
        base_payoff1, base_payoff2 = self.PAYOFF_MATRIX.get(
            (action1, action2), (0, 0)
        )
        
        payoff1, payoff2 = self._apply_environment_modifiers(
            base_payoff1, base_payoff2, env_state, agent1, agent2
        )
        
        if self.zero_sum_mode:
            total = payoff1 + payoff2
            if total != 0:
                adjustment = total / 2
                payoff1 -= adjustment
                payoff2 -= adjustment
        
        result = GameResult(
            agent1_id=agent1.id,
            agent2_id=agent2.id,
            agent1_action=action1,
            agent2_action=action2,
            agent1_payoff=payoff1,
            agent2_payoff=payoff2,
            is_zero_sum=self.zero_sum_mode
        )
        
        self.game_history.append(result)
        self.total_games += 1
        
        outcome1 = {
            "resource_change": payoff1,
            "my_action": action1,
            "opponent_action": action2,
            "beneficial": payoff1 > 0
        }
        outcome2 = {
            "resource_change": payoff2,
            "my_action": action2,
            "opponent_action": action1,
            "beneficial": payoff2 > 0
        }
        
        agent1.update_after_game(outcome1, agent2)
        agent2.update_after_game(outcome2, agent1)
        
        return result
    
    def _get_game_state(self, agent: Agent, opponent: Agent, env_state: EnvironmentState) -> Dict:
        return {
            "my_resources": agent.resources,
            "my_mood": agent.mood,
            "my_energy": agent.energy,
            "opponent_resources": opponent.resources,
            "opponent_tendency": opponent.tendency.value,
            "trust_in_opponent": agent.memory.get_trust_for(str(opponent.id)),
            "weather": env_state.weather.value,
            "market": env_state.market.value,
            "event": env_state.event.value,
            "resource_abundance": env_state.resource_abundance,
            "social_tension": env_state.social_tension,
        }
    
    def _apply_environment_modifiers(
        self,
        payoff1: float,
        payoff2: float,
        env_state: EnvironmentState,
        agent1: Agent,
        agent2: Agent
    ) -> Tuple[float, float]:
        modifiers = env_state.get_modifiers()
        
        resource_mult = modifiers.get("resource_multiplier", 1.0)
        resource_abundance = modifiers.get("resource_abundance", 1.0)
        luck_factor = modifiers.get("luck_factor", 1.0)
        
        payoff1 *= resource_mult * resource_abundance * luck_factor
        payoff2 *= resource_mult * resource_abundance * luck_factor
        
        if env_state.weather.value in ["rainy", "stormy"]:
            agent1.energy *= 0.95
            agent2.energy *= 0.95
        
        if env_state.event.value == "festival":
            if payoff1 > 0:
                payoff1 *= 1.1
            if payoff2 > 0:
                payoff2 *= 1.1
        
        if env_state.event.value == "disaster":
            payoff1 *= 0.9
            payoff2 *= 0.9
        
        payoff1 = round(payoff1, 2)
        payoff2 = round(payoff2, 2)
        
        return payoff1, payoff2
    
    def run_tournament_round(
        self, 
        agents: List[Agent], 
        env_state: EnvironmentState
    ) -> List[GameResult]:
        results = []
        n = len(agents)
        
        for i in range(n):
            for j in range(i + 1, n):
                if agents[i].energy > 0.1 and agents[j].energy > 0.1:
                    result = self.play_game(agents[i], agents[j], env_state)
                    results.append(result)
        
        return results
    
    def run_pairing_round(
        self,
        agents: List[Agent],
        env_state: EnvironmentState,
        pairings: Optional[List[Tuple[int, int]]] = None
    ) -> List[GameResult]:
        results = []
        
        if pairings is None:
            shuffled = agents.copy()
            random.shuffle(shuffled)
            pairings = [(shuffled[i].id, shuffled[i+1].id) for i in range(0, len(shuffled)-1, 2)]
        
        agent_dict = {a.id: a for a in agents}
        
        for id1, id2 in pairings:
            if id1 in agent_dict and id2 in agent_dict:
                a1, a2 = agent_dict[id1], agent_dict[id2]
                if a1.energy > 0.1 and a2.energy > 0.1:
                    result = self.play_game(a1, a2, env_state)
                    results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict:
        if not self.game_history:
            return {"total_games": 0}
        
        total_payoff = sum(r.agent1_payoff + r.agent2_payoff for r in self.game_history)
        avg_payoff = total_payoff / (2 * len(self.game_history))
        
        cooperate_count = sum(1 for r in self.game_history 
                             if r.agent1_action == "cooperate" or r.agent2_action == "cooperate")
        defect_count = sum(1 for r in self.game_history 
                          if r.agent1_action == "defect" or r.agent2_action == "defect")
        compromise_count = sum(1 for r in self.game_history 
                              if r.agent1_action == "compromise" or r.agent2_action == "compromise")
        
        return {
            "total_games": len(self.game_history),
            "average_payoff": round(avg_payoff, 2),
            "cooperation_rate": round(cooperate_count / (2 * len(self.game_history)), 2),
            "defection_rate": round(defect_count / (2 * len(self.game_history)), 2),
            "compromise_rate": round(compromise_count / (2 * len(self.game_history)), 2),
        }
    
    def __repr__(self):
        return f"GameEngine(games_played={self.total_games}, zero_sum={self.zero_sum_mode})"
