import logging

from autogen_core.base import MessageContext, TopicId
from autogen_core.components import message_handler

from autochat.models.messages import UserMessage, AssistantResponse, ResetMessage, HandoffMessage
from autochat.agents._base import BaseAgent
from autochat.utils import print_utils

_logger = logging.getLogger(__name__)


class ProxyAgent(BaseAgent):
    def __init__(
            self,
            *,
            inner_topic_type: str | None = None,
            outer_topic_types: str | list[str] | None = None,
            **kwargs
    ):
        if isinstance(outer_topic_types, str):
            outer_topic_types = [outer_topic_types]

        super().__init__(**kwargs)
        self._inner_topic_type = inner_topic_type
        self._outer_topic_types = outer_topic_types or []

    @property
    def inner_topic_type(self) -> str:
        return self._inner_topic_type

    @inner_topic_type.setter
    def inner_topic_type(self, value: str):
        self._inner_topic_type = value

    @property
    def outer_topic_type(self) -> list[str]:
        return self._outer_topic_types

    @outer_topic_type.setter
    def outer_topic_type(self, value: list[str]):
        self._outer_topic_types = value

    @property
    def inner_topic(self) -> TopicId:
        return TopicId(type=self.inner_topic_type, source=self.key)

    @property
    def outer_topics(self) -> list[TopicId]:
        return [TopicId(type=_outer_topic, source=self.key) for _outer_topic in self.outer_topic_type]

    @message_handler
    async def handle_outer_message(self, message: UserMessage | HandoffMessage, ctx: MessageContext) -> None:
        if isinstance(message, HandoffMessage):
            message = message.message

        # add source path for message
        message.path.append(self.name)

        """Transfer message from outer group to current handling Agent"""
        print_utils.print_logs(f"{self.name} Receive message from {message.source.upper()}", message, trace_messages=message.traces, debug=self.debug)
        message.source = self.type

        print_utils.print_logs(f"{self.name} Redirect message to Topic [{self.inner_topic.type}]", message, trace_messages=message.traces, debug=self.debug)
        await self.publish_message(
            message=message,
            topic_id=self.inner_topic
        )

    @message_handler
    async def handle_inner_response(self, message: AssistantResponse, ctx: MessageContext) -> None:
        """Handle assistant response from agent in group"""
        message.path.append(self.name)

        print_utils.print_logs(f"{self.name} Receive response from {message.source.upper()}", message, trace_messages=message.traces, debug=self.debug)
        if message.inner_handle_topic:
            self.inner_topic_type = message.inner_handle_topic

        # publish response to outer group
        for output_topic in self.outer_topics:
            print_utils.print_logs(f"{self.name} Redirect response to Topic [{output_topic.type}]", message, trace_messages=message.traces, debug=self.debug)
            message.inner_handle_topic = self.agent_topic_type
            message.source = self.type
            await self.publish_message(message, topic_id=output_topic)

    async def reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        await self.publish_message(message, topic_id=self.group_topic)
