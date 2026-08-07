# Security Notes

This repository is published for documentation purposes. It contains no live
credentials and points to no active AWS resources (all workshop resources were
torn down during cleanup).

## Placeholder convention

Environment-specific values are replaced with angle-bracket placeholders so the
configuration shape is documented without exposing real identifiers:

| Placeholder | Meaning |
|-------------|---------|
| `<ACCOUNT_ID>` | AWS account number |
| `<MEMORY_ID>` | AgentCore Memory resource ID |
| `<GATEWAY_ID>` | AgentCore Gateway ID |
| `<GATEWAY_URL>` | Gateway endpoint URL |
| `<GATEWAY_CLIENT_ID>` | Cognito app client ID for gateway OAuth |
| `<GATEWAY_TOKEN_ENDPOINT>` | Cognito OAuth token endpoint |
| `<COGNITO_USER_POOL_ID>` | Cognito User Pool ID |
| `<REDACTED>` | A secret value (never committed) |

## What is never committed

- `.env.local` and any `*.env.local` files (runtime secrets)
- `cognito_config.json` (client secret)
- `deployed-state.json` (resource and secret ARNs, regenerated locally)
- OAuth client secrets, access keys, or session tokens

These are enforced via `.gitignore`. Before pushing, secrets are verified absent
with a history-wide scan for known secret patterns (access keys, client secrets,
encrypted `enc:v1:` blobs).

## Running locally

Copy the provided example files and fill in your own values:

```bash
cp AgentCoreProject/agentcore/.env.local.example AgentCoreProject/agentcore/.env.local
cp AgentCoreProject/streamlit-ui/.env.example AgentCoreProject/streamlit-ui/.env
```

Never commit the filled-in copies.
