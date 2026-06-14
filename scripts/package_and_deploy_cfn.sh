#!/usr/bin/env bash
# Package all artifacts and deploy the CloudFormation stack.
# Run from the project root: bash scripts/package_and_deploy_cfn.sh
#
# What this script does:
#   1. Creates the S3 artifact bucket (if it doesn't exist)
#   2. Packages the agent code (ARM64 deps) and uploads to S3
#   3. Packages each Lambda function (x86_64) and uploads to S3
#   4. Uploads tool schema JSON files to S3
#   5. Deploys (or updates) the CloudFormation stack
#   6. Prints key outputs (Runtime ARN, Gateway URL, Memory ID)
set -euo pipefail

# ── Config ────────────────────────────────────────────────
REGION="us-west-2"
STACK_NAME="shopeasy-customer-support-agent"
ENVIRONMENT="prod"
PYTHON_VERSION="3.12"

export AWS_DEFAULT_REGION="$REGION"

# ── Derive account ID ─────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ARTIFACT_BUCKET="shopeasy-agentcore-artifacts-${ACCOUNT_ID}-${REGION}"

echo "=================================================="
echo "  ShopEasy Customer Support — CloudFormation Deploy"
echo "  Account : $ACCOUNT_ID"
echo "  Region  : $REGION"
echo "  Bucket  : $ARTIFACT_BUCKET"
echo "  Stack   : $STACK_NAME"
echo "=================================================="
echo

# ── Step 1: Ensure S3 artifact bucket exists ─────────────
echo "Step 1/5  Ensuring S3 artifact bucket..."
if ! aws s3api head-bucket --bucket "$ARTIFACT_BUCKET" 2>/dev/null; then
    aws s3api create-bucket \
        --bucket "$ARTIFACT_BUCKET" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
    aws s3api put-bucket-versioning \
        --bucket "$ARTIFACT_BUCKET" \
        --versioning-configuration Status=Enabled
    echo "  Created bucket: $ARTIFACT_BUCKET"
else
    echo "  Bucket already exists: $ARTIFACT_BUCKET"
fi
echo

# ── Step 2: Package agent code (ARM64 for AgentCore Runtime) ─
echo "Step 2/5  Packaging agent code (ARM64 / Graviton)..."
AGENT_BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$AGENT_BUILD_DIR"' EXIT

# Copy agent source files
cp app/CustomerSupportAgent/main.py          "$AGENT_BUILD_DIR/"
cp app/CustomerSupportAgent/tools.py         "$AGENT_BUILD_DIR/"
mkdir -p "$AGENT_BUILD_DIR/memory"
cp app/CustomerSupportAgent/memory/__init__.py "$AGENT_BUILD_DIR/memory/"
cp app/CustomerSupportAgent/memory/session.py  "$AGENT_BUILD_DIR/memory/"

# Install ARM64-compatible dependencies
echo "  Installing ARM64 dependencies (this may take a few minutes)..."
pip install \
    --platform manylinux2014_aarch64 \
    --python-version "$PYTHON_VERSION" \
    --implementation cp \
    --target "$AGENT_BUILD_DIR" \
    --only-binary :all: \
    --quiet \
    bedrock-agentcore \
    strands-agents \
    boto3 \
    mcp 2>/dev/null || {
        echo "  WARNING: Some packages may not have ARM64 wheels."
        echo "  Falling back to standard pip install (may not be ARM64 compatible)."
        pip install \
            --target "$AGENT_BUILD_DIR" \
            --quiet \
            bedrock-agentcore strands-agents boto3 mcp
    }

# Zip the agent package
AGENT_ZIP="$(pwd)/.build/agent_deployment.zip"
mkdir -p "$(pwd)/.build"
(cd "$AGENT_BUILD_DIR" && zip -r "$AGENT_ZIP" . -q)
echo "  Agent zip: $AGENT_ZIP ($(du -sh "$AGENT_ZIP" | cut -f1))"

# Upload
aws s3 cp "$AGENT_ZIP" "s3://$ARTIFACT_BUCKET/agent/deployment.zip" --quiet
echo "  Uploaded: s3://$ARTIFACT_BUCKET/agent/deployment.zip"
echo

# ── Step 3: Package Lambda functions (x86_64) ────────────
echo "Step 3/5  Packaging Lambda functions..."

package_lambda() {
    local name="$1"
    local source_dir="$2"
    local s3_key="$3"

    local build_dir
    build_dir=$(mktemp -d)

    # Copy handler
    cp "$source_dir/handler.py" "$build_dir/"

    # Install dependencies if any
    local req="$source_dir/requirements.txt"
    if [[ -f "$req" ]]; then
        local content
        content=$(grep -v '^\s*#' "$req" | grep -v '^\s*$' || true)
        if [[ -n "$content" ]]; then
            pip install -r "$req" -t "$build_dir" --quiet
        fi
    fi

    local zip_path=".build/${name}.zip"
    (cd "$build_dir" && zip -r "$(pwd)/../../$zip_path" . -q 2>/dev/null || \
     cd "$build_dir" && zip -r "$(realpath "../../$zip_path")" . -q)
    zip_path=".build/${name}.zip"

    aws s3 cp "$zip_path" "s3://$ARTIFACT_BUCKET/$s3_key" --quiet
    echo "  $name → s3://$ARTIFACT_BUCKET/$s3_key ($(du -sh "$zip_path" | cut -f1))"
    rm -rf "$build_dir"
}

mkdir -p .build
package_lambda "web_search"     "lambda/web_search"     "lambda/web_search.zip"
package_lambda "check_warranty" "lambda/check_warranty" "lambda/check_warranty.zip"
echo

# ── Step 4: Upload tool schemas ───────────────────────────
echo "Step 4/5  Uploading MCP tool schemas..."
aws s3 cp lambda/web_search/tools.json    "s3://$ARTIFACT_BUCKET/schemas/web_search_tools.json"    --quiet
aws s3 cp lambda/check_warranty/tools.json "s3://$ARTIFACT_BUCKET/schemas/check_warranty_tools.json" --quiet
echo "  Uploaded: schemas/web_search_tools.json"
echo "  Uploaded: schemas/check_warranty_tools.json"
echo

# ── Step 5: Deploy CloudFormation stack ───────────────────
echo "Step 5/5  Deploying CloudFormation stack '$STACK_NAME'..."
echo "  (First deploy takes ~10 minutes)"

aws cloudformation deploy \
    --template-file infrastructure/cloudformation.yaml \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ArtifactBucket="$ARTIFACT_BUCKET" \
        AgentCodeKey="agent/deployment.zip" \
        WebSearchLambdaKey="lambda/web_search.zip" \
        CheckWarrantyLambdaKey="lambda/check_warranty.zip" \
        WebSearchToolSchemaKey="schemas/web_search_tools.json" \
        CheckWarrantyToolSchemaKey="schemas/check_warranty_tools.json" \
        Environment="$ENVIRONMENT" \
    --tags \
        Project=ShopEasySupport \
        Environment="$ENVIRONMENT" \
    --no-fail-on-empty-changeset

echo

# ── Print outputs ─────────────────────────────────────────
echo "=================================================="
echo "  Stack outputs"
echo "=================================================="
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

RUNTIME_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`RuntimeArn`].OutputValue' \
    --output text)

echo
echo "=================================================="
echo "  To run the Streamlit app:"
echo ""
echo "  export AGENTCORE_RUNTIME_ARN=\"$RUNTIME_ARN\""
echo "  pip install -r streamlit_app/requirements.txt"
echo "  streamlit run streamlit_app/app.py"
echo "=================================================="

# Clean up build dir
rm -rf .build
