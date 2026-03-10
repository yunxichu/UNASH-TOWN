"""
小镇模块 - 主模拟系统
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import random
import time
from datetime import datetime

from .agent import Agent, create_diverse_agents, AgentTendency
from .environment import Environment, EnvironmentState
from .game import GameEngine, GameResult


class TimePhase(Enum):
    MORNING = "morning"
    GAME_TIME = "game_time"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


@dataclass
class DayLog:
    day: int
    events: List[Dict] = field(default_factory=list)
    game_results: List[GameResult] = field(default_factory=list)
    social_interactions: List[Dict] = field(default_factory=list)
    final_resources: Dict[int, float] = field(default_factory=dict)


class Town:
    def __init__(
        self,
        num_agents: int = 10,
        zero_sum_mode: bool = True,
        random_seed: Optional[int] = None,
        verbose: bool = True
    ):
        if random_seed is not None:
            random.seed(random_seed)
        
        self.agents = create_diverse_agents(num_agents)
        self.environment = Environment(seed=random_seed)
        self.game_engine = GameEngine(zero_sum_mode=zero_sum_mode)
        
        self.current_hour = 6
        self.current_day = 1
        self.verbose = verbose
        
        self.day_logs: List[DayLog] = []
        self.current_day_log: Optional[DayLog] = None
    
    def get_time_phase(self, hour: int) -> TimePhase:
        if 6 <= hour < 9:
            return TimePhase.MORNING
        elif 9 <= hour < 15:
            return TimePhase.GAME_TIME
        elif 15 <= hour < 18:
            return TimePhase.AFTERNOON
        elif 18 <= hour < 22:
            return TimePhase.EVENING
        else:
            return TimePhase.NIGHT
    
    def simulate_hour(self) -> Dict:
        phase = self.get_time_phase(self.current_hour)
        self.environment.update(self.current_hour)
        
        hour_events = {
            "hour": self.current_hour,
            "phase": phase.value,
            "environment": self.environment.get_description(),
            "events": []
        }
        
        if phase == TimePhase.MORNING:
            events = self._morning_activities()
            hour_events["events"] = events
        
        elif phase == TimePhase.GAME_TIME:
            results = self._run_game_session()
            hour_events["game_results"] = [
                {
                    "agents": (r.agent1_id, r.agent2_id),
                    "actions": (r.agent1_action, r.agent2_action),
                    "payoffs": (r.agent1_payoff, r.agent2_payoff)
                }
                for r in results
            ]
            if self.current_day_log:
                self.current_day_log.game_results.extend(results)
        
        elif phase == TimePhase.AFTERNOON:
            events = self._afternoon_activities()
            hour_events["events"] = events
        
        elif phase == TimePhase.EVENING:
            events = self._evening_activities()
            hour_events["events"] = events
        
        elif phase == TimePhase.NIGHT:
            events = self._night_activities()
            hour_events["events"] = events
        
        if self.current_day_log:
            self.current_day_log.events.append(hour_events)
        
        if self.verbose:
            self._print_hour_summary(hour_events)
        
        self.current_hour += 1
        if self.current_hour >= 24:
            self._end_day()
            self.current_hour = 0
            self.current_day += 1
            self._start_new_day()
        
        return hour_events
    
    def _morning_activities(self) -> List[Dict]:
        events = []
        
        for agent in self.agents:
            agent.rest()
            
            if random.random() < 0.3:
                other = random.choice([a for a in self.agents if a.id != agent.id])
                interaction = agent.socialize(other)
                events.append({
                    "type": "morning_socialize",
                    "agent": agent.name,
                    "partner": other.name
                })
        
        return events
    
    def _run_game_session(self) -> List[GameResult]:
        results = []
        
        active_agents = [a for a in self.agents if a.energy > 0.1]
        
        if len(active_agents) >= 2:
            round_results = self.game_engine.run_pairing_round(
                active_agents, 
                self.environment.state
            )
            results.extend(round_results)
        
        return results
    
    def _afternoon_activities(self) -> List[Dict]:
        events = []
        
        for agent in self.agents:
            agent.rest()
            
            if random.random() < 0.5:
                others = [a for a in self.agents if a.id != agent.id]
                if others:
                    partner = random.choice(others)
                    interaction = agent.socialize(partner)
                    events.append({
                        "type": "afternoon_socialize",
                        "agent": agent.name,
                        "partner": partner.name,
                        "trust_change": interaction["trust_change"]
                    })
                    if self.current_day_log:
                        self.current_day_log.social_interactions.append(interaction)
        
        return events
    
    def _evening_activities(self) -> List[Dict]:
        events = []
        
        for agent in self.agents:
            if agent.resources < 50:
                events.append({
                    "type": "struggling",
                    "agent": agent.name,
                    "resources": agent.resources
                })
            elif agent.resources > 150:
                events.append({
                    "type": "prospering",
                    "agent": agent.name,
                    "resources": agent.resources
                })
        
        if self.environment.state.event.value == "festival":
            for agent in self.agents:
                agent.mood = min(1.0, agent.mood + 0.1)
            events.append({"type": "festival_celebration"})
        
        return events
    
    def _night_activities(self) -> List[Dict]:
        events = []
        
        for agent in self.agents:
            agent.rest()
            agent.energy = min(1.0, agent.energy + 0.4)
        
        events.append({"type": "rest", "description": "所有居民休息"})
        
        return events
    
    def _start_new_day(self):
        self.environment.new_day()
        self.current_day_log = DayLog(day=self.current_day)
        
        if self.verbose:
            print(f"\n{'='*50}")
            print(f"第 {self.current_day} 天开始")
            print(f"环境: {self.environment.get_description()}")
            print(f"{'='*50}\n")
    
    def _end_day(self):
        if self.current_day_log:
            self.current_day_log.final_resources = {
                a.id: a.resources for a in self.agents
            }
            self.day_logs.append(self.current_day_log)
        
        if self.verbose:
            self._print_day_summary()
    
    def _print_hour_summary(self, hour_events: Dict):
        phase_names = {
            "morning": "早晨",
            "game_time": "博弈时间",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "夜晚"
        }
        
        print(f"\n--- 小时 {hour_events['hour']:02d}:00 ({phase_names.get(hour_events['phase'], hour_events['phase'])}) ---")
        print(f"环境: {hour_events['environment']}")
        
        if "game_results" in hour_events and hour_events["game_results"]:
            print(f"博弈场次: {len(hour_events['game_results'])}")
            for gr in hour_events["game_results"][:3]:
                a1, a2 = gr["agents"]
                act1, act2 = gr["actions"]
                p1, p2 = gr["payoffs"]
                print(f"  Agent {a1}({act1}) vs Agent {a2}({act2}): 收益 ({p1}, {p2})")
        
        if hour_events["events"]:
            for event in hour_events["events"][:3]:
                if event["type"] == "socialize" or "socialize" in event["type"]:
                    print(f"  {event.get('agent', '?')} 与 {event.get('partner', '?')} 社交")
    
    def _print_day_summary(self):
        print(f"\n{'='*50}")
        print(f"第 {self.current_day} 天结束总结")
        print(f"{'='*50}")
        
        sorted_agents = sorted(self.agents, key=lambda a: a.resources, reverse=True)
        
        print("\n资源排行:")
        for i, agent in enumerate(sorted_agents, 1):
            status = "富裕" if agent.resources > 150 else ("正常" if agent.resources > 50 else "贫困")
            print(f"  {i}. {agent.name} ({agent.tendency.value}): {agent.resources:.1f} [{status}]")
        
        stats = self.game_engine.get_statistics()
        print(f"\n博弈统计:")
        print(f"  总场次: {stats['total_games']}")
        print(f"  平均收益: {stats['average_payoff']}")
        print(f"  合作率: {stats['cooperation_rate']*100:.1f}%")
        print(f"  背叛率: {stats['defection_rate']*100:.1f}%")
        print(f"  妥协率: {stats['compromise_rate']*100:.1f}%")
    
    def simulate_day(self) -> DayLog:
        self._start_new_day()
        
        while self.current_hour != 0 or self.current_day_log is None:
            self.simulate_hour()
        
        return self.day_logs[-1]
    
    def simulate_days(self, num_days: int) -> List[DayLog]:
        logs = []
        for _ in range(num_days):
            day_log = self.simulate_day()
            logs.append(day_log)
        return logs
    
    def get_agent_status(self) -> List[Dict]:
        return [
            {
                "id": a.id,
                "name": a.name,
                "tendency": a.tendency.value,
                "resources": round(a.resources, 2),
                "mood": round(a.mood, 2),
                "energy": round(a.energy, 2),
                "interactions": len(a.memory.interactions)
            }
            for a in sorted(self.agents, key=lambda x: x.resources, reverse=True)
        ]
    
    def __repr__(self):
        return f"Town(day={self.current_day}, hour={self.current_hour}, agents={len(self.agents)})"
