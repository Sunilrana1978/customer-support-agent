# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ShopEasy Customer Support Agent** — deployed on **AWS Bedrock AgentCore** using the [Strands Agents](https://strandsagents.com) framework. A Streamlit app is the frontend. The agent is live (not spec-only).

## Technology Stack

- **AWS Bedrock AgentCore Runtime** — managed hosting for the Strands agent (`bedrock-agentcore` Python SDK)
- **Strands Agents** (`strands-agents`) — agent framework; tools decorated with `@tool`, agent created with `Agent(...)`
- **AgentCore Memory** — per-user semantic memory via `AgentCoreMemorySessionManager`
- **AgentCore Gateway** — MCP server that proxies Lambda-backed tools (Tools 4 & 5) to the agent
- **AWS Lambda** — two functions (`agentcore-web-search`, `agentcore-check-warranty`) backing Gateway tools
- **Streamlit** — chat UI that calls `bedrock-agentcore:invoke_agent_runtime` directly via boto3
- **AgentCore CLI** (`@aws/agentcore` npm package) — used for deploy, not runtime

## Commands

```bash
# Install agent dependencies (inside app/CustomerSupportAgent/)
pip install -e "app/CustomerSupportAgent"

# Run agent locally (requires Node.js + AgentCore CLI)
agentcore dev                          # starts server on http://localhost:8080
agentcore dev "What is the return policy for electronics?"  # quick test

# Deploy everything (Lambdas + Runtime + Memory + Gateway)
bash scripts/deploy.sh

# Re-deploy agent code after changes
agentcore deploy

# Deploy only the Lambda functions
python infrastructure/deploy_lambdas.py

# Run Streamlit frontend
export AGENTCORE_RUNTIME_ARN=<arn from agentcore status>
streamlit run streamlit_app/app.py

# Invoke deployed agent from CLI
agentcore invoke "Check warranty for PROD-001 purchased 2025-01-10"

# View logs / traces
agentcore logs
agentcore traces list
agentcore status
```

## Architecture

```
User → Streamlit (streamlit_app/app.py)
           │  boto3: invoke_agent_runtime
           ▼
    AgentCore Runtime
    app/CustomerSupportAgent/main.py  (@app.entrypoint)
           │
    Strands Agent
           ├── Tool 1: get_return_policy      ─┐
           ├── Tool 2: get_product_info         ├ tools.py (in-process)
           ├── Tool 3: get_technical_support   ─┘
           │
           ├── AgentCore Memory (session.py)
           │   AgentCoreMemorySessionManager — semantic strategy
           │   env: MEMORY_CUSTOMERSUPPORTMEMORY_ID (auto-injected by AgentCore)
           │
           └── AgentCore Gateway (MCP, no-auth)
               env: AGENTCORE_GATEWAY_URL (auto-injected by AgentCore)
                   ├── Tool 4: web_search   → lambda/web_search/handler.py   (DuckDuckGo)
                   └── Tool 5: check_warranty → lambda/check_warranty/handler.py
```

### Key data flows

- **Memory**: `AgentCoreMemorySessionManager` is passed as `session_manager=` to `Agent(...)`. AgentCore injects `MEMORY_CUSTOMERSUPPORTMEMORY_ID` at runtime. If absent (local dev), memory is silently skipped.
- **Gateway tools**: `MCPClient(lambda: streamablehttp_client(GATEWAY_URL))` is opened as a context manager; `list_tools_sync()` returns the Lambda-backed tools as Strands tool objects, appended to `DIRECT_TOOLS`. If `AGENTCORE_GATEWAY_URL` is unset (local dev), only the 3 direct tools are available.
- **Payload contract**: `invoke_agent_runtime` sends `{"prompt": "...", "session_id": "...", "user_id": "..."}`. The `context.session_id` from AgentCore Runtime takes precedence over `payload["session_id"]`.

## Deployment Config

`agentcore/agentcore.json` declares the Runtime, Memory, and Gateway. `agentcore/aws-targets.json` sets the AWS account and region (`us-west-2`). After `agentcore deploy`, the CLI provisions everything via CDK and injects environment variables into the Runtime automatically.

Lambda `tools.json` files (e.g. `lambda/web_search/tools.json`) are the MCP tool schemas registered with the Gateway via `agentcore add gateway-target --tool-schema-file`.

## Key Design Decisions

- **No Cognito auth**: Gateway uses `authorizerType: NONE`. The Runtime is IAM-secured (only callers with `bedrock-agentcore:InvokeAgentRuntime` can call it).
- **Model override**: Pass `"model_id"` in the invoke payload to use a different Bedrock model per request.
- **Lambda packaging**: `infrastructure/deploy_lambdas.py` installs deps into a temp dir and zips for `python3.12` (x86_64). The `duckduckgo-search` dep is needed only for `web_search`; `check_warranty` uses stdlib only.
- **Tool responses never raise**: Lambda handlers and direct tools return `{"error": "..."}` dicts on failure instead of raising exceptions.
