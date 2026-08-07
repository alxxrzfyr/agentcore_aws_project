"""Mock refund processing Lambda for policy testing."""
import json
import random

def lambda_handler(event, context):
    delimiter = "___"
    original_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]

    if tool_name == "process_refund":
        order_id = event.get("order_id", "UNKNOWN")
        amount = event.get("amount", 0)
        reason = event.get("reason", "not specified")
        conf_id = f"REF-{random.randint(100000, 999999)}"
        return {
            "status": "SUCCESS",
            "message": f"Refund of ${amount} processed for order {order_id}. Reason: {reason}. Confirmation ID: {conf_id}",
            "confirmation_id": conf_id,
        }
    return {"error": f"Unknown tool: {tool_name}"}
