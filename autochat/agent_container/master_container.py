import logging

from typing import Callable
from autochat.tools import Tool
from autochat.agents import MasterAgent
from .assistant_container import AssistantContainer


_logger = logging.getLogger(__name__)


class MasterContainer(AssistantContainer):
    def __init__(
            self,
            outer_handoff_tools: list[Tool] | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.outer_handoff_tools = outer_handoff_tools or []

    def add_outer_handoff_tool(self, tool: Tool):
        self.outer_handoff_tools.append(tool)

    def create_factory(self) -> Callable[[], MasterAgent]:
        def _factory() -> MasterAgent:
            return self.agent_class(
                name=self.name,
                description=self.description,
                agent_topic=self._agent_topic_type,
                system_message=self.system_message,
                model_client=self.model_client,
                memory_type=self.memory_type,
                memory_window_size=self.memory_window_size,
                tool_result_as_system_variable=self.tool_result_as_system_variable,
                tools=self.tools,
                handoff_tools=self.handoff_tools,
                outer_handoff_tools=self.outer_handoff_tools,
                **self.agent_arguments
            )

        return _factory