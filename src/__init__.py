"""
UNASH-TOWN: 多智能体博弈小镇
一个包含10个不同初始倾向智能体的博弈模拟系统
"""

from .agent import Agent, AgentTendency
from .environment import Environment
from .game import GameEngine
from .town import Town

__all__ = ['Agent', 'AgentTendency', 'Environment', 'GameEngine', 'Town']
__version__ = '0.1.0'
