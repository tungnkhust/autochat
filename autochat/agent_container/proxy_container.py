from typing import Callable
import logging

from autochat.agents import ProxyAgent

from ._base import AgentContainer

_logger = logging.getLogger(__name__)


class ProxyContainer(AgentContainer):
    def __init__(
            self,
            inner_topic_type: str | None = None,
            outer_topic_types: str | list[str] | None = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.inner_topic_type = inner_topic_type

        if not outer_topic_types:
            self.outer_topic_types = []

        if isinstance(outer_topic_types, str):
            self.outer_topic_types = [outer_topic_types]
        else:
            self.outer_topic_types = outer_topic_types

    def create_factory(self) -> Callable[[], ProxyAgent]:
        def _factory() -> ProxyAgent:
            return self.agent_class(
                name=self.name,
                description=self.description,
                proxy_topic_type=self.proxy_topic_type,
                master_topic_type=self.master_topic_type,
                group_topic_type=self.group_topic_type,
                agent_topic_type=self.agent_topic_type,
                memory_type=self.memory_type,
                memory_window_size=self.memory_window_size,
                inner_topic_type=self.inner_topic_type,
                outer_topic_types=self.outer_topic_types,
                **self.agent_arguments
            )

        return _factory