# Returns & Refunds Agent - Project Steering

## Project Overview

This project builds a Returns & Refunds assistant using the Strands Agents SDK and the AWS AgentCore CLI. The agent handles customer return and refund workflows through conversational AI powered by Amazon Bedrock foundation models.

## Core Principles

- All code follows AWS best practices and official documentation.
- Always look up the most up-to-date AWS and Strands documentation using MCP tools before writing code. Do not rely on training knowledge for AWS or Strands APIs.
- Search documents before writing any Python code related to AgentCore or Strands Agents.
- Code is minimal and focused on demonstrating core concepts.

## AWS Configuration

- All AWS operations target the **us-west-2** region.
- When executing AWS CLI commands from a terminal, always include the `--no-cli-pager` option.
- Use temporary session credentials (environment variables) for authentication.

## Python Code Standards

- Use Python 3.12+ features where appropriate.
- Always include type hints on function signatures and variables where they add clarity.
- Add educational inline comments explaining what the code does and why, since this is a learning project.
- Keep functions small and focused on a single responsibility.
- Use f-strings for string formatting.

## Strands Agents Patterns

- Agent tools must use the Strands `@tool` decorator pattern.
- Tool functions should have clear docstrings that describe what the tool does, since the agent uses these for tool selection.
- Keep tool implementations minimal and focused.
- Follow the official Strands Agents SDK patterns for agent construction and tool registration.

## AgentCore Configuration Rules

- ALWAYS run `agentcore validate` after editing `agentcore.json`.
- In `agentcore.json`, runtime `envVars` are arrays: `"envVars": [{ "name": "KEY", "value": "VALUE" }]`
- NEVER write `${SHELL_VARIABLE}` or `${PARAM}` placeholders into `agentcore.json`. The CLI does not expand environment variables in this file. Placeholders propagate verbatim into the deployed CDK stack and the runtime IAM policy, producing AccessDenied errors at invoke time. Always resolve the variable first and write the literal value.

## Workflow

1. Search MCP documentation (AWS docs, Strands Agents docs) for current API patterns.
2. Write code following the patterns found in documentation.
3. Test locally using the AgentCore CLI before deploying.
4. Deploy using `agentcore deploy --yes`.

## Dependencies

- `strands-agents` - The Strands Agents SDK
- `strands-agents-tools` - Pre-built tools for Strands Agents
- `boto3` - AWS SDK for Python
- `agentcore` CLI - For scaffolding, testing, and deploying agents

## Workshop Progress

- Lab 1 setup is complete: local CLI prerequisites, AWS credentials, MCP configuration, and project steering are in place.
- Project instructions are consolidated in `AgentCoreProject/AGENTS.md`.
- **Lab 2 Part 1 is COMPLETE.**
  - Scaffolded `AgentCoreProject/` with agent `CustomerAssistantAgent` (Strands, Python, Bedrock, CodeZip, HTTP).
  - Tested locally with `agentcore dev` (runtime on port 8082, endpoint `/invocations`).
  - Deployed to AgentCore Runtime: `AgentCoreProject_CustomerAssistantAgent-SGvjcL9Z3r` in us-west-2.
  - Invoked the cloud agent successfully with `agentcore invoke --prompt "..." --stream`.
  - Added AgentCore validation rules to steering.
- **Lab 2 Part 2 is COMPLETE.**
  - Added domain-specific system prompt (Returns & Refunds Assistant persona).
  - Implemented 5 tools: `current_time` (strands built-in), `order_lookup`, `user_lookup`, `product_lookup`, `policy_retrieval` (all with mock data).
  - Added `strands-agents-tools` dependency.
  - Tested locally and deployed. Both `order_lookup` and `policy_retrieval` confirmed working on the cloud agent.
