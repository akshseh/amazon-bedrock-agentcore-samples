"""AgentCore Memory session manager with graceful degradation."""
import uuid
from typing import Optional
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from config import MEMORY_ID, REGION


def get_memory_session_manager(session_id: Optional[str], actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Returns session manager, or None if not configured."""
    if not MEMORY_ID:
        return None
    session_id = session_id or uuid.uuid4().hex
    retrieval_config = {
        f"/inbox/{actor_id}/facts": RetrievalConfig(top_k=5, relevance_score=0.5),
        f"/inbox/{actor_id}/preferences": RetrievalConfig(top_k=3, relevance_score=0.5),
    }
    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(memory_id=MEMORY_ID, session_id=session_id, actor_id=actor_id, retrieval_config=retrieval_config),
        REGION,
    )
