import logging
from autogen_core.base import MessageContext

from autochat.models.messages import UserMessage, HandoffMessage, ResetMessage
from autochat.agents import AIAgent
from autochat.utils.utils import get_handoff_tool_name

_logger = logging.getLogger(__name__)


class MasterAgent(AIAgent):
    def __init__(
            self,
            outer_handoff_tools: list[str] | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.outer_handoff_tools = outer_handoff_tools or []

    def get_handoff_tools(self, message: UserMessage | HandoffMessage, ctx: MessageContext):
        prevent_handoff_tools = [get_handoff_tool_name(agent_name=name) for name in message.path]

        call_handoff_tools = []
        for tool in self._handoff_tools:
            if tool.name in prevent_handoff_tools:
                continue
            call_handoff_tools.append(tool)

        return call_handoff_tools

    async def reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        pass
