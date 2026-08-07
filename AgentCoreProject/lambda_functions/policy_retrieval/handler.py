"""Policy Retrieval Lambda - Queries the Bedrock Knowledge Base for return policy information.

This Lambda is invoked by AgentCore Gateway. It reads the Knowledge Base ID from
SSM Parameter Store and uses the Bedrock Agent Runtime retrieve API to find
relevant policy excerpts.
"""

import json
import boto3

REGION = "us-west-2"
SSM_KB_PARAM = "/app/workshop/kb/knowledge-base-id"

# Clients
ssm = boto3.client("ssm", region_name=REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

# Cache the KB ID after first lookup
_kb_id: str | None = None


def get_knowledge_base_id() -> str:
    """Retrieve the Knowledge Base ID from SSM (cached after first call)."""
    global _kb_id
    if _kb_id is None:
        response = ssm.get_parameter(Name=SSM_KB_PARAM)
        _kb_id = response["Parameter"]["Value"]
    return _kb_id


def lambda_handler(event: dict, context) -> dict:
    """Retrieve return policy information from the Bedrock Knowledge Base."""
    query = event.get("query", "")
    if not query:
        return {"error": "query is required"}

    kb_id = get_knowledge_base_id()

    # Use the Bedrock Agent Runtime retrieve API
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
            }
        },
    )

    # Extract relevant text from results
    results = response.get("retrievalResults", [])
    if not results:
        return {"message": "No relevant policy information found", "query": query}

    excerpts = []
    for result in results:
        text = result.get("content", {}).get("text", "")
        score = result.get("score", 0)
        if text:
            excerpts.append({"text": text, "relevance_score": score})

    return {
        "query": query,
        "policy_excerpts": excerpts,
        "result_count": len(excerpts),
    }
