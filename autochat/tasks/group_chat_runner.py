import asyncio

from typing import AsyncGenerator

from uuid import uuid4

from autogen_core.base import CancellationToken, AgentId, MessageContext, TopicId
from autogen_core.base import AgentRuntime
from autogen_core.components import ClosureAgent
from autogen_core.components import TypeSubscription
from autogen_core.application import SingleThreadedAgentRuntime

from autogen_core.components.models import (
    UserMessage as LLMUserMessage,
)

from autochat.models.messages import BaseMessage, UserMessage, AssistantResponse, ResetMessage

from autochat.agents import ProxyAgent
from autochat.agent_container import ProxyContainer
from autochat.group_chats import BaseGroupChat
from autochat.tasks import BaseTaskRunner, TaskResult


class GroupChatRunner(BaseTaskRunner):
    """A task runner for conversation chat"""
    def __init__(
            self,
            master_group: BaseGroupChat,
            participants_groups: list[BaseGroupChat],
            task_id: str | None = None,
            runtime: AgentRuntime | None = None,
    ):
        self.id = task_id or str(uuid4()).replace("-", "")[:24]
        self._runtime = runtime or SingleThreadedAgentRuntime()

        self.participant_groups = participants_groups
        self.master_group = master_group

        # Constant topic
        self._user_proxy_topic = "USER_PROXY"

        # topic to publish message in task
        self._task_topic = "TASK_RUNNER"
        self._output_topic = "OUTPUT_TASK"

        self.user_proxy = ProxyContainer(
            name="USER_PROXY",
            description=f"User Proxy",
            agent_class=ProxyAgent,
            agent_type=self._user_proxy_topic,
            agent_topic_type=self._user_proxy_topic,
            inner_topic_type=self.master_group.input_topic_type,
            outer_topic_types=self._output_topic,
        )

        # Constants for the closure agent to collect the output messages.
        self._stop_reason: str | None = None
        self._output_message: AssistantResponse | None = None
        # Flag to track if the group chat has been initialized.
        self._initialized = False

        # Flag to track if the group chat is running.
        self._is_running = False

        self.init_topic_type()

    def init_topic_type(self, **kwargs):
        # add output proxy for all group
        self.master_group.output_topic_type = self.user_proxy.agent_topic_type
        for group in self.participant_groups:
            group.output_topic_type = self.user_proxy.agent_topic_type

    def compile(self, **kwargs):

        # setup group pattern
        for group in self.participant_groups:
            self.master_group.add_sub_group(group)
            group.add_supper_group(self.master_group)

        # group compile
        self.master_group.compile()
        for group in self.participant_groups:
            group.compile()

    @property
    def user_proxy_topic(self):
        return TopicId(type=self._user_proxy_topic, source=self.id)

    @property
    def task_topic(self):
        return TopicId(type=self._task_topic, source=self.id)

    async def init(self):
        self.compile()
        await self.register()
        await self.subscribe_topic()
        self._initialized = True

    async def run(
        self,
        *,
        task: str | BaseMessage | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the task and return the result.

        The runner is stateful and a subsequent call to this method will continue
        from where the previous call left off. If the task is not specified,
        the runner will continue with the current task."""
        result: TaskResult | None = None
        async for message in self.run_stream(
            task=task,
            cancellation_token=cancellation_token,
        ):
            if isinstance(message, TaskResult):
                result = message
        if result is not None:
            return result
        raise AssertionError("The stream should have returned the final result.")

    async def run_stream(
        self,
        *,
        task: str | BaseMessage | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[BaseMessage | TaskResult, None]:
        """Run the task and produces a stream of messages and the final result
        :class:`TaskResult` as the last item in the stream.

        The runner is stateful and a subsequent call to this method will continue
        from where the previous call left off. If the task is not specified,
        the runner will continue with the current task."""
        ...

        if self._is_running:
            raise ValueError("The task is already running, it cannot run again until it is stopped.")

        self._is_running = True
        # Start the runtime.
        # TODO: The runtime should be started by a managed context.
        self._runtime.start()

        if not self._initialized:
            await self.init()

        # Run the task by publishing the start message.
        first_chat_message: BaseMessage | None = None

        if isinstance(task, str):
            llm_user_message = LLMUserMessage(content=task, source="user")
            first_chat_message = UserMessage(content=[llm_user_message], source="user")
        elif isinstance(task, UserMessage):
            first_chat_message = task

        await self._runtime.publish_message(
            message=first_chat_message,
            topic_id=self.user_proxy_topic
        )

        # Start a coroutine to stop the runtime and signal the output message queue is complete.
        async def stop_runtime() -> None:
            await self._runtime.stop_when_idle()

        shutdown_task = asyncio.create_task(stop_runtime())
        # Wait for the shutdown task to finish.
        await shutdown_task

        # Yield the final result.
        yield TaskResult(messages=[self._output_message], stop_reason=self._stop_reason)

        # Indicate that the team is no longer running.
        self._is_running = False

    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        if not self._initialized:
            raise RuntimeError("The group chat has not been initialized. It must be run before it can be reset.")

        if self._is_running:
            raise RuntimeError("The group chat is currently running. It must be stopped before it can be reset.")
        self._is_running = True

        # Start the runtime.
        self._runtime.start()

        # Send a reset message to the group chat.
        await self._runtime.publish_message(
            ResetMessage(),
            topic_id=self.task_topic,
        )

        # Stop the runtime.
        await self._runtime.stop_when_idle()

        # Reset the output message queue.
        self._stop_reason = None

        # Indicate that the team is no longer running.
        self._is_running = False

    async def subscribe_topic(self):
        await self.master_group.subscribe_topic(self._runtime)

        for group in self.participant_groups:
            await group.subscribe_topic(self._runtime)

        # ================== Task Topic ==================
        await self._runtime.add_subscription(
            TypeSubscription(topic_type=self._task_topic, agent_type=self.user_proxy.agent_type))

        await self._runtime.add_subscription(
            TypeSubscription(topic_type=self._task_topic, agent_type=self.master_group.proxy.agent_type))

        for group in self.participant_groups:
            await self._runtime.add_subscription(
                TypeSubscription(topic_type=self._task_topic, agent_type=group.proxy.agent_type))

    async def _register(self):
        await self.user_proxy.register(runtime=self._runtime)
        await self.master_group.register(self._runtime)
        for participant in self.participant_groups:
            await participant.register(self._runtime)

    async def register(self):
        async def collect_output_messages(
                _runtime: AgentRuntime,
                id: AgentId,
                message: AssistantResponse,
                ctx: MessageContext,
        ) -> None:
            if isinstance(message, AssistantResponse):
                self._output_message = message

        # register for component in task
        await self._register()

        # register closure agent
        await ClosureAgent.register(
            self._runtime,
            type="closure_output",
            closure=collect_output_messages,
            subscriptions=lambda: [
                TypeSubscription(topic_type=self._output_topic, agent_type="closure_output"),
            ],
        )
