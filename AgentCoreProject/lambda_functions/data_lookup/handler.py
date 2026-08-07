"""Data Lookup Lambda - Queries DynamoDB tables for order, customer, and product information.

This Lambda is invoked by AgentCore Gateway. The tool name (order_lookup, user_lookup,
or product_lookup) comes from context.client_context.custom['bedrockAgentCoreToolName'].
The event object contains the input properties defined in the tool spec.
"""

import json
import boto3

# DynamoDB client for us-west-2
dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

# Table references
CUSTOMERS_TABLE = dynamodb.Table("workshop-customers")
ORDERS_TABLE = dynamodb.Table("workshop-orders")
PRODUCTS_TABLE = dynamodb.Table("workshop-products")


def lambda_handler(event: dict, context) -> dict:
    """Route to the correct lookup based on the gateway tool name."""
    # Extract tool name from gateway context (format: target_name___tool_name)
    delimiter = "___"
    original_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]

    if tool_name == "order_lookup":
        return handle_order_lookup(event)
    elif tool_name == "user_lookup":
        return handle_user_lookup(event)
    elif tool_name == "product_lookup":
        return handle_product_lookup(event)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def handle_order_lookup(event: dict) -> dict:
    """Query workshop-orders by customer_id. Returns all orders for that customer."""
    customer_id = event.get("customer_id", "")
    if not customer_id:
        return {"error": "customer_id is required"}

    response = ORDERS_TABLE.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("customer_id").eq(customer_id)
    )
    items = response.get("Items", [])

    if not items:
        return {"message": f"No orders found for customer {customer_id}"}

    # Enrich each order with product details
    enriched_orders = []
    for order in items:
        product_id = order.get("product_id", "")
        product_info = PRODUCTS_TABLE.get_item(Key={"product_id": product_id}).get("Item", {})
        enriched_orders.append({
            "customer_id": order.get("customer_id"),
            "product_id": product_id,
            "product_name": product_info.get("product_name", "Unknown"),
            "product_category": product_info.get("product_category", "Unknown"),
            "provider": product_info.get("provider", "Unknown"),
            "status": order.get("status"),
            "purchased_date": order.get("purchased_date"),
        })

    return {"orders": enriched_orders, "count": len(enriched_orders)}


def handle_user_lookup(event: dict) -> dict:
    """Get customer info from workshop-customers by customer_id."""
    customer_id = event.get("customer_id", "")
    if not customer_id:
        return {"error": "customer_id is required"}

    response = CUSTOMERS_TABLE.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")

    if not item:
        return {"error": f"Customer {customer_id} not found"}

    return {
        "customer_id": item.get("customer_id"),
        "name": item.get("name"),
        "country_code": item.get("country_code"),
    }


def handle_product_lookup(event: dict) -> dict:
    """Get product info from workshop-products by product_id."""
    product_id = event.get("product_id", "")
    if not product_id:
        return {"error": "product_id is required"}

    response = PRODUCTS_TABLE.get_item(Key={"product_id": product_id})
    item = response.get("Item")

    if not item:
        return {"error": f"Product {product_id} not found"}

    return {
        "product_id": item.get("product_id"),
        "product_name": item.get("product_name"),
        "provider": item.get("provider"),
        "product_category": item.get("product_category"),
    }
