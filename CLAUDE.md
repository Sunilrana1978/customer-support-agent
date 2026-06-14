# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AWS Bedrock Shopping Customer Support Agent** — a spec-driven project that is not yet implemented. The full implementation plan lives in `SHOPPING_SUPPORT_AGENT_IMPLEMENTATION_GUIDE.md`. Code should be built according to that spec.

## Technology Stack

- **Python 3.11+** with Pydantic v2 for data models
- **AWS Bedrock** (Claude model) as the agent runtime
- **DynamoDB** for customer data, order history, and conversation memory (session TTL: 90 days)
- **AWS Lambda** for tool execution (invoked by Bedrock as action groups)
- **API Gateway** as the HTTP entry point
- **CloudWatch** for metrics and monitoring (`ShoppingSupport` namespace)

## Intended Project Structure

```
shopping-support-agent/
├── infrastructure/         # DynamoDB table creation, CloudFormation, IAM roles
├── src/
│   ├── agent/              # Main agent client (client.py) and config
│   ├── tools/              # Lambda-backed tools (customer, order, refund, shipping)
│   ├── models/             # Pydantic models (customer, order, session)
│   ├── evaluations/        # CloudWatch metrics and performance analytics
│   └── integrations/       # DynamoDB and Bedrock client wrappers
├── tests/
│   ├── unit/               # Tool and model tests using moto mock_dynamodb
│   ├── integration/        # DynamoDB integration tests
│   └── e2e/                # Full conversation flow tests
└── deployment/             # Lambda packaging and deploy scripts
```

## Commands

Once the code is scaffolded (per the spec):

```bash
# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_customer_tools.py -v

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Package Lambda function
bash deployment/package_lambda.sh

# Set up DynamoDB tables
python infrastructure/dynamodb_tables.py

# Deploy Lambda
AWS_ACCOUNT_ID=<id> bash deployment/deploy.sh
```

## Architecture

The system follows a layered design where **Bedrock Agent** acts as the orchestrator:

1. **API Gateway** receives `POST /invoke-agent` with `{session_id, customer_id, message}`
2. **`ShoppingCustomerSupportAgent.invoke_agent()`** (in `src/agent/client.py`) orchestrates:
   - Fetches customer identity (VIP status, lifetime value) from DynamoDB
   - Retrieves prior conversation from `shopping-agent-sessions` DynamoDB table (memory)
   - Injects customer context into the Bedrock session state
   - Calls `bedrock_agent_runtime.invoke_agent()` which triggers Lambda tools as needed
   - Persists updated conversation back to DynamoDB
   - Emits CloudWatch metrics to `ShoppingSupport` namespace
3. **Lambda tools** are action groups registered with the Bedrock agent:
   - `customer_tools`: `get_customer_profile`, `update_customer_vip_status`
   - `order_tools`: `get_order_status`, `get_recent_orders`
   - `refund_tools`: `check_return_policy`, `process_refund`

## DynamoDB Tables

| Table | PK | SK | Notes |
|---|---|---|---|
| `shopping-customers` | `customer_id` | — | GSI on `email` |
| `shopping-orders` | `customer_id` | `order_id` | GSI on `order_date` |
| `shopping-returns` | `return_id` | — | TTL 90 days; GSI on `order_id` |
| `shopping-agent-sessions` | `session_id` | `timestamp` | TTL 90 days |

All tables use `PAY_PER_REQUEST` billing.

## Key Design Decisions

- **VIP policy**: Regular customers get 30-day returns; Silver/Gold/Platinum get 60 days.
- **Session memory**: Stored as a `conversation` list in DynamoDB, retrieved on each `invoke_agent` call and re-injected into Bedrock session state.
- **Tool responses**: All tools return `{'success': bool, ...}` dicts — never raise exceptions to callers.
- **Tests use moto**: `@mock_dynamodb` decorator from `moto` library mocks AWS calls in unit/integration tests. Do not use real AWS in tests.
- **AWS region**: `us-west-2` for Bedrock and CloudWatch; tests should specify `us-east-1` when creating moto mock tables to match boto3 defaults.
