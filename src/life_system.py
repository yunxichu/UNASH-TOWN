"""
永不纳什小镇 - 智能体生活系统
包含睡眠、社交、情感、关系等生活化功能
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import random
import time


class ActivityType(Enum):
    SLEEPING = "sleeping"
    TRADING = "trading"
    SOCIALIZING = "socializing"
    RESTING = "resting"
    THINKING = "thinking"
    WALKING = "walking"


class RelationshipType(Enum):
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    RIVAL = "rival"
    ENEMY = "enemy"


class MoodType(Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    EXCITED = "excited"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    TIRED = "tired"
    REFRESHED = "refreshed"


@dataclass
class PhysicalState:
    energy: float = 100.0
    sleep_debt: float = 0.0
    hours_awake: float = 0.0
    last_sleep_quality: float = 1.0
    
    def need_sleep(self) -> bool:
        return self.energy < 30 or self.sleep_debt > 8
    
    def is_well_rested(self) -> bool:
        return self.energy > 80 and self.sleep_debt < 2
    
    def update(self, hours: float, is_sleeping: bool = False):
        if is_sleeping:
            recovery = min(8, hours) * 12.5
            self.energy = min(100, self.energy + recovery)
            self.sleep_debt = max(0, self.sleep_debt - hours * 0.5)
            self.hours_awake = 0
            self.last_sleep_quality = min(1.0, hours / 8)
        else:
            energy_cost = hours * 2.5
            self.energy = max(0, self.energy - energy_cost)
            self.hours_awake += hours
            if self.hours_awake > 16:
                self.sleep_debt += hours * 0.3


@dataclass
class EmotionalState:
    mood: MoodType = MoodType.NEUTRAL
    happiness: float = 50.0
    stress: float = 20.0
    confidence: float = 50.0
    loneliness: float = 0.0
    
    def update_mood(self):
        if self.happiness > 70 and self.stress < 30:
            self.mood = MoodType.HAPPY
        elif self.happiness < 30 or self.stress > 70:
            self.mood = MoodType.SAD
        elif self.stress > 60:
            self.mood = MoodType.ANXIOUS
        elif self.loneliness > 60:
            self.mood = MoodType.LONELY
        else:
            self.mood = MoodType.NEUTRAL
    
    def socialize_effect(self, quality: float = 0.5):
        self.happiness = min(100, self.happiness + quality * 10)
        self.loneliness = max(0, self.loneliness - quality * 20)
        self.stress = max(0, self.stress - quality * 5)
        self.update_mood()
    
    def trading_effect(self, profit: bool, amount: float = 0):
        if profit:
            self.happiness = min(100, self.happiness + min(10, amount))
            self.confidence = min(100, self.confidence + 5)
        else:
            self.happiness = max(0, self.happiness - min(10, abs(amount)))
            self.confidence = max(0, self.confidence - 5)
            self.stress = min(100, self.stress + 5)
        self.update_mood()


@dataclass
class Relationship:
    agent_id: str
    relationship_type: RelationshipType = RelationshipType.STRANGER
    trust: float = 50.0
    familiarity: float = 0.0
    interactions: int = 0
    last_interaction: float = 0.0
    sentiment: float = 0.0
    
    def interact(self, quality: float = 0.5):
        self.interactions += 1
        self.familiarity = min(100, self.familiarity + quality * 10)
        self.trust = max(0, min(100, self.trust + quality * 5 - (1 - quality) * 3))
        self.sentiment = max(-100, min(100, self.sentiment + quality * 10 - 5))
        self.last_interaction = time.time()
        self._update_type()
    
    def _update_type(self):
        if self.familiarity > 80 and self.trust > 70 and self.sentiment > 50:
            self.relationship_type = RelationshipType.CLOSE_FRIEND
        elif self.familiarity > 50 and self.trust > 50:
            self.relationship_type = RelationshipType.FRIEND
        elif self.familiarity > 20:
            self.relationship_type = RelationshipType.ACQUAINTANCE
        elif self.sentiment < -50:
            self.relationship_type = RelationshipType.ENEMY
        elif self.sentiment < -20:
            self.relationship_type = RelationshipType.RIVAL


@dataclass
class SocialProfile:
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    friends: Set[str] = field(default_factory=set)
    rivals: Set[str] = field(default_factory=set)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    conversation_style: str = "friendly"
    
    def __post_init__(self):
        if not self.personality_traits:
            self.personality_traits = {
                "extraversion": random.uniform(0.3, 0.9),
                "agreeableness": random.uniform(0.3, 0.9),
                "openness": random.uniform(0.3, 0.9),
                "conscientiousness": random.uniform(0.3, 0.9),
                "neuroticism": random.uniform(0.1, 0.7),
            }
        
        if not self.interests:
            all_interests = [
                "投资", "科技", "艺术", "音乐", "运动",
                "阅读", "美食", "旅行", "哲学", "心理学"
            ]
            self.interests = random.sample(all_interests, k=random.randint(2, 5))
    
    def meet_agent(self, agent_id: str) -> Relationship:
        if agent_id not in self.relationships:
            self.relationships[agent_id] = Relationship(agent_id=agent_id)
        return self.relationships[agent_id]
    
    def update_relationships(self):
        for agent_id, rel in self.relationships.items():
            if rel.relationship_type in [RelationshipType.FRIEND, RelationshipType.CLOSE_FRIEND]:
                self.friends.add(agent_id)
            elif rel.relationship_type in [RelationshipType.RIVAL, RelationshipType.ENEMY]:
                self.rivals.add(agent_id)
    
    def get_friend_count(self) -> int:
        return len(self.friends)
    
    def get_social_satisfaction(self) -> float:
        if not self.relationships:
            return 0.0
        
        friend_score = len(self.friends) * 10
        avg_trust = sum(r.trust for r in self.relationships.values()) / len(self.relationships)
        avg_familiarity = sum(r.familiarity for r in self.relationships.values()) / len(self.relationships)
        
        return min(100, (friend_score + avg_trust + avg_familiarity) / 3)


@dataclass
class Conversation:
    participants: List[str]
    topic: str
    start_time: float
    messages: List[Dict] = field(default_factory=list)
    mood: float = 0.5
    
    def add_message(self, speaker_id: str, content: str, emotion: str = "neutral"):
        self.messages.append({
            "speaker": speaker_id,
            "content": content,
            "emotion": emotion,
            "timestamp": time.time()
        })
    
    def get_duration(self) -> float:
        return time.time() - self.start_time


class SocialEngine:
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
        self.public_places: Dict[str, List[str]] = {
            "广场": [],
            "茶馆": [],
            "图书馆": [],
            "公园": [],
        }
    
    def start_conversation(self, participants: List[str], topic: str) -> str:
        conv_id = f"conv_{int(time.time())}_{random.randint(1000, 9999)}"
        self.conversations[conv_id] = Conversation(
            participants=participants,
            topic=topic,
            start_time=time.time()
        )
        return conv_id
    
    def generate_greeting(self, agent_name: str, target_name: str, relationship: Relationship) -> str:
        greetings = {
            RelationshipType.STRANGER: [
                f"你好，我是{agent_name}，很高兴认识你。",
                f"嗨，你是新来的吗？我叫{agent_name}。",
                f"你好，我们好像没见过，我是{agent_name}。",
            ],
            RelationshipType.ACQUAINTANCE: [
                f"嘿{target_name}，今天怎么样？",
                f"哦，{target_name}，好久不见！",
                f"{target_name}，今天天气不错啊。",
            ],
            RelationshipType.FRIEND: [
                f"嘿{target_name}！最近忙什么呢？",
                f"{target_name}！来聊聊吧，我有好多话想说。",
                f"老朋友{target_name}，今天一起喝杯茶？",
            ],
            RelationshipType.CLOSE_FRIEND: [
                f"{target_name}！想死我了，最近怎么样？",
                f"亲爱的{target_name}，你终于来了！",
                f"{target_name}，我有重要的事想和你分享。",
            ],
            RelationshipType.RIVAL: [
                f"哦，{target_name}，又是你。",
                f"{target_name}，希望今天市场对你不太友好。",
                f"哼，{target_name}，别以为我会让你赢。",
            ],
            RelationshipType.ENEMY: [
                f"{target_name}，离我远点。",
                f"我不想看到你，{target_name}。",
                f"{target_name}，我们没什么好说的。",
            ],
        }
        
        return random.choice(greetings.get(relationship.relationship_type, greetings[RelationshipType.STRANGER]))
    
    def generate_topic(self, interests: List[str], market_event: str = None) -> str:
        topics = []
        
        if market_event:
            topics.extend([
                f"你听说了吗？{market_event}！",
                f"关于{market_event}，你怎么看？",
                f"这个{market_event}真是让人意外啊。",
            ])
        
        for interest in interests:
            topics.extend([
                f"最近对{interest}很感兴趣，你呢？",
                f"你觉得{interest}怎么样？",
                f"我发现了一个关于{interest}的有趣事情。",
            ])
        
        topics.extend([
            "今天市场真是波动大啊。",
            "你睡得好吗？我昨晚做了个奇怪的梦。",
            "这个小镇真是个有趣的地方。",
            "你有什么投资心得可以分享吗？",
        ])
        
        return random.choice(topics)
    
    def generate_response(self, agent_name: str, message: str, relationship: Relationship, mood: MoodType) -> str:
        mood_responses = {
            MoodType.HAPPY: [
                "哈哈，太棒了！",
                "这真是个好消息！",
                "我心情很好，来聊聊吧！",
            ],
            MoodType.SAD: [
                "唉，最近有点烦...",
                "我心情不太好，抱歉。",
                "也许改天再聊吧。",
            ],
            MoodType.ANXIOUS: [
                "我有点担心市场...",
                "最近压力有点大。",
                "不知道接下来会发生什么。",
            ],
            MoodType.TIRED: [
                "有点困了...",
                "我需要休息一下。",
                "今天有点累。",
            ],
            MoodType.NEUTRAL: [
                "嗯，有意思。",
                "你说得对。",
                "我明白了。",
            ],
        }
        
        responses = mood_responses.get(mood, mood_responses[MoodType.NEUTRAL])
        
        if relationship.relationship_type == RelationshipType.FRIEND:
            responses.extend([
                "作为朋友，我觉得...",
                "跟你说实话...",
                "我们之间不用客气。",
            ])
        elif relationship.relationship_type == RelationshipType.RIVAL:
            responses.extend([
                "哼，我可不这么认为。",
                "你确定你是对的？",
                "我比你更懂这个。",
            ])
        
        return random.choice(responses)
    
    def agent_enter_place(self, agent_id: str, place: str):
        if place in self.public_places:
            if agent_id not in self.public_places[place]:
                self.public_places[place].append(agent_id)
    
    def agent_leave_place(self, agent_id: str, place: str):
        if place in self.public_places and agent_id in self.public_places[place]:
            self.public_places[place].remove(agent_id)
    
    def get_agents_in_place(self, place: str) -> List[str]:
        return self.public_places.get(place, [])
    
    def get_available_places(self) -> List[str]:
        return list(self.public_places.keys())


class SleepScheduler:
    SLEEP_HOURS_NEEDED = 8
    
    def __init__(self):
        self.sleep_schedules: Dict[str, Dict] = {}
    
    def set_sleep_schedule(self, agent_id: str, bedtime: int = 22, wake_time: int = 6):
        self.sleep_schedules[agent_id] = {
            "bedtime": bedtime,
            "wake_time": wake_time,
            "sleep_duration": self._calculate_duration(bedtime, wake_time),
            "is_sleeping": False,
            "sleep_start": None,
        }
    
    def _calculate_duration(self, bedtime: int, wake_time: int) -> int:
        if bedtime > wake_time:
            return (24 - bedtime) + wake_time
        else:
            return wake_time - bedtime
    
    def should_be_sleeping(self, agent_id: str, current_hour: int) -> bool:
        if agent_id not in self.sleep_schedules:
            self.set_sleep_schedule(agent_id)
        
        schedule = self.sleep_schedules[agent_id]
        bedtime = schedule["bedtime"]
        wake_time = schedule["wake_time"]
        
        if bedtime > wake_time:
            return current_hour >= bedtime or current_hour < wake_time
        else:
            return bedtime <= current_hour < wake_time
    
    def start_sleep(self, agent_id: str):
        if agent_id in self.sleep_schedules:
            self.sleep_schedules[agent_id]["is_sleeping"] = True
            self.sleep_schedules[agent_id]["sleep_start"] = time.time()
    
    def end_sleep(self, agent_id: str):
        if agent_id in self.sleep_schedules:
            self.sleep_schedules[agent_id]["is_sleeping"] = False
            self.sleep_schedules[agent_id]["sleep_start"] = None
    
    def is_sleeping(self, agent_id: str) -> bool:
        if agent_id not in self.sleep_schedules:
            return False
        return self.sleep_schedules[agent_id]["is_sleeping"]
    
    def get_sleep_status(self, agent_id: str) -> Dict:
        if agent_id not in self.sleep_schedules:
            self.set_sleep_schedule(agent_id)
        
        schedule = self.sleep_schedules[agent_id]
        return {
            "is_sleeping": schedule["is_sleeping"],
            "bedtime": schedule["bedtime"],
            "wake_time": schedule["wake_time"],
            "sleep_duration": schedule["sleep_duration"],
        }
