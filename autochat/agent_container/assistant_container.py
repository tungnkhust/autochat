import re
from typing import Any, Callable
import logging

from autogen_ext.models import OpenAIChatCompletionClient

from autogen_core.components.models import SystemMessage, ChatCompletionClient
from autochat.utils.file_utils import load_json, load_yaml
from autochat.utils.utils import get_function
from autochat.tools import Action, FunctionTool, Tool
from autochat.tools.action import ActionAuthentication

from autochat.agents import AssistantAgent

from ._base import AgentContainer


_logger = logging.getLogger(__name__)


class AssistantContainer(AgentContainer):
    def __init__(
            self,
            model_client: ChatCompletionClient | None = None,
            system_message: list[str | SystemMessage] | SystemMessage | str | None = None,
            tools: list[Tool] | None = None,
            handoff_tools: list[Tool] | None = None,
            tool_result_as_system_variable: bool = True,
            next_receive_agent_topic: str = "agent",
            **kwargs
    ):
        super().__init__(**kwargs)
        self.system_message = system_message or []
        self.model_client = model_client  or OpenAIChatCompletionClient(model="gpt-4o-mini")
        self.tools = tools
        self.handoff_tools = handoff_tools or []
        self.tool_result_as_system_variable = tool_result_as_system_variable
        self.next_receive_agent_topic = next_receive_agent_topic

    def add_handoff_tool(self, tool: Tool):
        self.handoff_tools.append(tool)

    def create_factory(self) -> Callable[[], AssistantAgent]:
        def _factory() -> AssistantAgent:
            return self.agent_class(
                name=self.name,
                description=self.description,
                proxy_topic_type=self.proxy_topic_type,
                master_topic_type=self.master_topic_type,
                group_topic_type=self.group_topic_type,
                agent_topic_type=self.agent_topic_type,
                memory_type=self.memory_type,
                memory_window_size=self.memory_window_size,
                system_message=self.system_message,
                model_client=self.model_client,
                tools=self.tools,
                handoff_tools=self.handoff_tools,
                next_receive_agent_topic=self.next_receive_agent_topic,
                tool_result_as_system_variable=self.tool_result_as_system_variable,
                **self.agent_arguments
            )

        return _factory

    @classmethod
    def from_config(cls, agent_class: AssistantAgent, config: dict[str, Any] = None, config_path: str | None = None, **kwargs):
        assert config or config_path

        if not config and config_path:
            if config_path.endswith(".json"):
                config = load_json(config_path)
            elif config_path.endswith(".yaml") or config_path.endswith(".yml"):
                config = load_yaml(config_path)

        # agent name
        name = config.pop("name")

        # agent description
        description = config.pop("description")

        # system message
        system_message = config.pop("system_prompt_template", [])
        if isinstance(system_message, str) and system_message.endswith('.txt'):
            with open(system_message, 'r') as pf:
                data = pf.read()
                system_message = re.split("\n\n={5,}\n\n", data)

        # memory
        memory_config = config.pop("memory", {})
        memory_type = memory_config.get("type", "zero")
        memory_window_size = memory_config.get("max_messages", 20)

        # tools
        tools: dict[str, Any] = config.pop("tools", {})

        _tools: [Tool] = []

        for tool_name, tool_def in tools.items():
            if isinstance(tool_def, str):
                if tool_def.endswith(".json"):
                    openapi_json = load_json(tool_def)
                elif tool_def.endswith(".yaml") or tool_def.endswith(".yml"):
                    openapi_json = load_yaml(tool_def)
                else:
                    raise ValueError(f"Tool definition not support: {tool_def}")

                _authentication = kwargs.get("authentication", {})
                authentication = ActionAuthentication(**_authentication)
                tool = Action.create(openapi_json, authentication=authentication)
            elif isinstance(tool_def, dict):
                func_name = tool_def.get("func_name")
                package = tool_def.get("package")
                description = tool_def.get("description", tool_name)
                func = get_function(module_name=package, function_name=func_name)

                tool = FunctionTool(
                    name=tool_name,
                    func=func,
                    description=description
                )
            else:
                raise ValueError(f"Tool definition not support: {tool_def}")

            _tools.append(tool)

        return cls(
            name=name,
            description=description,
            agent_class=agent_class,
            system_message=system_message,
            memory_type=memory_type,
            memory_window_size=memory_window_size,
            tools=_tools,
            **config,
            **kwargs
        )