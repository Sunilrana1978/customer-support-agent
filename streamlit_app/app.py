"""
ShopEasy Customer Support — Streamlit frontend.
Invokes the AgentCore Runtime via boto3.

Usage:
    export AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:<account>:runtime/<id>
    streamlit run streamlit_app/app.py
"""

import json
import os
import uuid
from datetime import datetime

import boto3
import streamlit as st

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")


def get_runtime_arn() -> str:
    return os.environ.get("AGENTCORE_RUNTIME_ARN", "")


def invoke_agent(message: str, session_id: str, user_id: str, agent_arn: str) -> str:
    client = boto3.client("bedrock-agentcore", region_name=REGION)

    payload = json.dumps({
        "prompt": message,
        "session_id": session_id,
        "user_id": user_id,
    }).encode("utf-8")

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=payload,
        qualifier="DEFAULT",
    )

    chunks = []
    for chunk in response.get("response", []):
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode("utf-8"))
        elif isinstance(chunk, dict):
            raw = chunk.get("chunk", {})
            if isinstance(raw, dict):
                chunks.append(raw.get("bytes", b"").decode("utf-8"))
            elif isinstance(raw, bytes):
                chunks.append(raw.decode("utf-8"))

    raw_text = "".join(chunks)
    try:
        data = json.loads(raw_text)
        return data.get("result", raw_text)
    except json.JSONDecodeError:
        return raw_text


def main():
    st.set_page_config(
        page_title="ShopEasy Customer Support",
        page_icon="🛒",
        layout="centered",
    )

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/shopping-cart.png", width=60)
        st.title("ShopEasy Support")
        st.caption("Powered by AWS Bedrock AgentCore")
        st.divider()

        agent_arn = st.text_input(
            "AgentCore Runtime ARN",
            value=get_runtime_arn(),
            placeholder="arn:aws:bedrock-agentcore:us-west-2:...",
            help="Run `agentcore status` to get your ARN after deployment",
        )

        user_id = st.text_input(
            "Customer ID",
            value="customer-001",
            help="Used to scope conversation memory per customer",
        )

        st.divider()
        if st.button("New Conversation", use_container_width=True):
            st.session_state.session_id = f"{user_id}-{uuid.uuid4().hex}"
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.markdown("**Try these examples:**")
        examples = [
            "What's the return policy for electronics?",
            "Tell me about product PROD-002",
            "My PROD-001 won't connect via Bluetooth",
            "Check warranty for PROD-002, purchased 2025-01-10",
            "Search for wireless headphone reviews 2025",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True, key=ex):
                st.session_state.pending_message = ex

        st.divider()
        if "session_id" in st.session_state:
            st.caption(f"Session ID:\n`{st.session_state.session_id}`")

    # ── State init ───────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"{user_id}-{uuid.uuid4().hex}"

    # ── Main chat area ───────────────────────────────────────
    st.title("Customer Support")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Pick up example button clicks or typed input
    prompt = st.session_state.pop("pending_message", None) or st.chat_input(
        "How can I help you today?"
    )

    if prompt:
        if not agent_arn:
            st.error(
                "Enter your AgentCore Runtime ARN in the sidebar.\n\n"
                "Get it by running: `agentcore status`"
            )
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = invoke_agent(
                        message=prompt,
                        session_id=st.session_state.session_id,
                        user_id=user_id,
                        agent_arn=agent_arn,
                    )
                    st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as exc:
                    err = f"**Error:** {exc}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})


if __name__ == "__main__":
    main()
