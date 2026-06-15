"""Generate architecture diagram for ShopEasy Customer Support Agent."""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.general import User, Client
from diagrams.aws.ml import Bedrock
from diagrams.aws.network import APIGateway
from diagrams.aws.compute import Lambda
from diagrams.aws.management import Cloudwatch
from diagrams.aws.storage import S3
from diagrams.programming.language import Python

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "1.0",
    "splines": "ortho",
    "nodesep": "0.9",
    "ranksep": "1.4",
    "fontname": "Helvetica",
}

node_attr = {
    "fontsize": "12",
    "fontname": "Helvetica",
}

with Diagram(
    "ShopEasy Customer Support Agent",
    filename="docs/architecture",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    user = User("Customer")

    with Cluster("Frontend"):
        streamlit = Client("Streamlit App\n(boto3 invoke)")

    with Cluster("AWS Bedrock AgentCore"):
        runtime = Bedrock("AgentCore Runtime\n(Strands Agent)")

        with Cluster("In-Process Tools"):
            t1 = Python("get_return_policy")
            t2 = Python("get_product_info")
            t3 = Python("get_technical_support")

        memory = Bedrock("AgentCore Memory\n(Semantic / per-user)")

        with Cluster("AgentCore Gateway  (MCP / no-auth)"):
            gateway = APIGateway("Gateway Endpoint")
            with Cluster("Lambda Functions"):
                lam_search = Lambda("web_search\n(DuckDuckGo)")
                lam_warranty = Lambda("check_warranty\n(Mock warranty DB)")

    bedrock_model = Bedrock("Amazon Bedrock\nus.amazon.nova-lite-v1:0")
    cw = Cloudwatch("CloudWatch\n(Traces + Logs)")
    s3 = S3("S3 Artifact Bucket\n(deploy only)")

    # Main request flow
    user >> Edge(label="chat") >> streamlit
    streamlit >> Edge(label="invoke_agent_runtime") >> runtime

    # Model
    runtime >> Edge(label="inference") >> bedrock_model

    # Direct tools
    runtime >> Edge(label="tool call") >> t1
    runtime >> Edge(label="tool call") >> t2
    runtime >> Edge(label="tool call") >> t3

    # Memory
    runtime >> Edge(label="read / write\nsession memory") >> memory

    # Gateway path
    runtime >> Edge(label="MCP") >> gateway
    gateway >> lam_search
    gateway >> lam_warranty

    # Observability
    runtime >> Edge(label="traces / logs", style="dashed") >> cw

    # Deployment artifact (dashed)
    s3 >> Edge(label="agent zip + lambda zips\n(deploy time)", style="dashed") >> runtime
