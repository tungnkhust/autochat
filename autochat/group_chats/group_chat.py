from autogen_core.base import AgentRuntime
from autogen_core.components.tools import FunctionTool, Tool

from autochat.agent_container import AgentContainer, MasterContainer, ProxyContainer
from autogen_core.components import TypeSubscription

from ._base import BaseGroup

class BaseGroupChat(BaseGroup):
    def __init__(
            self,
            proxy: ProxyContainer | None = None,
            master: MasterContainer | None = None,
            participants: list[AgentContainer] | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)

        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")

        self.proxy = proxy
        self.master = master
        self.participants = participants or []

        self.init_topic_type()

    def init_topic_type(self, **kwargs):
        # set group topic for each agent
        self.proxy.master_topic_type = self.master_topic_type
        self.proxy.group_topic_type = self.group_topic_type
        # init inner topic proxy to master
        self.proxy.inner_topic_type = self.master_topic_type

        self.master.proxy_topic_type = self.proxy_topic_type
        self.master.group_topic_type = self.group_topic_type

        for participant in self.participants:
            participant.master_topic_type = self.master_topic_type
            participant.proxy_topic_type = self.proxy_topic_type
            participant.group_topic_type = self.group_topic_type

    @property
    def master_topic_type(self) -> str:
        return self.master.agent_topic_type

    @property
    def proxy_topic_type(self) -> str:
        return self.proxy.agent_topic_type

    def add_handoff_tool(self, tool: Tool):
        self.master.add_handoff_tool(tool=tool)

    def add_outer_handoff_tool(self, tool: Tool):
        self.master.add_outer_handoff_tool(tool=tool)

    def compile(self, **kwargs):
        self.proxy.outer_topic_types = [self.output_topic_type]

    async def subscribe_topic(self, runtime: AgentRuntime, **kwargs):
        # Subscribe proxy to input topic
        await runtime.add_subscription(
            TypeSubscription(topic_type=self.input_topic_type, agent_type=self.proxy.agent_type))

    async def register(self, runtime: AgentRuntime, **kwargs):
        # register proxy agent
        await self.proxy.register(runtime=runtime)

        # register master agent
        await self.master.register(runtime=runtime)

        # register participant agent
        for participant in self.participants:
            await participant.register(runtime=runtime)

