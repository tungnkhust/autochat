from dataclasses import dataclass
from typing import AsyncGenerator, Protocol, Sequence

from autogen_core.base import CancellationToken

from autochat.models.messages import BaseMessage


@dataclass
class TaskResult:
    """Result of running a task."""

    messages: Sequence[BaseMessage]
    """Messages produced by the task."""

    stop_reason: str | None = None
    """The reason the task stopped."""


class BaseTaskRunner(Protocol):
    """A task runner."""

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
        ...

    def run_stream(
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

    async def reset(self) -> None:
        """Reset the team and all its participants to its initial state."""
        ...
