"""
Deploy web_search and check_warranty Lambda functions for AgentCore Gateway.

Run:
    python infrastructure/deploy_lambdas.py
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
LAMBDA_ROLE_NAME = "AgentCoreGatewayLambdaRole"

FUNCTIONS = [
    {
        "name": "agentcore-web-search",
        "handler": "handler.handler",
        "source_dir": "lambda/web_search",
        "description": "Tool 4: web_search via DuckDuckGo for AgentCore Gateway",
        "timeout": 30,
        "memory": 256,
        "runtime": "python3.12",
    },
    {
        "name": "agentcore-check-warranty",
        "handler": "handler.handler",
        "source_dir": "lambda/check_warranty",
        "description": "Tool 5: check_warranty for AgentCore Gateway",
        "timeout": 15,
        "memory": 128,
        "runtime": "python3.12",
    },
]


def get_account_id() -> str:
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def ensure_lambda_role(account_id: str) -> str:
    iam = boto3.client("iam")

    try:
        return iam.get_role(RoleName=LAMBDA_ROLE_NAME)["Role"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchEntity":
            raise

    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }
    arn = iam.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust),
        Description="Lambda execution role for AgentCore Gateway tools",
    )["Role"]["Arn"]

    iam.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    print(f"  Created IAM role {LAMBDA_ROLE_NAME}, waiting for propagation...")
    time.sleep(12)
    return arn


def build_zip(source_dir: str) -> bytes:
    """Package handler + pip-installed deps into a zip (standard x86_64)."""
    req_file = Path(source_dir) / "requirements.txt"
    content = req_file.read_text().strip() if req_file.exists() else ""
    has_deps = content and not content.startswith("#")

    tmp = tempfile.mkdtemp()
    try:
        # Copy Python source files
        for f in Path(source_dir).glob("*.py"):
            shutil.copy(f, tmp)

        # Install dependencies into same dir
        if has_deps:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file),
                 "-t", tmp, "-q", "--no-cache-dir"],
                check=True,
            )

        # Zip everything
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in Path(tmp).rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(tmp))
        return buf.getvalue()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def deploy_function(cfg: dict, role_arn: str, account_id: str) -> str:
    lam = boto3.client("lambda", region_name=REGION)
    name = cfg["name"]

    print(f"  Building zip for {name}...")
    zip_bytes = build_zip(cfg["source_dir"])

    try:
        existing = lam.get_function(FunctionName=name)
        print(f"  Updating existing function {name}...")
        lam.update_function_code(FunctionName=name, ZipFile=zip_bytes)
        return existing["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    print(f"  Creating function {name}...")
    resp = lam.create_function(
        FunctionName=name,
        Runtime=cfg["runtime"],
        Role=role_arn,
        Handler=cfg["handler"],
        Code={"ZipFile": zip_bytes},
        Description=cfg["description"],
        Timeout=cfg["timeout"],
        MemorySize=cfg["memory"],
    )

    # Allow AgentCore Gateway to invoke this Lambda
    try:
        lam.add_permission(
            FunctionName=name,
            StatementId="AgentCoreGatewayInvoke",
            Action="lambda:InvokeFunction",
            Principal="bedrock-agentcore.amazonaws.com",
            SourceAccount=account_id,
        )
    except lam.exceptions.ResourceConflictException:
        pass

    return resp["FunctionArn"]


def main():
    print("=" * 60)
    print("  Deploying Lambda tools for AgentCore Gateway")
    print("=" * 60)

    account_id = get_account_id()
    print(f"\nAccount: {account_id}  Region: {REGION}\n")

    print("Ensuring Lambda execution role...")
    role_arn = ensure_lambda_role(account_id)
    print(f"  Role ARN: {role_arn}\n")

    arns = {}
    for cfg in FUNCTIONS:
        print(f"Deploying {cfg['name']}...")
        arn = deploy_function(cfg, role_arn, account_id)
        arns[cfg["name"]] = arn
        print(f"  ARN: {arn}\n")

    print("=" * 60)
    print("Done! Now add Gateway targets by running:\n")
    print(
        f'agentcore add gateway-target \\\n'
        f'  --name WebSearchTarget \\\n'
        f'  --type lambda-function-arn \\\n'
        f'  --lambda-arn {arns["agentcore-web-search"]} \\\n'
        f'  --tool-schema-file lambda/web_search/tools.json \\\n'
        f'  --gateway CustomerSupportGateway\n'
    )
    print(
        f'agentcore add gateway-target \\\n'
        f'  --name CheckWarrantyTarget \\\n'
        f'  --type lambda-function-arn \\\n'
        f'  --lambda-arn {arns["agentcore-check-warranty"]} \\\n'
        f'  --tool-schema-file lambda/check_warranty/tools.json \\\n'
        f'  --gateway CustomerSupportGateway\n'
    )
    print("Then run:  agentcore deploy")
    print("=" * 60)

    return arns


if __name__ == "__main__":
    main()
