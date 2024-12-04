from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from typing import Any


class BaseMessage(BaseModel):
    """A base message."""
    id: str = str(uuid4()).replace("-", "")[:24]
    source: str
    content: Any = None

    """The name of the agent that sent this message."""
    path: list[str] = []

    traces: list[Any] = []
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def show_id(self):
        return f"{self.__class__.__name__}(id={self.id}, source={self.source})"

    def show_log(self):
        return f"{self.__class__.__name__}(source={self.source}, content={self.content}, path={self.path})"

class UserMessage(BaseMessage):
    content: list[Any] = []
    sender_id: str | None = None


class AssistantResponse(BaseMessage):
    content: Any = None
    inner_handle_topic: str | None = None
    outer_handle_topic: str | None = None


class HandoffMessage(BaseMessage):
    """A message requesting handoff of a conversation to another agent."""

    target: str
    """The name of the target agent to handoff to."""

    message: BaseMessage | None = None
    """The raw message to the target agent."""



class ResetMessage(BaseModel):
    """A request to reset the agents in the group chat."""
    content: str = ""
