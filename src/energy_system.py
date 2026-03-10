"""
永不纳什小镇 - 精力系统
完整的精力管理机制
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class EnergyLevel(Enum):
    EXHAUSTED = "exhausted"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    FULL = "full"


@dataclass
class EnergySystem:
    MAX_ENERGY = 100.0
    MIN_ENERGY = 0.0
    FULL_SLEEP_HOURS = 8.0
    
    current_energy: float = 100.0
    max_energy: float = 100.0
    sleep_debt: float = 0.0
    hours_slept_last_night: float = 8.0
    consecutive_poor_sleep: int = 0
    
    social_interactions_today: int = 0
    trades_today: int = 0
    energy_spent_today: float = 0.0
    
    COST_SOCIALIZE = 8.0
    COST_TRADE = 12.0
    COST_WALK = 3.0
    COST_THINK = 5.0
    COST_REST = -10.0
    
    MAX_SOCIAL_PER_DAY = 15
    MAX_TRADES_PER_DAY = 10
    
    def get_energy_level(self) -> EnergyLevel:
        ratio = self.current_energy / self.max_energy
        if ratio < 0.2:
            return EnergyLevel.EXHAUSTED
        elif ratio < 0.4:
            return EnergyLevel.LOW
        elif ratio < 0.7:
            return EnergyLevel.MODERATE
        elif ratio < 0.9:
            return EnergyLevel.HIGH
        else:
            return EnergyLevel.FULL
    
    def can_socialize(self) -> bool:
        return (
            self.current_energy >= self.COST_SOCIALIZE and
            self.social_interactions_today < self.MAX_SOCIAL_PER_DAY
        )
    
    def can_trade(self) -> bool:
        return (
            self.current_energy >= self.COST_TRADE and
            self.trades_today < self.MAX_TRADES_PER_DAY
        )
    
    def spend_energy(self, amount: float, activity: str = "general") -> bool:
        if self.current_energy < amount:
            return False
        
        self.current_energy = max(self.MIN_ENERGY, self.current_energy - amount)
        self.energy_spent_today += amount
        
        if activity == "socialize":
            self.social_interactions_today += 1
        elif activity == "trade":
            self.trades_today += 1
        
        return True
    
    def recover_energy(self, amount: float):
        self.current_energy = min(self.max_energy, self.current_energy + amount)
    
    def sleep(self, hours: float) -> Dict:
        self.hours_slept_last_night = hours
        
        sleep_quality = min(1.0, hours / self.FULL_SLEEP_HOURS)
        
        base_recovery = hours * 12.5
        quality_bonus = sleep_quality * 20
        
        if hours >= self.FULL_SLEEP_HOURS:
            self.max_energy = self.MAX_ENERGY
            self.sleep_debt = 0
            self.consecutive_poor_sleep = 0
        else:
            deficit = self.FULL_SLEEP_HOURS - hours
            self.sleep_debt += deficit
            
            if hours < 6:
                self.consecutive_poor_sleep += 1
                max_energy_penalty = min(30, self.consecutive_poor_sleep * 10)
                self.max_energy = self.MAX_ENERGY - max_energy_penalty
            else:
                self.consecutive_poor_sleep = max(0, self.consecutive_poor_sleep - 1)
        
        recovery = base_recovery + quality_bonus
        self.current_energy = min(self.max_energy, recovery)
        
        return {
            "hours_slept": hours,
            "sleep_quality": sleep_quality,
            "energy_recovered": recovery,
            "max_energy": self.max_energy,
            "sleep_debt": self.sleep_debt,
        }
    
    def new_day_reset(self):
        self.social_interactions_today = 0
        self.trades_today = 0
        self.energy_spent_today = 0.0
    
    def get_trading_skill_modifier(self) -> float:
        level = self.get_energy_level()
        modifiers = {
            EnergyLevel.FULL: 1.0,
            EnergyLevel.HIGH: 0.9,
            EnergyLevel.MODERATE: 0.7,
            EnergyLevel.LOW: 0.4,
            EnergyLevel.EXHAUSTED: 0.1,
        }
        return modifiers.get(level, 0.5)
    
    def get_social_skill_modifier(self) -> float:
        level = self.get_energy_level()
        modifiers = {
            EnergyLevel.FULL: 1.0,
            EnergyLevel.HIGH: 0.95,
            EnergyLevel.MODERATE: 0.8,
            EnergyLevel.LOW: 0.5,
            EnergyLevel.EXHAUSTED: 0.2,
        }
        return modifiers.get(level, 0.5)
    
    def get_status(self) -> Dict:
        return {
            "current_energy": round(self.current_energy, 1),
            "max_energy": round(self.max_energy, 1),
            "energy_level": self.get_energy_level().value,
            "sleep_debt": round(self.sleep_debt, 1),
            "hours_slept_last_night": self.hours_slept_last_night,
            "social_today": f"{self.social_interactions_today}/{self.MAX_SOCIAL_PER_DAY}",
            "trades_today": f"{self.trades_today}/{self.MAX_TRADES_PER_DAY}",
            "trading_skill": f"{self.get_trading_skill_modifier()*100:.0f}%",
            "consecutive_poor_sleep": self.consecutive_poor_sleep,
        }


@dataclass
class DailySchedule:
    wake_time: int = 6
    sleep_time: int = 22
    
    planned_sleep_hours: float = 8.0
    actual_sleep_hours: float = 8.0
    
    activities: List[Dict] = field(default_factory=list)
    
    def add_activity(self, hour: int, activity: str, duration: float = 1.0):
        self.activities.append({
            "hour": hour,
            "activity": activity,
            "duration": duration,
        })
    
    def get_activity_at(self, hour: int) -> Optional[str]:
        for act in self.activities:
            if act["hour"] == hour:
                return act["activity"]
        return None
    
    def calculate_sleep_hours(self) -> float:
        if self.sleep_time > self.wake_time:
            return 24 - self.sleep_time + self.wake_time
        else:
            return self.wake_time - self.sleep_time
