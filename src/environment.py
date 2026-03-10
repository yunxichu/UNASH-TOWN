"""
环境模块 - 定义随机变化的环境系统
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import random


class Weather(Enum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    FOGGY = "foggy"


class MarketCondition(Enum):
    BOOM = "boom"
    STABLE = "stable"
    RECESSION = "recession"
    CRISIS = "crisis"


class EventType(Enum):
    FESTIVAL = "festival"
    MARKET_DAY = "market_day"
    DISASTER = "disaster"
    VISITOR = "visitor"
    NORMAL = "normal"


@dataclass
class EnvironmentState:
    weather: Weather = Weather.SUNNY
    market: MarketCondition = MarketCondition.STABLE
    event: EventType = EventType.NORMAL
    resource_abundance: float = 1.0
    social_tension: float = 0.5
    luck_factor: float = 1.0
    
    def get_modifiers(self) -> Dict[str, float]:
        weather_mods = {
            Weather.SUNNY: {"cooperation_bonus": 0.1, "energy_cost": 0.9},
            Weather.CLOUDY: {"cooperation_bonus": 0.0, "energy_cost": 1.0},
            Weather.RAINY: {"cooperation_bonus": -0.1, "energy_cost": 1.1},
            Weather.STORMY: {"cooperation_bonus": -0.2, "energy_cost": 1.3},
            Weather.FOGGY: {"cooperation_bonus": -0.05, "energy_cost": 1.0, "trust_penalty": 0.1},
        }
        
        market_mods = {
            MarketCondition.BOOM: {"resource_multiplier": 1.5, "greed_bonus": 0.2},
            MarketCondition.STABLE: {"resource_multiplier": 1.0, "greed_bonus": 0.0},
            MarketCondition.RECESSION: {"resource_multiplier": 0.7, "greed_bonus": -0.1},
            MarketCondition.CRISIS: {"resource_multiplier": 0.5, "greed_bonus": -0.2},
        }
        
        event_mods = {
            EventType.FESTIVAL: {"cooperation_bonus": 0.2, "mood_bonus": 0.2},
            EventType.MARKET_DAY: {"resource_multiplier": 1.2, "competition_bonus": 0.1},
            EventType.DISASTER: {"cooperation_bonus": 0.3, "resource_multiplier": 0.8},
            EventType.VISITOR: {"trust_bonus": 0.1, "resource_multiplier": 1.1},
            EventType.NORMAL: {},
        }
        
        modifiers = {}
        modifiers.update(weather_mods.get(self.weather, {}))
        modifiers.update(market_mods.get(self.market, {}))
        modifiers.update(event_mods.get(self.event, {}))
        
        modifiers["resource_abundance"] = self.resource_abundance
        modifiers["social_tension"] = self.social_tension
        modifiers["luck_factor"] = self.luck_factor
        
        return modifiers


class Environment:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.state = EnvironmentState()
        self.history: List[Dict] = []
        self.day_count = 0
    
    def update(self, hour: int) -> EnvironmentState:
        self._update_weather()
        self._update_market(hour)
        self._update_event(hour)
        self._update_dynamic_factors()
        
        snapshot = {
            "hour": hour,
            "weather": self.state.weather.value,
            "market": self.state.market.value,
            "event": self.state.event.value,
            "resource_abundance": self.state.resource_abundance,
            "social_tension": self.state.social_tension,
        }
        self.history.append(snapshot)
        
        return self.state
    
    def _update_weather(self):
        weather_transitions = {
            Weather.SUNNY: [Weather.SUNNY, Weather.SUNNY, Weather.CLOUDY, Weather.FOGGY],
            Weather.CLOUDY: [Weather.SUNNY, Weather.CLOUDY, Weather.CLOUDY, Weather.RAINY],
            Weather.RAINY: [Weather.CLOUDY, Weather.RAINY, Weather.RAINY, Weather.STORMY],
            Weather.STORMY: [Weather.RAINY, Weather.CLOUDY, Weather.STORMY],
            Weather.FOGGY: [Weather.SUNNY, Weather.CLOUDY, Weather.FOGGY],
        }
        
        possible_weathers = weather_transitions.get(self.state.weather, [Weather.SUNNY])
        self.state.weather = random.choice(possible_weathers)
    
    def _update_market(self, hour: int):
        if hour == 9:
            market_roll = random.random()
            if market_roll < 0.15:
                self.state.market = MarketCondition.BOOM
            elif market_roll < 0.6:
                self.state.market = MarketCondition.STABLE
            elif market_roll < 0.9:
                self.state.market = MarketCondition.RECESSION
            else:
                self.state.market = MarketCondition.CRISIS
    
    def _update_event(self, hour: int):
        if hour == 6:
            event_roll = random.random()
            if event_roll < 0.1:
                self.state.event = EventType.FESTIVAL
            elif event_roll < 0.25:
                self.state.event = EventType.MARKET_DAY
            elif event_roll < 0.3:
                self.state.event = EventType.DISASTER
            elif event_roll < 0.4:
                self.state.event = EventType.VISITOR
            else:
                self.state.event = EventType.NORMAL
    
    def _update_dynamic_factors(self):
        self.state.resource_abundance = max(0.5, min(1.5, 
            self.state.resource_abundance + random.uniform(-0.1, 0.1)))
        
        self.state.social_tension = max(0.0, min(1.0,
            self.state.social_tension + random.uniform(-0.15, 0.15)))
        
        self.state.luck_factor = random.uniform(0.8, 1.2)
    
    def new_day(self):
        self.day_count += 1
        self.state = EnvironmentState()
        self.state.resource_abundance = random.uniform(0.8, 1.2)
        self.state.social_tension = random.uniform(0.3, 0.7)
    
    def get_description(self) -> str:
        weather_desc = {
            Weather.SUNNY: "阳光明媚",
            Weather.CLOUDY: "多云",
            Weather.RAINY: "下雨",
            Weather.STORMY: "暴风雨",
            Weather.FOGGY: "大雾",
        }
        
        market_desc = {
            MarketCondition.BOOM: "市场繁荣",
            MarketCondition.STABLE: "市场稳定",
            MarketCondition.RECESSION: "市场萧条",
            MarketCondition.CRISIS: "市场危机",
        }
        
        event_desc = {
            EventType.FESTIVAL: "节日庆典",
            EventType.MARKET_DAY: "集市日",
            EventType.DISASTER: "灾难事件",
            EventType.VISITOR: "外来访客",
            EventType.NORMAL: "平常日子",
        }
        
        return f"天气: {weather_desc[self.state.weather]}, 市场: {market_desc[self.state.market]}, 事件: {event_desc[self.state.event]}"
    
    def __repr__(self):
        return f"Environment(weather={self.state.weather.value}, market={self.state.market.value}, event={self.state.event.value})"
