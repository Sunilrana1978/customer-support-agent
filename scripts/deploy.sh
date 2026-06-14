#!/usr/bin/env bash
# Full deployment script for the ShopEasy Customer Support AgentCore agent.
# Run from the project root: bash scripts/deploy.sh
set -euo pipefail

REGION="us-west-2"
export AWS_DEFAULT_REGION="$REGION"

echo "=================================================="
echo "  ShopEasy Customer Support Agent — Deployment"
echo "  AWS Bedrock AgentCore  |  Region: $REGION"
echo "=================================================="
echo

# ── Prerequisites ─────────────────────────────────────────
check_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found. $2"; exit 1; }; }

check_cmd aws    "Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
check_cmd node   "Install Node.js 20+: https://nodejs.org"
check_cmd python3 "Install Python 3.11+"
check_cmd npm    "Install Node.js (includes npm)"

# Install AgentCore CLI if not present
if ! command -v agentcore >/dev/null 2>&1; then
    echo "Installing AgentCore CLI..."
    npm install -g @aws/agentcore
fi

# Verify AWS credentials
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) \
    || { echo "ERROR: AWS credentials not configured. Run 'aws configure'"; exit 1; }

echo "AWS Account : $ACCOUNT_ID"
echo "Region      : $REGION"
echo

# ── Step 1: Patch aws-targets.json with real account ID ──
echo "Step 1/5  Configuring AgentCore targets..."
sed -i.bak "s/REPLACE_WITH_YOUR_ACCOUNT_ID/$ACCOUNT_ID/" agentcore/aws-targets.json
rm -f agentcore/aws-targets.json.bak
echo "  agentcore/aws-targets.json updated"
echo

# ── Step 2: Deploy Lambda functions ──────────────────────
echo "Step 2/5  Deploying Lambda functions (web_search, check_warranty)..."
python3 infrastructure/deploy_lambdas.py
echo

# ── Step 3: Retrieve Lambda ARNs ─────────────────────────
echo "Step 3/5  Fetching Lambda ARNs..."
WEB_SEARCH_ARN=$(python3 - <<'EOF'
import boto3, sys
try:
    c = boto3.client("lambda", region_name="us-west-2")
    print(c.get_function(FunctionName="agentcore-web-search")["Configuration"]["FunctionArn"])
except Exception as e:
    sys.exit(f"ERROR: {e}")
EOF
)
CHECK_WARRANTY_ARN=$(python3 - <<'EOF'
import boto3, sys
try:
    c = boto3.client("lambda", region_name="us-west-2")
    print(c.get_function(FunctionName="agentcore-check-warranty")["Configuration"]["FunctionArn"])
except Exception as e:
    sys.exit(f"ERROR: {e}")
EOF
)

echo "  web_search ARN    : $WEB_SEARCH_ARN"
echo "  check_warranty ARN: $CHECK_WARRANTY_ARN"
echo

# ── Step 4: Add Gateway targets ──────────────────────────
echo "Step 4/5  Adding Lambda targets to AgentCore Gateway..."

agentcore add gateway-target \
    --name WebSearchTarget \
    --type lambda-function-arn \
    --lambda-arn "$WEB_SEARCH_ARN" \
    --tool-schema-file lambda/web_search/tools.json \
    --gateway CustomerSupportGateway

agentcore add gateway-target \
    --name CheckWarrantyTarget \
    --type lambda-function-arn \
    --lambda-arn "$CHECK_WARRANTY_ARN" \
    --tool-schema-file lambda/check_warranty/tools.json \
    --gateway CustomerSupportGateway

echo "  Gateway targets added"
echo

# ── Step 5: Deploy to AgentCore ──────────────────────────
echo "Step 5/5  Deploying Runtime + Memory + Gateway to AgentCore..."
echo "  (This takes 5-10 minutes on first deploy)"
agentcore deploy -y

echo
echo "=================================================="
echo "  Deployment complete!"
echo "=================================================="
agentcore status
echo
echo "To launch the Streamlit app:"
echo "  1. Copy the Runtime ARN from 'agentcore status' above"
echo "  2. export AGENTCORE_RUNTIME_ARN=<paste ARN here>"
echo "  3. pip install -r streamlit_app/requirements.txt"
echo "  4. streamlit run streamlit_app/app.py"
echo "=================================================="
