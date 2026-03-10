"""
永不纳什小镇 - 博弈系统
囚徒困境、零和博弈、联盟博弈
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import random


class GameAction(Enum):
    COOPERATE = "cooperate"
    DEFECT = "defect"
    COMPROMISE = "compromise"


class GameOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    MUTUAL_WIN = "mutual_win"
    MUTUAL_LOSE = "mutual_lose"


@dataclass
class GameResult:
    player1_id: str
    player2_id: str
    player1_action: GameAction
    player2_action: GameAction
    player1_payoff: float
    player2_payoff: float
    player1_outcome: GameOutcome
    player2_outcome: GameOutcome
    timestamp: int
    
    def is_betrayal(self) -> bool:
        return (
            (self.player1_action == GameAction.COOPERATE and self.player2_action == GameAction.DEFECT) or
            (self.player2_action == GameAction.COOPERATE and self.player1_action == GameAction.DEFECT)
        )
    
    def is_mutual_cooperation(self) -> bool:
        return (
            self.player1_action == GameAction.COOPERATE and 
            self.player2_action == GameAction.COOPERATE
        )
    
    def is_mutual_defection(self) -> bool:
        return (
            self.player1_action == GameAction.DEFECT and 
            self.player2_action == GameAction.DEFECT
        )


class PayoffMatrix:
    PRISONERS_DILEMMA = {
        (GameAction.COOPERATE, GameAction.COOPERATE): (3, 3),
        (GameAction.COOPERATE, GameAction.DEFECT): (0, 5),
        (GameAction.DEFECT, GameAction.COOPERATE): (5, 0),
        (GameAction.DEFECT, GameAction.DEFECT): (1, 1),
        (GameAction.COOPERATE, GameAction.COMPROMISE): (2, 2),
        (GameAction.COMPROMISE, GameAction.COOPERATE): (2, 2),
        (GameAction.DEFECT, GameAction.COMPROMISE): (4, -1),
        (GameAction.COMPROMISE, GameAction.DEFECT): (-1, 4),
        (GameAction.COMPROMISE, GameAction.COMPROMISE): (1, 1),
    }


class GameStrategy:
    def __init__(self, personality: Dict, memory, social_graph):
        self.personality = personality
        self.memory = memory
        self.social_graph = social_graph
    
    def decide(self, opponent_id: str, context: Dict) -> GameAction:
        trust = self.social_graph.get_trust(opponent_id)
        risk = self.personality.get("risk", 0.5)
        greed = self.personality.get("greed", 0.5)
        revenge = self.personality.get("revenge", 0.5)
        
        betrayals = self.memory.get_recent_betrayals(opponent_id) if hasattr(self.memory, 'get_recent_betrayals') else 0
        if betrayals > 0 and random.random() < revenge:
            return GameAction.DEFECT
        
        if self.social_graph.is_enemy(opponent_id):
            if random.random() < 0.7:
                return GameAction.DEFECT
        
        if self.social_graph.is_ally(opponent_id):
            if random.random() < 0.8:
                return GameAction.COOPERATE
        
        if trust > 70 and random.random() < 0.7:
            return GameAction.COOPERATE
        elif trust < 30 and random.random() < 0.6:
            return GameAction.DEFECT
        
        if risk > 0.7 and random.random() < 0.5:
            return GameAction.DEFECT
        
        if greed > 0.7 and random.random() < 0.4:
            return GameAction.DEFECT
        
        return random.choice([GameAction.COOPERATE, GameAction.COMPROMISE])
    
    def update_after_game(self, result: GameResult, my_id: str):
        opponent_id = result.player2_id if result.player1_id == my_id else result.player1_id
        my_action = result.player1_action if result.player1_id == my_id else result.player2_action
        opponent_action = result.player2_action if result.player1_id == my_id else result.player1_action
        
        if opponent_action == GameAction.DEFECT and my_action == GameAction.COOPERATE:
            if hasattr(self.memory, 'record_betrayal'):
                self.memory.record_betrayal(opponent_id)
            self.social_graph.add_enemy(opponent_id)
        
        if opponent_action == GameAction.COOPERATE:
            if hasattr(self.memory, 'record_cooperation'):
                self.memory.record_cooperation(opponent_id)
            if random.random() < 0.3:
                self.social_graph.add_friend(opponent_id)


class GameEngine:
    def __init__(self, payoff_matrix: Dict = None):
        self.payoff_matrix = payoff_matrix or PayoffMatrix.PRISONERS_DILEMMA
        self.game_history: List[GameResult] = []
        self.game_counter = 0
    
    def play_game(
        self,
        player1_id: str,
        player2_id: str,
        action1: GameAction,
        action2: GameAction,
        timestamp: int,
        modifiers: Dict = None
    ) -> GameResult:
        base_payoff = self.payoff_matrix.get(
            (action1, action2),
            (0, 0)
        )
        
        payoff1, payoff2 = base_payoff
        
        if modifiers:
            multiplier = modifiers.get("multiplier", 1.0)
            payoff1 *= multiplier
            payoff2 *= multiplier
        
        outcome1 = self._determine_outcome(payoff1, payoff2)
        outcome2 = self._determine_outcome(payoff2, payoff1)
        
        result = GameResult(
            player1_id=player1_id,
            player2_id=player2_id,
            player1_action=action1,
            player2_action=action2,
            player1_payoff=payoff1,
            player2_payoff=payoff2,
            player1_outcome=outcome1,
            player2_outcome=outcome2,
            timestamp=timestamp
        )
        
        self.game_history.append(result)
        self.game_counter += 1
        
        return result
    
    def _determine_outcome(self, my_payoff: float, opponent_payoff: float) -> GameOutcome:
        if my_payoff > opponent_payoff:
            return GameOutcome.WIN
        elif my_payoff < opponent_payoff:
            return GameOutcome.LOSE
        elif my_payoff > 0:
            return GameOutcome.MUTUAL_WIN
        elif my_payoff < 0:
            return GameOutcome.MUTUAL_LOSE
        else:
            return GameOutcome.DRAW
    
    def get_statistics(self) -> Dict:
        if not self.game_history:
            return {"total_games": 0}
        
        cooperation_count = sum(
            1 for g in self.game_history 
            if g.player1_action == GameAction.COOPERATE or g.player2_action == GameAction.COOPERATE
        )
        defection_count = sum(
            1 for g in self.game_history 
            if g.player1_action == GameAction.DEFECT or g.player2_action == GameAction.DEFECT
        )
        betrayal_count = sum(1 for g in self.game_history if g.is_betrayal())
        
        return {
            "total_games": len(self.game_history),
            "cooperation_rate": cooperation_count / (2 * len(self.game_history)),
            "defection_rate": defection_count / (2 * len(self.game_history)),
            "betrayal_count": betrayal_count,
            "mutual_cooperation": sum(1 for g in self.game_history if g.is_mutual_cooperation()),
            "mutual_defection": sum(1 for g in self.game_history if g.is_mutual_defection()),
        }