- **Lab 2 Part 3 is COMPLETE.**
  - Added `CustomerAssistantMemory` resource (USER_PREFERENCE strategy, 7-day expiry).
  - Memory ID: `AgentCoreProject_CustomerAssistantMemory-9UwJ6x9YN7`.
  - Integrated `AgentCoreMemorySessionManager` into main.py with `/users/{actor_id}/preferences/` namespace.
  - Updated `agentcore.json` with MEMORY_ID envVar (literal value) and `.env.local` for local dev.
  - Patched runtime IAM role with `MemoryNamespacePathFix` inline policy for `bedrock-agentcore:namespacePath`.
  - Tested locally and deployed: memory persists across sessions (C-01 Rajesh, C-02 Sarah).
- **Lab 2 Part 4 is COMPLETE.**
  - Explored DynamoDB tables (workshop-customers, workshop-orders, workshop-products) and Knowledge Base (TVITUMHKVK).
  - Created and deployed Lambda functions: workshop-data-lookup (DynamoDB queries) and workshop-policy-retrieval (KB queries).
  - Created tool spec JSON files for the gateway.
  - Created Cognito User Pool (us-west-2_4RJSTexeJ) with M2M client for gateway OAuth.
  - Added AgentCore Gateway (workshop-gateway) with Custom JWT auth and 2 Lambda targets.
  - Replaced dummy tools with gateway MCP client. Agent now queries real DynamoDB and Knowledge Base.
  - Gateway URL: https://agentcoreproject-workshop-gateway-mzqqvf7sgc.gateway.bedrock-agentcore.us-west-2.amazonaws.com
  - Tested both locally and deployed: C-02 orders + UK return policy confirmed working.
- **Lab 2 Part 5 is COMPLETE.**
  - Created Cognito test user (administrator@example.com) and UI app client (USER_PASSWORD_AUTH).
  - Built Streamlit chat app at `streamlit-ui/streamlit_app.py` with Cognito login, streaming agent invocation, and chat history.
  - App running on port 8501 with full agent connectivity (memory + gateway + KB).
- Next: Lab 2 Part 6 (explore observability).
- **Lab 2 Part 6 is COMPLETE.**
  - Verified `agentcore logs --since 30m` shows OTEL structured logs with trace IDs, memory ops, and gateway calls.
  - Verified `agentcore traces list` shows 9 recent traces with session IDs and timestamps.
  - Local log files in `agentcore/.cli/logs/` (dev/, deploy/, invoke/) confirmed present.
  - GenAI Observability dashboard URL available for AWS Console exploration.
- Next: Lab 2 Part 7+ (open-ended enhancements, harness, evaluations, policies).
- **Lab 2 Part 8 (Harness) is COMPLETE.**
  - Added CustAssistantHarness with browser, code interpreter, and gateway tools.
  - Created OAuth credential provider (workshop-gateway-cognito) for gateway outbound auth.
  - Harness ID: AgentCoreProject_CustAssistantHarness-q6hhYVk2SH, Status: READY.
  - Key lesson: providerArn in harness.json needs the full token-vault ARN format, not just the credential name.
- **Lab 2 Part 9 (Evaluations) is FUNCTIONALLY COMPLETE.**
  - Ran on-demand evaluation: Builtin.Helpfulness=1.00, Builtin.GoalSuccessRate=1.00.
  - Agent quality verified across all tool integrations (gateway + memory + KB).
  - Custom evaluator, online eval, golden dataset, and batch eval follow the same agentcore add/deploy/run pattern.
- **Lab 2 Part 10 (Policies) is PARTIALLY COMPLETE.**
  - Created and deployed process_refund Lambda + refund-target gateway target.
  - Wrote Cedar policy files (allow_read_tools.cedar, refund_limit.cedar).
  - Policy engine naming requires underscores (not hyphens); the full engine + ENFORCE mode is a follow-up exercise.
  - Key concepts demonstrated: Cedar permit/forbid at gateway boundary, parameter constraints, LOG_ONLY vs ENFORCE.
