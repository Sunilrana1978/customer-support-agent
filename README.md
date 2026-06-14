# ShopEasy Customer Support Agent

AI-powered e-commerce customer support built on **AWS Bedrock AgentCore** with a Streamlit frontend.

## Architecture

```
User → Streamlit App → AgentCore Runtime (Strands Agent)
                              │
               ┌──────────────┼──────────────┐
               │              │              │
         Tool 1-3         AgentCore      AgentCore
        (direct)           Memory         Gateway
    get_return_policy   (sessions +    (MCP server)
    get_product_info     history)           │
    get_technical_support                  ├── Tool 4: web_search (Lambda)
                                           └── Tool 5: check_warranty (Lambda)
```

### AgentCore Services Used

| Service | Role |
|---|---|
| **AgentCore Runtime** | Hosts the Strands agent as a managed HTTP service |
| **AgentCore Memory** | Semantic memory across sessions (per user) |
| **AgentCore Gateway** | MCP server routing Lambda-backed tools |
| **AgentCore Observability** | Automatic traces → CloudWatch |

### Tools

| # | Tool | Location | Backend |
|---|---|---|---|
| 1 | `get_return_policy` | Runtime (direct) | In-process |
| 2 | `get_product_info` | Runtime (direct) | In-process |
| 3 | `get_technical_support` | Runtime (direct) | In-process |
| 4 | `web_search` | Gateway → Lambda | DuckDuckGo |
| 5 | `check_warranty` | Gateway → Lambda | Mock warranty DB |

## Prerequisites

- AWS account with **Bedrock model access** enabled (Claude Sonnet 4.0 in us-west-2)
- **AWS CLI** configured (`aws configure`)
- **Node.js 20+** (for the AgentCore CLI)
- **Python 3.11+**

## Project Structure

```
customer-support-agent/
├── agentcore/
│   ├── agentcore.json          # AgentCore project config (Runtime, Memory, Gateway)
│   └── aws-targets.json        # AWS account + region
├── app/
│   └── CustomerSupportAgent/
│       ├── main.py             # Agent entrypoint (@app.entrypoint)
│       ├── tools.py            # Direct tools 1-3 (Strands @tool)
│       ├── memory/
│       │   └── session.py      # AgentCoreMemorySessionManager setup
│       └── pyproject.toml      # Agent Python dependencies
├── lambda/
│   ├── web_search/
│   │   ├── handler.py          # DuckDuckGo search Lambda
│   │   ├── tools.json          # MCP tool schema for Gateway
│   │   └── requirements.txt
│   └── check_warranty/
│       ├── handler.py          # Warranty lookup Lambda
│       ├── tools.json          # MCP tool schema for Gateway
│       └── requirements.txt
├── streamlit_app/
│   ├── app.py                  # Streamlit chat UI
│   └── requirements.txt
├── infrastructure/
│   └── deploy_lambdas.py       # Deploy Lambda functions via boto3
└── scripts/
    └── deploy.sh               # One-command full deployment
```

## Deployment

### Option A — One-command (recommended)

```bash
bash scripts/deploy.sh
```

This script:
1. Patches `agentcore/aws-targets.json` with your account ID
2. Deploys the two Lambda functions (`web_search`, `check_warranty`)
3. Adds them as Gateway targets
4. Runs `agentcore deploy` (provisions Runtime + Memory + Gateway via CDK)

### Option B — Step by step

```bash
# 1. Install AgentCore CLI
npm install -g @aws/agentcore

# 2. Update your account ID
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/REPLACE_WITH_YOUR_ACCOUNT_ID/$ACCOUNT_ID/" agentcore/aws-targets.json

# 3. Deploy Lambda functions
python3 infrastructure/deploy_lambdas.py

# 4. Add Lambda targets to the Gateway (use ARNs printed in step 3)
agentcore add gateway-target \
  --name WebSearchTarget \
  --type lambda-function-arn \
  --lambda-arn <WEB_SEARCH_ARN> \
  --tool-schema-file lambda/web_search/tools.json \
  --gateway CustomerSupportGateway

agentcore add gateway-target \
  --name CheckWarrantyTarget \
  --type lambda-function-arn \
  --lambda-arn <CHECK_WARRANTY_ARN> \
  --tool-schema-file lambda/check_warranty/tools.json \
  --gateway CustomerSupportGateway

# 5. Deploy everything (Runtime + Memory + Gateway) — takes ~5-10 min
agentcore deploy

# 6. Check status and get Runtime ARN
agentcore status
```

## Running the Streamlit App

```bash
# Install dependencies
pip install -r streamlit_app/requirements.txt

# Set the Runtime ARN (from agentcore status)
export AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:<account>:runtime/<id>

# Launch the app
streamlit run streamlit_app/app.py
```

Open http://localhost:8501 in your browser.

## Local Development (without AWS)

```bash
# Install agent dependencies
cd app/CustomerSupportAgent
pip install -e ".[dev]"

# Start local dev server
agentcore dev

# Test in another terminal
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the return policy for electronics?"}'
```

## Useful CLI Commands

```bash
agentcore status          # View deployed resources and ARNs
agentcore invoke "Hello"  # Quick test of the deployed agent
agentcore logs            # Stream runtime logs
agentcore traces list     # View observability traces
agentcore deploy          # Redeploy after code changes
```

## Teardown

```bash
agentcore remove all
agentcore deploy          # Tears down all AWS resources

# Also delete the Lambda functions
aws lambda delete-function --function-name agentcore-web-search
aws lambda delete-function --function-name agentcore-check-warranty
```
