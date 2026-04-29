from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AgentRole(str, Enum):
    MANAGER   = "Manager"
    DEVELOPER = "Developer"
    REVIEWER  = "Reviewer"
    TESTER    = "Tester"
    HUMAN     = "Human"


class ModelTier(str, Enum):
    """Уровень мощности модели, которую использует агент."""
    WEAK   = "weak"    # маленькая/дешёвая модель
    STRONG = "strong"  # большая/дорогая модель


@dataclass
class Message:
    """
    Сообщение между агентами.
    Аналог: задача в Jira, комментарий в pull request, письмо в чат команды.
    """
    sender: AgentRole
    recipient: AgentRole
    content: dict          # произвольный payload — зависит от типа сообщения
    step: int = 0          # номер шага итерации


@dataclass
class AgentMemory:
    """
    Память агента — история всех сообщений и решений.
    Менеджер использует её для принятия решений об эскалации.
    """
    messages: list = field(default_factory=list)

    def add(self, msg: Message):
        self.messages.append(msg)

    def last_from(self, role: AgentRole) -> Optional[Message]:
        for m in reversed(self.messages):
            if m.sender == role:
                return m
        return None

    def count_iterations(self) -> int:
        """Сколько раз Developer уже пытался решить задачу."""
        return sum(1 for m in self.messages if m.sender == AgentRole.DEVELOPER)