# AgentCore AWS Workshop: Returns & Refunds Assistant

A production-grade AI agent built with the **AWS Bedrock AgentCore CLI** and the **Strands Agents SDK**. This project demonstrates the complete lifecycle of building, deploying, and managing an intelligent returns and refunds assistant on AWS.

## Overview

This project was developed as part of the AWS AgentCore CLI Workshop. It showcases how to build a conversational AI agent that handles customer return and refund workflows using Amazon Bedrock foundation models, DynamoDB for data persistence, a Bedrock Knowledge Base for policy retrieval, and Cedar policies for fine-grained access control.

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
│  │  (User Preferences │  │  ┌───────────┐  ┌─────────────┐  │  │
│  │   7-day retention) │  │  │data-lookup│  │policy-retriev│  │  │
│  └────────────────────┘  │  └─────┬─────┘  └──────┬──────┘  │  │
│                          │        │                │          │  │
│                          │  ┌─────┴─────┐  ┌──────┴──────┐  │  │
│                          │  │  Lambda   │  │   Lambda    │  │  │
│                          │  │(DynamoDB) │  │(KB Retrieve)│  │  │
│                          │  └─────┬─────┘  └──────┬──────┘  │  │
│                          │        │                │          │  │
│                          └────────┼────────────────┼──────────┘  │
└───────────────────────────────────┼────────────────┼─────────────┘
                                    │                │
                           ┌────────┴────┐   ┌──────┴──────────┐
                           │  DynamoDB   │   │ Bedrock         │
                           │  - customers│   │ Knowledge Base  │
                           │  - orders   │   │ (Return Policies│
                           │  - products │   │  US/UK/India)   │
                           └─────────────┘   └─────────────────┘
```

## Features

- **Conversational Agent**: Built with Strands Agents SDK on Claude Sonnet 4.5
- **Persistent Memory**: Cross-session user preference recall via AgentCore Memory
- **Real Data Access**: DynamoDB queries for customers, orders, and products
- **Policy Retrieval**: RAG-powered policy lookup from a Bedrock Knowledge Base
- **Refund Processing**: Tool-based refund workflow with amount constraints
- **Gateway Architecture**: MCP-protocol gateway with OAuth (Cognito) authentication
- **Cedar Policies**: Fine-grained access control on gateway tools
- **Streamlit UI**: Web chat interface with Cognito user authentication
- **Agent Harness**: Testing harness with browser, code interpreter, and gateway tools
- **Observability**: OTEL structured logs, distributed traces, and GenAI dashboard

## Project Structure

```
AgentCoreProject/
├── app/
│   ├── CustomerAssistantAgent/     # Main agent application
│   │   ├── main.py                 # Agent entrypoint (Strands SDK)
│   │   ├── mcp_client/            # MCP gateway client with OAuth
│   │   ├── model/                 # Bedrock model loader
│   │   └── pyproject.toml         # Python dependencies
│   └── CustAssistantHarness/      # Testing harness configuration
│       ├── harness.json           # Harness tools and model config
│       └── system-prompt.md       # Harness system prompt
├── lambda_functions/
│   ├── data_lookup/               # DynamoDB query Lambda
│   ├── policy_retrieval/          # Knowledge Base retrieve Lambda
│   └── refund_processing/         # Refund processing Lambda
├── tool_specs/
│   ├── data_lookup.json           # Tool schema: order/user/product lookup
│   ├── policy_retrieval.json      # Tool schema: policy RAG queries
│   └── refund_processing.json     # Tool schema: process refunds
├── policies/
│   ├── allow_read_tools.cedar     # Permit read-only data tools
│   └── refund_limit.cedar         # Restrict refunds to < $500
├── streamlit-ui/
│   └── streamlit_app.py           # Chat UI with Cognito login
├── agentcore/
│   ├── agentcore.json             # Main project configuration
│   ├── aws-targets.json           # Deployment region/account
│   ├── .llm-context/             # TypeScript schema definitions
│   └── cdk/                       # CDK infrastructure code
├── AGENTS.md                      # AI assistant context document
└── README.md                      # Project-level documentation
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | Strands Agents SDK |
| Foundation Model | Claude Sonnet 4.5 (Amazon Bedrock) |
| Infrastructure | AWS CDK (via AgentCore CLI) |
| Data Store | Amazon DynamoDB |
| Knowledge Base | Amazon Bedrock Knowledge Bases |
| Authentication | Amazon Cognito (OAuth 2.0 / User Pools) |
| Gateway Protocol | MCP (Model Context Protocol) |
| Access Control | Cedar Policy Language |
| Deployment | AgentCore CLI (`agentcore deploy`) |
| UI Framework | Streamlit |
| Observability | OpenTelemetry (OTEL) |

## Workshop Labs Completed

1. **Lab 2.1** - Agent scaffolding and deployment to AgentCore Runtime
2. **Lab 2.2** - Domain-specific system prompt and tool implementation
3. **Lab 2.3** - Persistent memory integration (USER_PREFERENCE strategy)
4. **Lab 2.4** - Gateway setup with Lambda targets (DynamoDB + Knowledge Base)
5. **Lab 2.5** - Streamlit chat UI with Cognito authentication
6. **Lab 2.6** - Observability (OTEL logs, traces, GenAI dashboard)
7. **Lab 2.8** - Agent harness with browser, code interpreter, and gateway
8. **Lab 2.9** - Evaluations (helpfulness, goal success rate)
9. **Lab 2.10** - Cedar policies and refund processing with access control

## Key Concepts Demonstrated

### Strands Agents SDK
- `@tool` decorator pattern for agent tools
- Streaming async invocation
- Session management with memory
- MCP client integration for gateway tools

### AgentCore Gateway
- Lambda function targets exposed as MCP tools
- Custom JWT authorization (Cognito)
- Tool schema specifications (JSON)
- OAuth credential provider for outbound auth

### Cedar Policies
- `permit` rules for read-only data tools
- `when` clauses for parameter constraints (refund amount < $500)
- LOG_ONLY vs ENFORCE modes for policy engines

### Memory
- USER_PREFERENCE strategy for cross-session recall
- Namespace templates (`/users/{actorId}/preferences`)
- Session-scoped memory managers

## Prerequisites

- Python 3.12+
- AWS CLI configured with appropriate credentials
- AgentCore CLI (`agentcore`)
- Access to Amazon Bedrock (Claude Sonnet model)

## Local Development

```bash
cd AgentCoreProject

# Install agent dependencies
cd app/CustomerAssistantAgent
uv sync
cd ../..

# Configure local environment
cp agentcore/.env.local.example agentcore/.env.local
# Edit .env.local with your MEMORY_ID, GATEWAY_URL, and credentials

# Run the agent locally
agentcore dev

# Invoke locally
agentcore invoke --prompt "Look up orders for customer C-02" --stream
```

## Deployment

```bash
# Validate configuration
agentcore validate

# Deploy all resources
agentcore deploy --yes

# Invoke the deployed agent
agentcore invoke --prompt "What is the return policy for electronics in the UK?" --stream
```

## Running the Streamlit UI

```bash
cd streamlit-ui
pip install streamlit boto3
streamlit run streamlit_app.py
```

The UI runs on port 8501 and requires Cognito user credentials to authenticate.

## License

This project was built as part of an AWS workshop for educational purposes.
