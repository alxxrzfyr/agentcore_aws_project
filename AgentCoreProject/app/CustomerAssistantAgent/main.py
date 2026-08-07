from typing import Any
from collections import OrderedDict
from datetime import datetime, timedelta
import os
import uuid

from strands import Agent, tool
import asyncio
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from strands_tools import current_time
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

# --- System Prompt ---
# Defines the agent's persona as a Returns & Refunds specialist.
DEFAULT_SYSTEM_PROMPT = """You are a Returns & Refunds Assistant. You help administrators with:
- Looking up customer orders and account information
- Checking return eligibility for customer orders
- Calculating refund amounts based on product condition and return reason
- Answering questions about return policies for different countries and categories

The user is an administrator who can access all customer data, orders, and return policies.
Be helpful and concise. Always confirm details before processing any return or refund.
Use available tools to look up real data rather than making assumptions."""


# --- Mock Data Removed ---
# Real data now comes from DynamoDB and Knowledge Base through the AgentCore Gateway.
# The gateway MCP client (configured in mcp_client/client.py) exposes:
#   - data-lookup___order_lookup
#   - data-lookup___user_lookup
#   - data-lookup___product_lookup
#   - policy-retrieval___policy_retrieval


# --- Tools List ---
# current_time is a local tool; the gateway tools are discovered via the MCP client.
tools = [current_time]

_INLINE_FUNCTION_NAMES: set[str] = set()

# The MCP client is passed as a tool to Agent directly (not pre-started at module level)
# because the Agent constructor manages its lifecycle.


# --- Memory Configuration ---
# The memory ID is passed via environment variable (set in agentcore.json for deployed,
# .env.local for local dev).
MEMORY_ID = os.environ.get("MEMORY_ID", "")
MEMORY_REGION = "us-west-2"
# The actor_id identifies who is using the agent. Default to "administrator" for this workshop.
DEFAULT_ACTOR_ID = "administrator"


def _make_conversation_manager():
    return NullConversationManager()


def _create_memory_session_manager(session_id: str, actor_id: str = DEFAULT_ACTOR_ID):
    """Create an AgentCore Memory session manager for cross-session recall.

    The namespace pattern must match what was configured in agentcore.json:
    /users/{actorId}/preferences
    """
    if not MEMORY_ID:
        log.warning("MEMORY_ID not set; running without persistent memory.")
        return None

    # Build retrieval config using the namespace from agentcore.json.
    # Use the exact template with {actorId} placeholder that the SDK will resolve.
    namespace = f"/users/{actor_id}/preferences/"

    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            namespace: RetrievalConfig(
                top_k=10,
                relevance_score=0.3,  # Low threshold for testing
            )
        },
    )
    return AgentCoreMemorySessionManager(config, region_name=MEMORY_REGION)


# Reuses one Agent per session_id so each session keeps its own in-process
# conversation history (best-effort; resets on cold start). The cache is bounded
# to 128 sessions with LRU eviction (least-recently-used is dropped and its
# history reset) so a single process serving many sessions cannot leak history
# between them or grow without limit. Memory provides durable cross-session recall.
def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)

        # Create a memory session manager for this session
        session_manager = _create_memory_session_manager(session_id)

        # Build tools list: local tools + MCP gateway client
        agent_tools = list(tools)  # copy the base tools list
        for mcp_client in mcp_clients:
            if mcp_client:
                agent_tools.append(mcp_client)

        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=agent_tools,
            conversation_manager=_make_conversation_manager(),
            session_manager=session_manager,
            hooks=[
            ],
        )
        return cache[session_id]
    return get_or_create_agent
get_or_create_agent = agent_factory()


def strip_trailing_tool_use(messages: Any) -> list[dict]:
    """Strip toolUse blocks from the tail until the last message has none."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original_content = last.get("content", [])
        if not isinstance(original_content, list) or not all(isinstance(block, dict) for block in original_content):
            raise ValueError("each message content value must be a list of content blocks")

        content = [block for block in original_content if "toolUse" not in block]
        if len(content) == len(original_content):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()

    return messages


def _extract_prompt(payload: dict):
    """Accept validated harness messages, tool results, or a plain prompt string."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        tool_results = payload["tool_results"]
        if not isinstance(tool_results, list) or not all(
            isinstance(tool_result, dict) and isinstance(tool_result.get("toolUseId"), str)
            for tool_result in tool_results
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in tool_results]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt


def _has_inline_function_call(messages) -> bool:
    """Return True if messages contains an assistant toolUse for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES or not isinstance(messages, list):
        return False
    for msg in messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse", {}).get("name") in _INLINE_FUNCTION_NAMES:
                    return True
    return False


def _is_inline_function_call(event: dict) -> bool:
    """Check if a contentBlockStart event is for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES:
        return False
    cbs = event.get("contentBlockStart", {})
    start = cbs.get("start", {})
    tool_use = start.get("toolUse") if isinstance(start, dict) else None
    return tool_use is not None and tool_use.get("name") in _INLINE_FUNCTION_NAMES



@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")


    session_id = getattr(context, 'session_id', None) or str(uuid.uuid4())
    agent = get_or_create_agent(session_id)

    prompt = _extract_prompt(payload)


    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
