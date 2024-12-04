from autogen_core.base import AgentRuntime
from autogen_core.components.tools import FunctionTool, Tool

from autochat.utils.utils import get_handoff_tool_name

class BaseGroup:
    def __init__(
            self,
            name: str,
            description: str,
            group_topic_type: str | None = None,
            input_topic_type: str | None = None,
            output_topic_type: str | None = None,
            sub_groups: list["BaseGroup"] | None = None,
            supper_groups: list["BaseGroup"] | None = None,
            **kwargs
    ):
        # init params
        self.name = name
        self.description = description

        # factory
        self._group_topic_type = group_topic_type
        self._input_topic_type = input_topic_type
        self._output_topic_type = output_topic_type

        self.sub_groups = sub_groups or []
        self.supper_groups = supper_groups or []

        self.init(**kwargs)

    @property
    def group_topic_type(self) -> str:
        if not self._group_topic_type:
            self._group_topic_type = f"group_{self.name}"
        return self._group_topic_type

    @group_topic_type.setter
    def group_topic_type(self, value: str):
        self._group_topic_type = value

    @property
    def input_topic_type(self) -> str:
        if not self._input_topic_type:
            self._input_topic_type = f"{self.name}"
        return self._input_topic_type

    @input_topic_type.setter
    def input_topic_type(self, value: str):
        self._input_topic_type = value

    @property
    def output_topic_type(self) -> str:
        if not self._output_topic_type:
            self._output_topic_type = f"{self.name}_output"
        return self._output_topic_type

    @output_topic_type.setter
    def output_topic_type(self, value: str):
        self._output_topic_type = value

    def init(self, **kwargs):
        pass

    def add_sub_group(self, group: "BaseGroup"):
        self.sub_groups.append(group)

    def add_supper_group(self, group: "BaseGroup"):
        self.supper_groups.append(group)

    async def subscribe_topic(self, runtime: AgentRuntime, **kwargs):
        raise NotImplementedError()

    async def register(self, runtime: AgentRuntime, **kwargs):
        raise NotImplementedError()

    def to_handoff_tool(self):
        def _handoff():
            return self.input_topic_type

        return FunctionTool(
            description=self.description,
            name=get_handoff_tool_name(agent_name=self.name),
            func=_handoff
        )

    def add_handoff_tool(self, tool: Tool):
        raise NotImplementedError()

    def add_outer_handoff_tool(self, tool: Tool):
        raise NotImplementedError()