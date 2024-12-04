from typing import Callable, Any
import logging

from autogen_core.base import AgentRuntime
from autogen_core.components.tools import FunctionTool
from autogen_core.components import TypeSubscription

from autochat.agents import BaseAgent
from autochat.utils.utils import get_handoff_tool_name
from autochat.models import Memory, MemoryType

_logger = logging.getLogger(__name__)


class AgentContainer:
    def __init__(
            self,
            name: str,
            description: str,
            agent_class,
            *,
            agent_type: str | None = None,
            agent_topic_type: str | None = None,
            proxy_topic_type: str | None = None,
            master_topic_type: str | None = None,
            group_topic_type: str | None = None,
            memory_type: MemoryType = MemoryType.Window,
            memory_window_size: int = 20,
            **kwargs
    ):
        # class
        self.agent_class = agent_class

        # arguments
        self.name = name
        self.description = description
        self.memory_type = memory_type
        self.memory_window_size = memory_window_size
        self.agent_arguments: dict[str, Any] = {}

        # factory
        self._agent_type = agent_type
        self._agent_topic_type = agent_topic_type

        self.proxy_topic_type = proxy_topic_type
        self.master_topic_type = master_topic_type
        self.group_topic_type = group_topic_type

        # init other params
        self.init(**kwargs)

    def init(self, **kwargs):
        self.agent_arguments.update(kwargs)

    @property
    def agent_type(self):
        if not self._agent_type:
            self._agent_type = self.name

        return self._agent_type

    @agent_type.setter
    def agent_type(self, value: str):
        self._agent_type = value

    @property
    def agent_topic_type(self):
        if not self._agent_topic_type:
            self._agent_topic_type = self.agent_type

        return self._agent_topic_type

    @agent_topic_type.setter
    def agent_topic_type(self, value: str):
        self._agent_topic_type = value

    def to_handoff_tool(self) -> FunctionTool:
        def _handoff():
            return self.agent_topic_type

        tool = FunctionTool(
            name=get_handoff_tool_name(self.name),
            description=self.description,
            func=_handoff
        )
        return tool

    def create_factory(self) -> Callable[[], BaseAgent]:
        def _factory() -> BaseAgent:
            return self.agent_class(
                name=self.name,
                description=self.description,
                proxy_topic_type=self.proxy_topic_type,
                master_topic_type=self.master_topic_type,
                group_topic_type=self.group_topic_type,
                agent_topic_type=self.agent_topic_type,
                memory_type=self.memory_type,
                memory_window_size=self.memory_window_size,
                **self.agent_arguments
            )

        return _factory

    async def register(self, runtime: AgentRuntime, **kwargs):
        await self.agent_class.register(
            runtime=runtime,
            type=self.agent_type,
            factory=self.create_factory()
        )
        await runtime.add_subscription(
            TypeSubscription(topic_type=self.agent_topic_type, agent_type=self.agent_type))
        await runtime.add_subscription(
            TypeSubscription(topic_type=self.group_topic_type, agent_type=self.agent_type))

    @classmethod
    def from_config(cls, agent_class: BaseAgent, config: dict[str, Any], **kwargs):
       return cls(agent_class=agent_class, **config)
