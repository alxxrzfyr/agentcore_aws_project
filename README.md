# AgentCore AWS Workshop: Returns & Refunds Assistant

A production-grade AI agent built with the **AWS Bedrock AgentCore CLI** and the **Strands Agents SDK**. This project demonstrates the complete lifecycle of building, deploying, and managing an intelligent returns and refunds assistant on AWS, from initial scaffolding through to Cedar-based access control and observability.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [How It Works](#how-it-works)
- [Data Model](#data-model)
- [Gateway and Tools](#gateway-and-tools)
- [Cedar Access Control](#cedar-access-control)
- [Memory and Session Management](#memory-and-session-management)
- [Observability](#observability)
- [Agent Harness and Evaluations](#agent-harness-and-evaluations)
- [Workshop Labs Completed](#workshop-labs-completed)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Running the Streamlit UI](#running-the-streamlit-ui)
- [Example Interactions](#example-interactions)
- [Configuration Reference](#configuration-reference)
- [Lessons Learned](#lessons-learned)
- [License](#license)

## Overview

This project was developed as part of the AWS AgentCore CLI Workshop. It showcases how to build a conversational AI agent that handles customer return and refund workflows using:

- **Amazon Bedrock** foundation models (Claude Sonnet 4.5) for natural language understanding
- **Amazon DynamoDB** for customer, order, and product data persistence
- **Amazon Bedrock Knowledge Bases** for RAG-powered return policy retrieval across US, UK, and India
- **Amazon Cognito** for OAuth 2.0 authentication (both M2M and user flows)
- **Cedar policies** for fine-grained, parameter-level access control at the gateway boundary
- **OpenTelemetry** for structured logging, distributed tracing, and the GenAI observability dashboard

The agent is deployed to the AgentCore Runtime and accessed either through a Streamlit chat UI or directly via the AgentCore CLI.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Streamlit Chat UI                          │
│               (Cognito Auth + Streaming Responses)                │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   AgentCore Runtime (AWS)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │            CustomerAssistantAgent (Strands SDK)             │  │
│  │  - Claude Sonnet 4.5 via Bedrock                           │  │
│  │  - System Prompt (Returns & Refunds persona)               │  │
│  │  - Session Manager (cross-session memory)                  │  │
│  │  - MCP Client (gateway connectivity)                       │  │
│  └────────────┬──────────────────────┬───────────────────────┘  │
│               │                      │                           │
│               ▼                      ▼                           │
│  ┌────────────────────┐  ┌───────────────────────────────────┐  │
│  │  AgentCore Memory  │  │     AgentCore Gateway (MCP)       │  │
│  │  (User Preferences │  │  ┌────────────────────────────┐   │  │
│  │   7-day retention) │  │  │ data-lookup (Lambda)       │   │  │
│  │                    │  │  │  - order_lookup            │   │  │
│  │  Namespace:        │  │  │  - user_lookup             │   │  │
│  │  /users/{actorId}  │  │  │  - product_lookup          │   │  │
│  │  /preferences      │  │  ├────────────────────────────┤   │  │
│  └────────────────────┘  │  │ policy-retrieval (Lambda)  │   │  │
│                          │  │  - policy_retrieval (RAG)   │   │  │
│                          │  ├────────────────────────────┤   │  │
│                          │  │ refund-target (Lambda)     │   │  │
│                          │  │  - process_refund          │   │  │
│                          │  └────────────────────────────┘   │  │
│                          │                                    │  │
│                          │  Auth: Custom JWT (Cognito)        │  │
│                          │  Policies: Cedar (permit/forbid)   │  │
│                          └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                       │                           │
          ┌────────────┴────────────┐    ┌────────┴─────────────┐
          │      DynamoDB           │    │  Bedrock Knowledge   │
          │  ┌─────────────────┐    │    │  Base (TVITUMHKVK)   │
          │  │workshop-customers│    │    │                      │
          │  │workshop-orders   │    │    │  Return policies for │
          │  │workshop-products │    │    │  US, UK, India across│
          │  └─────────────────┘    │    │  all product categories│
          └─────────────────────────┘    └──────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| Conversational Agent | Built with Strands Agents SDK on Claude Sonnet 4.5 with streaming responses |
| Persistent Memory | Cross-session user preference recall via AgentCore Memory (7-day TTL) |
| Real Data Access | DynamoDB queries for customers, orders, and products with automatic enrichment |
| Policy Retrieval | RAG-powered return policy lookup from a vector-indexed Knowledge Base |
| Refund Processing | Tool-based refund workflow with Cedar-enforced amount constraints |
| Gateway Architecture | MCP-protocol gateway with OAuth client_credentials authentication |
| Cedar Policies | Fine-grained access control: read tools permitted, refunds capped at $500 |
| Streamlit UI | Web chat interface with Cognito USER_PASSWORD_AUTH login flow |
| Agent Harness | Testing harness with browser, code interpreter, and gateway tool access |
| Evaluations | On-demand quality evaluation (helpfulness, goal success rate scoring) |
| Observability | OTEL structured logs, distributed traces with session IDs, GenAI dashboard |

## Project Structure

```
AgentCoreProject/
├── app/
│   ├── CustomerAssistantAgent/        # Main agent application
│   │   ├── main.py                    # Agent entrypoint (Strands SDK)
│   │   ├── mcp_client/
│   │   │   └── client.py             # MCP gateway client with OAuth token caching
│   │   ├── model/
│   │   │   ├── load.py               # BedrockModel loader (Claude Sonnet 4.5)
│   │   │   └── mantle_compat.py      # OpenAI-compat workaround for Mantle
│   │   ├── skills/
│   │   │   └── fetcher.py            # Skills module
│   │   ├── pyproject.toml            # Python dependencies (strands, bedrock-agentcore)
│   │   └── .gitignore
│   └── CustAssistantHarness/         # Testing harness
│       ├── harness.json              # Browser + code interpreter + gateway tools
│       └── system-prompt.md          # Harness system prompt
├── lambda_functions/
│   ├── data_lookup/
│   │   └── handler.py               # DynamoDB multi-tool Lambda
│   ├── policy_retrieval/
│   │   └── handler.py               # Knowledge Base RAG Lambda
│   └── refund_processing/
│       └── handler.py               # Refund processing Lambda
├── tool_specs/
│   ├── data_lookup.json             # Schema: order_lookup, user_lookup, product_lookup
│   ├── policy_retrieval.json        # Schema: policy_retrieval
│   └── refund_processing.json       # Schema: process_refund
├── policies/
│   ├── allow_read_tools.cedar       # Permit all authenticated callers on read tools
│   └── refund_limit.cedar           # Permit refunds only when amount < 500
├── streamlit-ui/
│   └── streamlit_app.py             # Chat UI with Cognito login + streaming
├── agentcore/
│   ├── agentcore.json               # Main declarative project configuration
│   ├── aws-targets.json             # Deployment target (us-west-2)
│   ├── .env.local.example           # Template for local development secrets
│   ├── .llm-context/                # TypeScript schema definitions for AI assistants
│   ├── .cli/
│   │   └── deployed-state.json      # Tracks deployed resource IDs
│   └── cdk/                          # CDK infrastructure (@aws/agentcore-cdk)
├── AGENTS.md                         # AI assistant context document
└── README.md
```

## Technology Stack

| Layer | Component | Technology |
|-------|-----------|------------|
| Agent | Framework | Strands Agents SDK (`strands-agents >= 1.15.0`) |
| Agent | Foundation Model | Claude Sonnet 4.5 (`global.anthropic.claude-sonnet-4-5-20250929-v1:0`) |
| Agent | Built-in Tools | `strands-agents-tools` (current_time) |
| Infra | IaC | AWS CDK via `@aws/agentcore-cdk` L3 constructs |
| Infra | Deployment | AgentCore CLI (`agentcore deploy`) |
| Data | Persistence | Amazon DynamoDB (3 tables) |
| Data | RAG | Amazon Bedrock Knowledge Bases (vector search) |
| Auth | User Auth | Amazon Cognito User Pools (USER_PASSWORD_AUTH) |
| Auth | M2M Auth | Amazon Cognito App Client (client_credentials) |
| Auth | Gateway Auth | Custom JWT Authorizer (Cognito OIDC discovery) |
| Access | Policy Engine | Cedar Policy Language |
| Gateway | Protocol | MCP (Model Context Protocol) over StreamableHTTP |
| UI | Framework | Streamlit (port 8501) |
| Ops | Logging | OpenTelemetry (OTEL) structured logs |
| Ops | Tracing | Distributed traces with session correlation |
| Ops | Dashboard | AWS GenAI Observability Dashboard |

## How It Works

### Request Flow

1. **User sends message** via Streamlit UI or `agentcore invoke`
2. **Cognito authenticates** the request (USER_PASSWORD_AUTH for UI, IAM for CLI)
3. **AgentCore Runtime** receives the payload and routes to the agent process
4. **Strands Agent** processes the message with Claude Sonnet 4.5
5. **Agent decides** which tools to call based on the conversation context
6. **MCP Client** authenticates to the gateway (client_credentials OAuth)
7. **Gateway** validates the JWT, checks Cedar policies, and invokes the Lambda target
8. **Lambda** executes (DynamoDB query, KB retrieval, or refund processing)
9. **Response streams** back through the agent to the UI in real-time
10. **Memory** extracts and stores user preferences for future sessions

### Agent Architecture (main.py)

The agent uses a factory pattern with LRU session caching:

```python
# Session-cached agent factory (max 128 concurrent sessions)
get_or_create_agent = agent_factory()

# Each session gets its own:
# - Conversation history (in-process, best-effort)
# - Memory session manager (durable, cross-session)
# - MCP gateway client (shared OAuth token cache)
```

Key design decisions:
- **NullConversationManager**: Disables automatic truncation since the agent manages its own context
- **strip_trailing_tool_use()**: Normalizes message history from harness callers to prevent malformed invocations
- **Streaming async**: Uses `agent.stream_async()` for real-time token delivery to the UI

## Data Model

### DynamoDB Tables

| Table | Partition Key | Description |
|-------|--------------|-------------|
| `workshop-customers` | `customer_id` | Customer profiles (name, country_code) |
| `workshop-orders` | `customer_id` | Orders with product_id, status, purchased_date |
| `workshop-products` | `product_id` | Product catalog (name, provider, category) |

### Sample Data

```
Customers: C-01 (Rajesh, IN), C-02 (Sarah, UK), C-03 (Mike, US)
Products:  Electronics, Clothing, Home & Kitchen, Books
Orders:    Various statuses (delivered, shipped, processing)
```

### Knowledge Base

The Bedrock Knowledge Base contains return policy documents covering:
- **United States**: 30-day return window, free returns on most items
- **United Kingdom**: 14-day cooling-off period (Consumer Rights Act 2015)
- **India**: 7-10 day return window depending on category

Policies vary by product category (electronics have shorter windows, clothing requires tags attached, etc.).

## Gateway and Tools

The AgentCore Gateway exposes three Lambda targets as MCP tools:

### data-lookup target

| Tool | Parameters | Returns |
|------|-----------|---------|
| `order_lookup` | `customer_id` (string) | Orders with enriched product details |
| `user_lookup` | `customer_id` (string) | Customer name and country code |
| `product_lookup` | `product_id` (string) | Product name, provider, category |

The `order_lookup` tool automatically enriches each order with product details by joining against the products table.

### policy-retrieval target

| Tool | Parameters | Returns |
|------|-----------|---------|
| `policy_retrieval` | `query` (string) | Relevance-scored policy excerpts (top 5) |

Uses the Bedrock Agent Runtime `retrieve` API with vector search. The Knowledge Base ID is fetched from SSM Parameter Store and cached.

### refund-target

| Tool | Parameters | Returns |
|------|-----------|---------|
| `process_refund` | `order_id`, `amount` (int), `reason` | Confirmation ID or policy denial |

Subject to Cedar policy enforcement: refunds over $500 are denied at the gateway boundary before the Lambda even executes.

## Cedar Access Control

Cedar policies provide declarative, auditable access control at the gateway layer:

### allow_read_tools.cedar
```cedar
// Allow any authenticated caller to invoke read-only tools
permit(
  principal,
  action in [
    Action::"data-lookup___order_lookup",
    Action::"data-lookup___user_lookup",
    Action::"data-lookup___product_lookup",
    Action::"policy-retrieval___policy_retrieval"
  ],
  resource
);
```

### refund_limit.cedar
```cedar
// Allow refunds under $500 for any authenticated caller
permit(
  principal,
  action == Action::"refund-target___process_refund",
  resource
) when {
  context.input.amount < 500
};
```

**Key insight**: Cedar evaluates `context.input.amount` against the tool invocation parameters, meaning access control operates on the actual runtime values the agent is sending, not just the identity of the caller. This enables parameter-level constraints without modifying the Lambda code.

Policy engines support two modes:
- **LOG_ONLY**: Logs policy decisions without blocking (useful for testing)
- **ENFORCE**: Actively blocks requests that violate policies

## Memory and Session Management

The agent uses AgentCore Memory with the `USER_PREFERENCE` strategy:

```
Namespace: /users/{actorId}/preferences/
Strategy:  USER_PREFERENCE (automatic extraction of stated preferences)
TTL:       7 days
```

**How it works**:
1. When a user says "I prefer email communication" or "my shipping address is...", the memory system automatically extracts and stores this as a preference
2. On subsequent sessions, the agent retrieves relevant preferences from the namespace
3. The `RetrievalConfig` uses `top_k=10` with a `relevance_score=0.3` threshold

**Cross-session example**:
- Session 1: "I'm customer C-01, Rajesh. I prefer refunds to my original payment method."
- Session 2 (new session): Agent automatically recalls Rajesh's refund preference without being told again.

## Observability

### Structured Logging (OTEL)

```bash
agentcore logs --since 30m
```

Logs include:
- Trace IDs for request correlation
- Memory read/write operations
- Gateway tool invocations and responses
- Model inference timing

### Distributed Tracing

```bash
agentcore traces list
```

Each trace captures the full request lifecycle:
- Agent invocation start/end
- Individual tool calls with duration
- Memory retrieval latency
- Gateway round-trip time

### GenAI Dashboard

The AWS Console provides a GenAI Observability dashboard with:
- Token usage per invocation
- Latency percentiles (p50, p95, p99)
- Error rates by tool
- Session-level conversation replay

## Agent Harness and Evaluations

### Harness

The `CustAssistantHarness` provides an enhanced testing environment with:

| Tool | Purpose |
|------|---------|
| `agentcore_browser` | Web research and page navigation |
| `agentcore_code_interpreter` | Python computation and data analysis |
| `agentcore_gateway` | Full gateway access with OAuth credential provider |

The harness uses the `workshop-gateway-cognito` credential stored in AgentCore's token vault for outbound OAuth.

### Evaluations

On-demand evaluation results:
- **Builtin.Helpfulness**: 1.00 (perfect score)
- **Builtin.GoalSuccessRate**: 1.00 (perfect score)

Evaluation types supported:
- **On-demand**: Single prompt evaluation with built-in metrics
- **Online**: Continuous monitoring with configurable sampling
- **Batch**: Dataset-driven evaluation with golden answers
- **Custom**: User-defined evaluator Lambdas

## Workshop Labs Completed

| Lab | Topic | Key Deliverable |
|-----|-------|-----------------|
| 2.1 | Agent Scaffolding | Deployed basic agent to AgentCore Runtime |
| 2.2 | System Prompt & Tools | Returns & Refunds persona with mock tools |
| 2.3 | Memory Integration | Cross-session preference recall (USER_PREFERENCE) |
| 2.4 | Gateway + Lambda | Real DynamoDB + Knowledge Base via MCP gateway |
| 2.5 | Streamlit UI | Web chat with Cognito authentication |
| 2.6 | Observability | OTEL logs, traces, GenAI dashboard |
| 2.8 | Agent Harness | Browser + code interpreter + gateway testing |
| 2.9 | Evaluations | Helpfulness and goal success rate scoring |
| 2.10 | Cedar Policies | Refund amount constraints, read-tool permits |

## Prerequisites

- **Python 3.12+** with `uv` package manager
- **AWS CLI v2** configured with credentials that have Bedrock, DynamoDB, Lambda, Cognito, and IAM permissions
- **AgentCore CLI** (`agentcore`) installed and configured
- **Access to Amazon Bedrock** with Claude Sonnet model enabled in us-west-2
- **Node.js 18+** (for CDK infrastructure deployment)

## Local Development

```bash
cd AgentCoreProject

# Install agent dependencies
cd app/CustomerAssistantAgent
uv sync
cd ../..

# Configure local environment
cp agentcore/.env.local.example agentcore/.env.local
# Edit .env.local with your actual values:
#   MEMORY_ID          - from agentcore show
#   GATEWAY_URL        - your gateway endpoint
#   GATEWAY_CLIENT_ID  - Cognito app client ID
#   GATEWAY_CLIENT_SECRET - Cognito app client secret
#   GATEWAY_TOKEN_ENDPOINT - Cognito token URL

# Run the agent locally (starts runtime on port 8082)
agentcore dev

# Invoke locally (in another terminal)
agentcore invoke --prompt "Look up orders for customer C-02" --stream

# Validate configuration after changes
agentcore validate
```

## Deployment

```bash
# Validate configuration
agentcore validate

# Deploy all resources (agent, memory, gateway, credentials)
agentcore deploy --yes

# Verify deployment
agentcore invoke --prompt "What is the return policy for electronics in the UK?" --stream

# View logs
agentcore logs --since 30m

# List recent traces
agentcore traces list
```

### Deployment Resources Created

| Resource | Type | Identifier |
|----------|------|------------|
| Agent Runtime | CloudFormation Stack | `AgentCoreProject_CustomerAssistantAgent-*` |
| Memory | Managed Resource | `AgentCoreProject_CustomerAssistantMemory-*` |
| Gateway | Managed Resource | `agentcoreproject-workshop-gateway-*` |
| Harness | Managed Resource | `AgentCoreProject_CustAssistantHarness-*` |

## Running the Streamlit UI

```bash
cd streamlit-ui
pip install streamlit boto3
streamlit run streamlit_app.py
```

The UI runs on `http://localhost:8501` and requires:
- A Cognito user account (created via AWS Console or CLI)
- The UI app client ID configured in `streamlit_app.py`
- Network access to the AgentCore Runtime endpoint

### UI Features
- Cognito username/password login
- Real-time streaming responses
- Chat history within session
- Session ID tracking for memory correlation

## Example Interactions

### Order Lookup
```
User: What orders does customer C-02 have?
Agent: Let me look up the orders for customer C-02.

[Calls order_lookup with customer_id="C-02"]

Customer C-02 (Sarah, UK) has the following orders:
1. Wireless Headphones (Electronics) - Delivered on 2024-01-15
2. Winter Jacket (Clothing) - Shipped on 2024-02-01
3. Coffee Maker (Home & Kitchen) - Processing
```

### Policy Query
```
User: What's the return policy for electronics in the UK?
Agent: [Calls policy_retrieval with query about UK electronics returns]

For electronics in the UK, the return policy is:
- 14-day cooling-off period under the Consumer Rights Act 2015
- Item must be in original packaging with all accessories
- Refund processed within 14 days of receiving the returned item
- Faulty items can be returned within 30 days for a full refund
```

### Refund Processing
```
User: Process a refund of $150 for order ORD-001, reason: defective item
Agent: [Calls process_refund with order_id="ORD-001", amount=150, reason="defective item"]

Refund processed successfully:
- Amount: $150
- Order: ORD-001
- Reason: Defective item
- Confirmation ID: REF-847291
```

### Refund Denied by Cedar Policy
```
User: Process a refund of $750 for order ORD-002
Agent: [Calls process_refund with amount=750]
[Cedar policy denies: amount >= 500]

I'm unable to process that refund. Refunds over $500 require manager
approval and cannot be processed through this system. Please escalate
to your supervisor for authorization.
```

## Configuration Reference

### agentcore.json

The main configuration file declares all project resources:

| Section | Purpose |
|---------|---------|
| `runtimes[]` | Agent deployment config (code location, env vars, network mode) |
| `memories[]` | Memory resources (strategy, namespace templates, TTL) |
| `agentCoreGateways[]` | Gateway config (targets, auth, semantic search) |
| `credentials[]` | OAuth credential providers for outbound auth |
| `harnesses[]` | Testing harness references |
| `policyEngines[]` | Cedar policy engine configuration |

### Environment Variables (Runtime)

| Variable | Purpose |
|----------|---------|
| `MEMORY_ID` | AgentCore Memory resource identifier |
| `GATEWAY_URL` | Gateway endpoint URL |
| `GATEWAY_CLIENT_ID` | Cognito app client ID for OAuth |
| `GATEWAY_CLIENT_SECRET` | Cognito app client secret |
| `GATEWAY_TOKEN_ENDPOINT` | Cognito OAuth token endpoint |
| `GATEWAY_SCOPE` | OAuth scope (`gateway/invoke`) |

## Lessons Learned

### Architecture Decisions

1. **Gateway over direct Lambda calls**: The MCP gateway provides a unified authentication layer, Cedar policy enforcement, and semantic tool discovery without modifying individual Lambda functions.

2. **Memory namespace design**: Using `/users/{actorId}/preferences/` allows per-user preference isolation while keeping the retrieval scope narrow and fast.

3. **LRU session cache**: Bounded at 128 sessions to prevent memory leaks in long-running processes while maintaining conversation context for active sessions.

4. **Token caching with pre-expiry refresh**: The MCP client caches OAuth tokens and refreshes 60 seconds before expiry, avoiding request failures during token rotation.

### Operational Insights

5. **agentcore.json does not expand environment variables**: Placeholders like `${SHELL_VAR}` propagate verbatim into CDK and cause AccessDenied at runtime. Always write literal values.

6. **Policy engine naming requires underscores**: Hyphens in policy engine names cause validation failures in the AgentCore CLI.

7. **Harness providerArn format**: The credential provider ARN must use the full token-vault path format (`arn:aws:bedrock-agentcore:...:token-vault/default/oauth2credentialprovider/...`), not just the credential name.

8. **Memory IAM permissions**: The runtime role needs an explicit `bedrock-agentcore:namespacePath` permission for memory operations beyond what the default deployment provides.

### Testing Strategy

9. **Evaluations validate the full chain**: The on-demand evaluation tests the agent end-to-end (model + tools + memory), not just the model in isolation.

10. **Cedar LOG_ONLY mode for development**: Start with LOG_ONLY to validate policy logic against real traffic before switching to ENFORCE in production.

## License

This project was built as part of an AWS workshop for educational purposes.
