import logging
from autogen_core.base import MessageContext


from autochat.models.messages import ResetMessage
from autochat.models import LLMResult
from autochat.agents import AIAgent

_logger = logging.getLogger(__name__)


class AssistantAgent(AIAgent):
    def get_handoffs(self, llm_result: LLMResult, **kwargs) -> list[str]:
        handoffs = []
        intent = llm_result.metadata.get("intent", "")
        if "OOS" in intent:
            handoffs.append(self._master_topic_type)
        return handoffs

    def get_next_receive_agent_topic(self, llm_result: LLMResult, **kwargs):
        intent = llm_result.metadata.get("intent", "")
        if intent == "MAIN_UC":
            return self._master_topic_type

        return self._next_receive_agent_topic

    async def reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        pass
