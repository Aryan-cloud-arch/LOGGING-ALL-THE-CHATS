"""
Telegram DM Mirror - Source Package
====================================
Real-time mirroring of Telegram DM conversations
to a backup group using bot personas.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .monitor import Monitor
from .bots import BotManager

__all__ = [
    "Monitor",
    "BotManager"
]
