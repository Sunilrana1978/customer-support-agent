import os
from typing import Optional

MEMORY_ID = os.environ.get("MEMORY_CUSTOMERSUPPORTMEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")


def get_memory_session_manager(session_id: str, actor_id: str) -> Optional[object]:
    """Return an AgentCoreMemorySessionManager if memory is configured, else None."""
    if not MEMORY_ID:
        return None

    from bedrock_agentcore.memory.integrations.strands.config import (
        AgentCoreMemoryConfig,
        RetrievalConfig,
    )
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager,
    )

    retrieval_config = {
        f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
        f"/summaries/{actor_id}/{session_id}": RetrievalConfig(top_k=3, relevance_score=0.5),
    }

    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        ),
        REGION,
    )
