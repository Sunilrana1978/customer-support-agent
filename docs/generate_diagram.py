"""
Generate architecture diagram for ShopEasy Customer Support Agent.
Layout: Customer → Frontend (left) | AWS Bedrock AgentCore box (right).
"""

import graphviz

ICONS = "/Users/sunilkumar/.pyenv/versions/python_env_3_11/lib/python3.11/site-packages/resources"

def icon(path):
    return f"{ICONS}/{path}"

C_AGENTCORE = "#E8F4FD"
C_GATEWAY   = "#FEF9E7"
C_TOOLS     = "#EAFAF1"
C_FRONTEND  = "#F2F3F4"
C_BORDER    = "#AEB6BF"

C_MAIN = "#2E86AB"
C_MEM  = "#27AE60"
C_INF  = "#8E44AD"
C_GW   = "#E67E22"
C_OBS  = "#95A5A6"


def node(g, name, label, img, fontsize="9"):
    g.node(name,
        label=label, shape="none",
        image=icon(img), imagescale="true", imagepos="tc", labelloc="b",
        width="1.0", height="1.2", fixedsize="false",
        fontsize=fontsize, fontname="Helvetica Neue")


def edge(g, src, dst, label="", color="#555", style="solid", fontsize="8"):
    g.edge(src, dst,
        label=label, color=color, fontcolor=color,
        style=style, fontsize=fontsize, fontname="Helvetica Neue",
        penwidth="1.3", arrowsize="0.65")


g = graphviz.Digraph("ShopEasy Customer Support Agent", engine="dot", format="png")

g.attr(
    rankdir="LR",
    bgcolor="white",
    pad="0.6",
    nodesep="0.45",
    ranksep="1.0",
    splines="polyline",
    fontname="Helvetica Neue",
    dpi="150",
)

# ── Left side: Customer + Frontend ───────────────────────────────────────────
node(g, "user", "Customer", "aws/general/user.png")

with g.subgraph(name="cluster_frontend") as cf:
    cf.attr(label="Frontend", style="filled,rounded",
            color=C_BORDER, fillcolor=C_FRONTEND,
            fontname="Helvetica Neue", fontsize="10", margin="12")
    node(cf, "streamlit", "Streamlit\n(boto3)", "aws/general/client.png")

# ── Right side: AWS Bedrock AgentCore ────────────────────────────────────────
with g.subgraph(name="cluster_agentcore") as ac:
    ac.attr(label="AWS Bedrock AgentCore",
            style="filled,rounded", color=C_BORDER, fillcolor=C_AGENTCORE,
            fontname="Helvetica Neue Bold", fontsize="12", margin="20")

    node(ac, "runtime",      "AgentCore Runtime\n(Strands Agent)", "aws/ml/bedrock.png")
    node(ac, "memory",       "AgentCore Memory\n(Semantic)",       "aws/ml/bedrock.png")
    node(ac, "bedrock_model","Amazon Bedrock\nNova Lite v1",       "aws/ml/bedrock.png")
    node(ac, "cw",           "CloudWatch\nTraces + Logs",          "aws/management/cloudwatch.png")

    with ac.subgraph(name="cluster_tools") as ct:
        ct.attr(label="Direct Tools  ·  in-process",
                style="filled,rounded", color=C_BORDER, fillcolor=C_TOOLS,
                fontname="Helvetica Neue", fontsize="10", margin="12")
        node(ct, "tools",
             "get_return_policy\nget_product_info\nget_technical_support",
             "programming/language/python.png", fontsize="8.5")

    with ac.subgraph(name="cluster_gateway") as cg:
        cg.attr(label="AgentCore Gateway  ·  MCP",
                style="filled,rounded", color=C_BORDER, fillcolor=C_GATEWAY,
                fontname="Helvetica Neue", fontsize="10", margin="12")
        node(cg, "gateway",      "Gateway\n(no-auth)",             "aws/network/api-gateway.png")
        node(cg, "lam_search",   "web_search\n(DuckDuckGo)",       "aws/compute/lambda.png")
        node(cg, "lam_warranty", "check_warranty\n(Warranty DB)",  "aws/compute/lambda.png")

# ── Edges ────────────────────────────────────────────────────────────────────
edge(g, "user",      "streamlit",     "chat",                 C_MAIN)
edge(g, "streamlit", "runtime",       "invoke_agent_runtime", C_MAIN)
edge(g, "runtime",   "memory",        "session memory",       C_MEM)
edge(g, "runtime",   "tools",         "tool call",            C_MEM)
edge(g, "runtime",   "gateway",       "MCP",                  C_GW)
edge(g, "gateway",   "lam_search",    "",                     C_GW)
edge(g, "gateway",   "lam_warranty",  "",                     C_GW)
edge(g, "runtime",   "bedrock_model", "inference",            C_INF)
edge(g, "runtime",   "cw",            "traces",               C_OBS, style="dashed")

# ── Render ───────────────────────────────────────────────────────────────────
g.render("docs/architecture", cleanup=True)
print("Generated docs/architecture.png")
