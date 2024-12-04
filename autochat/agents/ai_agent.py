from typing import List, Any, Mapping
import logging
import json
import copy
from autogen_core.base import MessageContext, TopicId, CancellationToken
from autogen_core.components.models import (
    ChatCompletionClient,
    SystemMessage as LLMSystemMessage,
    FunctionExecutionResult as LLMFunctionExecutionResult,
    FunctionExecutionResultMessage as LLMFunctionExecutionResultMessage,
    AssistantMessage as LLMAssistantMessage,
    LLMMessage
)
from autogen_core.components.tools import Tool
from autogen_core.components import FunctionCall, message_handler
from openai import BaseModel

from autochat.models.messages import UserMessage, AssistantResponse, HandoffMessage, ResetMessage
from autochat.models import LLMResult

from autochat.agents._base import BaseAgent
from autochat.utils import print_utils
from autochat.utils.utils import parser_assistant_message, build_system_prompt


_logger = logging.getLogger(__name__)


class AIAgent(BaseAgent):

    def __init__(
            self,
            system_message: LLMSystemMessage | list[LLMSystemMessage] | str | list[str],
            model_client: ChatCompletionClient,
            tools: List[Tool] | None = None,
            handoff_tools: List[Tool] | None = None,
            next_receive_agent_topic: str = "agent", # [self, proxy, master, other]
            tool_result_as_system_variable: bool = True,
            tool_result_save_as_metadata: bool = True,
            **kwargs
    ):
        # preprocess init
        tools = tools or []
        handoff_tools = handoff_tools or []

        super().__init__(**kwargs)

        self._system_message = system_message
        self._model_client = model_client
        self._tools = tools
        self._handoff_tools = handoff_tools

        if next_receive_agent_topic == "agent":
            self._next_receive_agent_topic = self.type
        elif next_receive_agent_topic == "master":
            self._next_receive_agent_topic = self.master_topic.type
        else:
            self._next_receive_agent_topic = next_receive_agent_topic

        self._color_show = print_utils.color_green

        self.state: dict[str, Any] = {}
        self.tool_result_as_system_variable = tool_result_as_system_variable
        self.tool_result_save_as_metadata = tool_result_save_as_metadata

    def _parser_system_message(self, system_variables: dict[str, Any] | None = None):
        system_message = copy.copy(self._system_message)
        system_variables = system_variables or {}

        if not isinstance(system_message, list):
            system_message = [system_message]

        system_prompt_template: list[str] = []

        for message in system_message:
            if isinstance(message, LLMSystemMessage):
                _message = message.content
            elif isinstance(message, str):
                _message = message
            else:
                raise TypeError(f"Expected type [str | SystemMessage] but got {type(message)}")

            system_prompt_template.append(_message)

        _system_message = build_system_prompt(system_prompt_template, system_variables)

        return LLMSystemMessage(content=_system_message)

    async def call_llm(
            self,
            messages: list[LLMMessage],
            json_output: bool | None = None,
            extra_create_args: Mapping[str, Any] = None,
            cancellation_token: CancellationToken | None = None,
            system_variables: dict[str, Any] = None,
            tools: list[Tool] = None
    ) -> LLMResult:
        tools = tools or []

        extra_create_args = extra_create_args or {}
        system_variables = system_variables or {}

        system_message = self._parser_system_message(system_variables)

        result = await self._model_client.create(
            messages=[system_message] + messages,
            tools=tools,
            cancellation_token=cancellation_token,
            json_output=json_output,
            extra_create_args=extra_create_args
        )

        metadata = {}

        # parser output
        if isinstance(result.content, str):
            parsed_content = parser_assistant_message(result.content)
            result.content = parsed_content["response"]
            parsed_content.pop("response")
            metadata.update(parsed_content)

        llm_result = LLMResult(
            content=result.content,
            finish_reason=result.finish_reason,
            logprobs=result.logprobs,
            usage=result.usage,
            cached=result.cached,
            metadata=metadata
        )

        return llm_result

    async def call_llm_with_retry_new_conversation(
            self,
            messages: list[LLMMessage],
            json_output: bool | None = None,
            extra_create_args: Mapping[str, Any] = None,
            cancellation_token: CancellationToken | None = None,
            system_variables: dict[str, Any] = None,
            tools: list[Tool] = None
    ) -> tuple[LLMResult, list[LLMMessage]]:

        llm_result = await self.call_llm(
            messages=messages,
            json_output=json_output,
            extra_create_args=extra_create_args,
            system_variables=system_variables,
            cancellation_token=cancellation_token,
            tools=tools
        )

        new_conversation = llm_result.metadata.get("new_conversation", None)

        if new_conversation:
            messages = [messages[-1]]

            llm_result = await self.call_llm(
                messages=messages,
                tools=tools,
                json_output=json_output,
                extra_create_args=extra_create_args,
                system_variables=system_variables,
                cancellation_token=cancellation_token
            )
            llm_result.metadata["reset_history"] = True

        return llm_result, messages

    def get_tools(self, message: UserMessage | HandoffMessage, ctx: MessageContext):
        return self._tools

    def get_handoff_tools(self, message: UserMessage | HandoffMessage, ctx: MessageContext):
        return self._handoff_tools

    async def run_llm_loop(
            self,
            messages: list[LLMMessage],
            json_output: bool | None = None,
            extra_create_args: Mapping[str, Any] = None,
            cancellation_token: CancellationToken | None = None,
            system_variables: dict[str, Any] = None,
            tools: list[Tool] = None,
            handoff_tools: list[Tool] = None,
            **kwargs
    ):
        """Basic run LLM loops."""
        tools = tools or []
        tools_map = {tool.name: tool for tool in tools}
        handoff_tools = handoff_tools or []
        handoff_tools_map = {tool.name: tool for tool in handoff_tools}
        tool_results = {}
        reset_history = False

        handoffs: list[str] = []

        llm_result, messages = await self.call_llm_with_retry_new_conversation(
            messages=messages,
            tools=tools + handoff_tools,
            json_output=json_output,
            extra_create_args=extra_create_args,
            system_variables=system_variables
        )
        reset_history = llm_result.metadata.get("reset_history", False)

        # Run loop process function calling
        while isinstance(llm_result.content, list) and all(isinstance(m, FunctionCall) for m in llm_result.content):
            tool_call_results: List[LLMFunctionExecutionResult] = []

            # Process each function call.
            for call in llm_result.content:
                arguments = json.loads(call.arguments)
                # if call is normal tool
                if call.name in tools_map:
                    result = await tools_map[call.name].run_json(arguments, cancellation_token)
                    result_as_str = tools_map[call.name].return_value_as_string(result)
                    tool_call_results.append(LLMFunctionExecutionResult(call_id=call.id, content=result_as_str))
                    tool_results[call.name] = result

                    if self.tool_result_as_system_variable:
                        if isinstance(result, BaseModel):
                            system_variables.update(result.model_dump())
                        elif isinstance(result, dict):
                            system_variables.update(result)

                # if call is handoff tool
                elif call.name in handoff_tools_map:
                    # Execute the tool to get the handoff agent's topic type.
                    result = await handoff_tools_map[call.name].run_json(arguments, cancellation_token)
                    topic_type = handoff_tools_map[call.name].return_value_as_string(result)

                    handoffs.append(topic_type)

            if len(handoffs) > 0:
                # If have handoff tool then break and handoff to other agent
                break

            # Continue process after call tools
            if len(tool_call_results) > 0:
                # Make continue LLM call with the results.
                messages.extend(
                    [
                        LLMAssistantMessage(content=llm_result.content, source=self.id.type),
                        LLMFunctionExecutionResultMessage(content=tool_call_results),
                    ]
                )
                llm_result = await self.call_llm(
                    messages=messages,
                    tools=tools,
                    json_output=json_output,
                    extra_create_args=extra_create_args,
                    system_variables=system_variables
                )

        if self.tool_result_save_as_metadata:
            llm_result.metadata["tool_results"] = tool_results

        llm_result.metadata["reset_history"] = reset_history

        return {
            "llm_result": llm_result,
            "handoffs": handoffs,
            "messages": messages
        }

    def get_handoffs(self, llm_result: LLMResult, **kwargs) -> list[str]:
        return []

    def get_next_receive_agent_topic(self, llm_result: LLMResult, **kwargs):
        return self._next_receive_agent_topic

    @message_handler
    async def handle_user_message(self, message: UserMessage | HandoffMessage, ctx: MessageContext) -> None:

        # Process for handoff message
        if isinstance(message, HandoffMessage):
            message = message.message

        message.path.append(self.name)

        print_utils.print_logs(f"{self.name} Receive message from {message.source.upper()}", message, trace_messages=message.traces, debug=self.debug)

        tools = self.get_tools(message=message, ctx=ctx)
        handoff_tools = self.get_handoff_tools(message=message, ctx=ctx)

        system_variables = message.metadata.get("system_variables", {})

        output = await self.run_llm_loop(
            messages=message.content,
            tools=tools,
            handoff_tools=handoff_tools,
            system_variables=system_variables,
            cancellation_token=ctx.cancellation_token
        )

        llm_result = output.get("llm_result")
        handoffs: list[str] = output.get("handoffs", [])
        message.content = output.get("messages", message.content)

        check_handoffs = self.get_handoffs(llm_result)

        if check_handoffs:
            handoffs.extend(check_handoffs)

        # processing handoff
        for handoff in handoffs:
            if not handoff:
                continue

            handoff_message = HandoffMessage(
                    target=handoff,
                    message=message,
                    source=self.type
            )

            print_utils.print_logs(f"{self.name} Handoff to {handoff}", message, trace_messages=message.traces, debug=self.debug)
            target_topic = TopicId(type=handoff, source=self.key)
            await self.publish_message(handoff_message, topic_id=target_topic)
            return

        message.content.append(LLMAssistantMessage(content=llm_result.content, source=self.id.type))

        message_response = AssistantResponse(
            content=message.content,
            inner_handle_topic=self.get_next_receive_agent_topic(llm_result=llm_result),
            source=self.type,
            metadata=llm_result.metadata,
            traces=message.traces,
            path=[self.name]
        )
        print_utils.print_logs(f"{self.name} Publish response to Topic {self.proxy_topic.type}", message_response, trace_messages=message_response.traces, debug=self.debug)

        await self.publish_message(
            message=message_response,
            topic_id=self.proxy_topic
        )

    async def reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        pass
