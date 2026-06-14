"""
Customer Support Agent — AWS Bedrock AgentCore Runtime entrypoint.

Direct tools (Tools 1-3):
  - get_return_policy   → return window and conditions
  - get_product_info    → catalog lookup
  - get_technical_support → troubleshooting + ticket

Gateway tools via AgentCore Gateway → Lambda (Tools 4-5):
  - web_search         → DuckDuckGo (no API key)
  - check_warranty     → warranty status lookup

Memory: AgentCoreMemorySessionManager stores conversation history per session.
"""

import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from botocore.config import Config
from strands import Agent
from strands.models import BedrockModel

from tools import get_return_policy, get_product_info, get_technical_support
from memory.session import get_memory_session_manager

app = BedrockAgentCoreApp()

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

SYSTEM_PROMPT = """You are a helpful customer support agent for ShopEasy, an e-commerce platform.

You assist customers with:
- Return policies: use get_return_policy to explain return windows and conditions
- Product details: use get_product_info to look up specs, price, and availability
- Technical issues: use get_technical_support for troubleshooting steps and to open a ticket
- Warranty status: use check_warranty (Gateway tool) to verify coverage and expiry
- Web searches: use web_search (Gateway tool) for current reviews or external information

Guidelines:
- Be empathetic, concise, and solution-focused
- Always cite the support ticket ID when opening a technical case
- Offer escalation to a human agent if the issue is unresolved after troubleshooting
- Never share pricing or policy details from memory; always call the appropriate tool
"""

DIRECT_TOOLS = [get_return_policy, get_product_info, get_technical_support]


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    session_id = getattr(context, "session_id", payload.get("session_id", "default-session"))
    user_id = payload.get("user_id", "anonymous")
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    model_id = payload.get("model_id", MODEL_ID)

    model = BedrockModel(
        model_id=model_id,
        region_name=AWS_REGION,
        boto_client_config=Config(
            read_timeout=900,
            connect_timeout=10,
            retries=dict(max_attempts=3, mode="adaptive"),
        ),
    )

    session_manager = get_memory_session_manager(session_id, user_id)

    if GATEWAY_URL:
        from strands.tools.mcp.mcp_client import MCPClient
        from mcp.client.streamable_http import streamablehttp_client

        mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL))
        with mcp_client:
            gateway_tools = list(mcp_client.list_tools_sync())
            agent = Agent(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                tools=DIRECT_TOOLS + gateway_tools,
                session_manager=session_manager,
            )
            result = agent(user_message)
    else:
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=DIRECT_TOOLS,
            session_manager=session_manager,
        )
        result = agent(user_message)

    return {"result": _extract_text(result), "session_id": session_id}


def _extract_text(result) -> str:
    if hasattr(result, "message"):
        content = result.message.get("content", [])
        return " ".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and "text" in block
        )
    return str(result)


if __name__ == "__main__":
    app.run()
