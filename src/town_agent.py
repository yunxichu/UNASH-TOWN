"""
永不纳什小镇 - 智能体完整生活系统
整合睡眠、社交、交易、精力于一体的智能体
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import random
import time

from .agent_interface import (
    BaseAgent, AgentInfo, AgentStatus, AgentType,
    TradingContext, TradingDecision
)
from .life_system import (
    PhysicalState, EmotionalState, SocialProfile, Relationship,
    ActivityType, MoodType, RelationshipType
)
from .energy_system import EnergySystem, EnergyLevel


class TownAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        name: str,
        initial_capital: float = 10000.0,
        bedtime: int = 22,
        wake_time: int = 6
    ):
        super().__init__(agent_id, name, initial_capital)
        
        self.energy = EnergySystem()
        self.emotional = EmotionalState()
        self.social = SocialProfile()
        
        self.bedtime = bedtime
        self.wake_time = wake_time
        self._is_sleeping = False
        self._current_activity = ActivityType.RESTING
        self._current_location = "家"
        
        self.daily_schedule: List[Dict] = []
        self.interaction_log: List[Dict] = []
        
        self.hours_slept_last_night: float = 8.0
    
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
        
        result = self.energy.sleep(sleep_hours)
        
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
    
    def update_hour(self, current_hour: int):
        if self.should_sleep(current_hour) and not self._is_sleeping:
            self.start_sleeping()
        elif not self.should_sleep(current_hour) and self._is_sleeping:
            self.wake_up()
            self.energy.new_day_reset()
    
    def decide(self, context: TradingContext) -> TradingDecision:
        if self._is_sleeping:
            return TradingDecision.no_action()
        
        if not self.can_trade():
            return TradingDecision.no_action()
        
        if not self.energy.spend_energy(self.energy.COST_TRADE, "trade"):
            return TradingDecision.no_action()
        
        return self._make_trading_decision(context)
    
    def _make_trading_decision(self, context: TradingContext) -> TradingDecision:
        market = context.market_data
        technical = context.technical
        state = context.agent_state
        
        skill_modifier = self.energy.get_trading_skill_modifier()
        confidence_modifier = (self.emotional.confidence / 100) * skill_modifier
        stress_modifier = 1 - (self.emotional.stress / 200)
        
        effective_confidence = confidence_modifier * stress_modifier
        
        if technical.rsi < 30 and random.random() < 0.5 * effective_confidence:
            quantity = int(state.capital * 0.1 * skill_modifier / market.price)
            if quantity > 0:
                return TradingDecision.buy(
                    price=market.price * 0.99,
                    quantity=quantity,
                    reasoning=f"RSI超卖，精力充沛(技能:{skill_modifier*100:.0f}%)"
                )
        
        elif technical.rsi > 70 and state.position > 0 and random.random() < 0.5 * effective_confidence:
            quantity = int(state.position * 0.5 * skill_modifier)
            if quantity > 0:
                return TradingDecision.sell(
                    price=market.price * 1.01,
                    quantity=quantity,
                    reasoning=f"RSI超买，获利了结(技能:{skill_modifier*100:.0f}%)"
                )
        
        if random.random() < 0.1 * effective_confidence:
            if random.random() < 0.5:
                quantity = int(state.capital * 0.05 * skill_modifier / market.price)
                if quantity > 0:
                    return TradingDecision.buy(
                        price=market.price,
                        quantity=quantity,
                        reasoning="随机买入"
                    )
        
        return TradingDecision.no_action()
    
    def socialize_with(self, other: 'TownAgent', social_engine) -> Dict:
        if not self.can_socialize() or not other.can_socialize():
            return {"success": False, "reason": "精力不足或已达社交上限"}
        
        if not self.energy.spend_energy(self.energy.COST_SOCIALIZE, "socialize"):
            return {"success": False, "reason": "精力耗尽"}
        
        if not other.energy.spend_energy(other.energy.COST_SOCIALIZE, "socialize"):
            return {"success": False, "reason": "对方精力耗尽"}
        
        relationship = self.social.meet_agent(other.agent_id)
        other_relationship = other.social.meet_agent(self.agent_id)
        
        my_skill = self.energy.get_social_skill_modifier()
        other_skill = other.energy.get_social_skill_modifier()
        
        greeting = social_engine.generate_greeting(
            self.name, other.name, relationship
        )
        
        topic = social_engine.generate_topic(
            self.social.interests,
            market_event=None
        )
        
        response = social_engine.generate_response(
            other.name, greeting, other_relationship, other.emotional.mood
        )
        
        interaction_quality = (
            self.social.personality_traits["agreeableness"] * my_skill +
            other.social.personality_traits["agreeableness"] * other_skill
        ) / 2
        
        common_interests = set(self.social.interests) & set(other.social.interests)
        if common_interests:
            interaction_quality += 0.2
        
        relationship.interact(interaction_quality)
        other_relationship.interact(interaction_quality)
        
        self.emotional.socialize_effect(interaction_quality)
        other.emotional.socialize_effect(interaction_quality)
        
        self.social.update_relationships()
        other.social.update_relationships()
        
        interaction_record = {
            "type": "socialize",
            "partner": other.name,
            "greeting": greeting,
            "topic": topic,
            "response": response,
            "quality": interaction_quality,
            "my_energy": self.energy.current_energy,
            "timestamp": time.time()
        }
        
        self.interaction_log.append(interaction_record)
        other.interaction_log.append({
            **interaction_record,
            "partner": self.name,
        })
        
        return {
            "success": True,
            "greeting": greeting,
            "topic": topic,
            "response": response,
            "quality": interaction_quality,
            "relationship": relationship.relationship_type.value,
            "my_energy_left": self.energy.current_energy,
            "my_social_count": f"{self.energy.social_interactions_today}/{self.energy.MAX_SOCIAL_PER_DAY}",
        }
    
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
            "friends": len(self.social.friends),
            "capital": round(self.capital, 2),
            "position": self.position,
            "total_value": round(self.total_value, 2),
            "sleep_debt": energy_status["sleep_debt"],
            "hours_slept": self.hours_slept_last_night,
        }
    
    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            agent_type=AgentType.LOCAL,
            status=AgentStatus.INACTIVE if self._is_sleeping else AgentStatus.ACTIVE,
            capabilities=["trading", "socializing"],
            metadata={
                "interests": self.social.interests,
                "personality": self.social.personality_traits,
                "bedtime": self.bedtime,
                "wake_time": self.wake_time,
                "energy_level": self.energy.get_energy_level().value,
            }
        )
    
    def on_trade_executed(self, trade_info: Dict):
        super().on_trade_executed(trade_info)
        
        profit = trade_info.get("type") == "sell"
        amount = abs(trade_info.get("price", 0) * trade_info.get("quantity", 0) - 
                    self.avg_cost * trade_info.get("quantity", 0))
        self.emotional.trading_effect(profit, amount / 100)
    
    def on_market_event(self, event: str, data: Dict):
        if event == "market_crash":
            self.emotional.stress = min(100, self.emotional.stress + 20)
            self.emotional.confidence = max(0, self.emotional.confidence - 10)
        elif event == "market_boom":
            self.emotional.happiness = min(100, self.emotional.happiness + 10)
            self.emotional.confidence = min(100, self.emotional.confidence + 5)
        
        self.emotional.update_mood()


def create_town_agents(num_agents: int = 10, initial_capital: float = 10000.0) -> List[TownAgent]:
    names = [
        "小明", "小红", "小华", "小丽", "小强",
        "小芳", "小伟", "小娟", "小军", "小燕",
        "小刚", "小梅", "小勇", "小英", "小杰"
    ]
    
    agents = []
    for i in range(num_agents):
        name = names[i % len(names)]
        bedtime = random.randint(21, 23)
        wake_time = random.randint(5, 7)
        
        agent = TownAgent(
            agent_id=f"town_agent_{i}",
            name=f"{name}_{i}",
            initial_capital=initial_capital,
            bedtime=bedtime,
            wake_time=wake_time
        )
        agents.append(agent)
    
    return agents
