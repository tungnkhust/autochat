from enum import Enum
from typing import Any

from dataclasses import dataclass, field
from pydantic import BaseModel
from autogen_core.components.models import CreateResult


class MemoryType(str, Enum):
    Naive: str = "naive"
    Window: str = "window"
    Zero: str = "zero"


class Memory(BaseModel):
    messages: list[dict[str, Any]] = []
    type: str = MemoryType.Window
    window_size: int = 5

    def add_message(self, message: BaseModel) -> None:
        match self.type:
            case MemoryType.Window:
                self.messages.append(message.model_dump(exclude={"id", "session_id"}))
                # Ensure the list does not exceed the window size
                if len(self.messages) > self.window_size:
                    self.messages.pop(0)  # Remove the oldest message
            case MemoryType.Naive:
                self.messages.append(message.model_dump())
            case _:
                pass


@dataclass
class LLMResult(CreateResult):
    metadata: dict[str, Any] = field(default_factory=dict)