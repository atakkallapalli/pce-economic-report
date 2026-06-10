# Enterprise Observability MCP Hub — Non-AgentCore Deployment

## Overview

The Enterprise Observability MCP Hub is a centralized gateway deployed in AWS GovCloud that provides unified [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tool access for AI agents across the enterprise. This deployment variant uses **API Gateway + Okta OIDC + ECS Fargate** without Amazon Bedrock AgentCore, giving teams full control over the gateway layer while maintaining FedRAMP High compliance.

AI agents (desktop coding tools, cloud applications, on-premises servers) connect to the hub via HTTPS with Okta-issued JWT tokens and invoke observability tools against enterprise systems — Splunk, Dynatrace, S3 Lakehouse, and CloudWatch — all accessible within the enterprise cloud network boundary.

---

## Architecture Diagrams

See [`Observability_MCP_Hub_NonAgentCore.drawio`](./Observability_MCP_Hub_NonAgentCore.drawio) for full C4 architecture diagrams:

| Diagram | Description |
|---------|-------------|
| **C4 Level 1 — System Context** | High-level view of people, MCP clients, the hub system, Okta IdP, and enterprise data sources |
| **C4 Level 2 — Container** | Internal containers: API Gateway, Lambda Authorizer, ALB, ECS Fargate MCP servers, Secrets Manager, KMS, observability stack |
| **C4 Level 3 — Component** | Internal components of a single MCP server (transport, protocol handler, tool registry, vendor client, credential provider) |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No AgentCore** | Full ownership of gateway, no dependency on Bedrock AgentCore GA timeline or feature set |
| **Okta OIDC (no Cognito)** | Enterprise already standardized on Okta; avoids duplicate IdP; direct JWT validation via JWKS |
| **API Gateway + Lambda Authorizer** | Native JWT validation with Okta discovery URL; custom scope-to-IAM mapping; request throttling |
| **Internal ALB (not public)** | Traffic arrives via enterprise network (TGW/VPN/PrivateLink managed by network team); ALB stays private |
| **ECS Fargate per MCP server** | Independent scaling, deployment, and failure isolation per vendor integration |
| **Enterprise tools on internal network** | Splunk, Dynatrace, S3 Lakehouse, CloudWatch are reachable via enterprise network routing — no internet egress needed for vendor calls |
| **No network components in scope** | Transit Gateway, Site-to-Site VPN, PrivateLink, Shield, WAF are managed by the Enterprise Network Team |

---

## System Context (C4 Level 1)

### People

| Actor | Role |
|-------|------|
| **SRE / Platform Engineer** | Uses AI agents to investigate incidents, query logs/metrics, automate runbooks |
| **Observability Admin** | Manages MCP server configs, Okta scopes, IAM policies, vendor integrations |

### MCP Clients

| Client Type | Description | Auth Flow |
|-------------|-------------|-----------|
| **Desktop AI Coding Agents** | Claude Desktop, Cursor, VS Code, Kiro, Devin | OAuth 2.0 Authorization Code + PKCE → Okta JWT |
| **Enterprise Cloud Application Agents** | ECS, Lambda, SageMaker in other AWS accounts | OAuth 2.0 Client Credentials → Okta M2M JWT |
| **On-Premises Ops Agents** | Datacenter servers running Python SDK + Bedrock LLMs | OAuth 2.0 Client Credentials → Okta JWT |

### Enterprise Data Sources (Internal Network)

| System | Protocol | Purpose |
|--------|----------|---------|
| **Splunk Enterprise** | REST API | Log aggregation, SIEM, SPL queries, alerts |
| **Dynatrace** | API v2 | APM, infrastructure monitoring, Davis AI anomaly detection |
| **S3 Observability Lakehouse** | S3 + Athena SQL | Historical logs, traces, metrics (Parquet/Iceberg) |
| **Amazon CloudWatch** | CloudWatch API | Multi-account metrics, logs, alarms, dashboards |

---

## Container Architecture (C4 Level 2)

### Request Flow

```
MCP Client → [HTTPS + Okta JWT] → API Gateway → Lambda Authorizer (JWKS validation)
                                        ↓
                                   VPC Link (private)
                                        ↓
                                 Internal ALB (path-based routing)
                                        ↓
                        ┌───────────────┼───────────────┬───────────────┐
                        ↓               ↓               ↓               ↓
                  Splunk MCP      Dynatrace MCP    S3 Lake MCP     CloudWatch MCP
                  (:3000)           (:3001)          (:3002)          (:3003)
                        ↓               ↓               ↓               ↓
                   Splunk API     Dynatrace API    S3+Athena       CloudWatch API
                   (enterprise network — internal routing)
```

### Containers

| Container | Technology | Purpose |
|-----------|-----------|---------|
| **Amazon API Gateway** | HTTP API (Regional) | TLS termination, JWT authorizer, route dispatch, throttling (1000 rps) |
| **Lambda Authorizer** | AWS Lambda (Python/Node) | Okta JWKS validation, scope-to-IAM policy mapping, token caching (5 min TTL) |
| **AWS IAM** | AWS Managed | Per-service task roles with least-privilege policies |
| **Application Load Balancer** | Internal ALB | Path-based routing to MCP server target groups, health checks |
| **Splunk MCP Server** | ECS Fargate (Port 3000) | Tools: `splunk_search`, `splunk_get_alerts`, `splunk_list_indexes`, `splunk_saved_searches` |
| **Dynatrace MCP Server** | ECS Fargate (Port 3001) | Tools: `dt_get_problems`, `dt_query_metrics`, `dt_get_entities`, `dt_get_logs` |
| **S3 Lakehouse MCP Server** | ECS Fargate (Port 3002) | Tools: `lake_query_athena`, `lake_list_tables`, `lake_get_partitions`, `lake_describe_schema` |
| **CloudWatch MCP Server** | ECS Fargate (Port 3003) | Tools: `cw_get_metrics`, `cw_query_logs`, `cw_describe_alarms`, `cw_get_dashboards` |
| **ECS Auto Scaling** | Target Tracking | CPU 70% target, Min: 2, Max: 10 per service |
| **Cloud Map** | Service Discovery | Namespace: `mcp-obs.internal`, DNS-based routing |
| **Secrets Manager** | AWS Managed | Vendor API tokens, 30-day auto-rotation, per-service scoping |
| **KMS** | CMK (FIPS 140-2 L3) | Envelope encryption for secrets, logs, S3 |
| **SSM Parameter Store** | SecureString | MCP server configs, endpoint URLs, feature flags |
| **CloudWatch** | Container Insights | Custom metrics (latency, error rate, tool invocation count), alarms |
| **X-Ray** | Distributed Tracing | Service map, latency breakdown per MCP tool call |
| **CloudTrail** | API Audit | Management + data events, compliance trail |

---

## Component Architecture (C4 Level 3 — Single MCP Server)

Each MCP server container follows a consistent internal architecture:

| Component | Responsibility |
|-----------|---------------|
| **HTTP/SSE Transport Layer** | Express.js or FastAPI; handles HTTP POST `/mcp` (Streamable HTTP), SSE for streaming, `/health` endpoint |
| **MCP Protocol Handler** | JSON-RPC 2.0 processing; dispatches `tools/list`, `tools/call`, `initialize` |
| **Tool Registry** | Registered tools with JSON Schema input validation; tool discovery |
| **Vendor API Client** | HTTP client with connection pooling, retry (exponential backoff), 30s timeout |
| **Credential Provider** | Fetches from Secrets Manager via IAM role; in-memory cache (5 min TTL) |
| **Response Formatter** | MCP `tool_result` formatting, pagination, error mapping, content truncation |
| **Observability Middleware** | Structured JSON logging, X-Ray trace segments, CloudWatch EMF metrics |

---

## Authentication & Authorization

### Flow

1. **Token Acquisition**: MCP client obtains JWT from Okta (Auth Code + PKCE for users, Client Credentials for M2M)
2. **Token Presentation**: Client sends `Authorization: Bearer <JWT>` with MCP tool call request
3. **Validation**: API Gateway invokes Lambda Authorizer → fetches Okta JWKS → validates signature (RS256), expiry, audience, issuer
4. **Scope Enforcement**: Lambda maps Okta scopes (e.g., `mcp:splunk:read`) to IAM policy allowing specific routes
5. **IAM Authorization**: ECS task roles enforce least-privilege access to AWS resources (Secrets Manager, S3, CloudWatch)

### Okta Scopes

| Scope | Access |
|-------|--------|
| `mcp:splunk:read` | Splunk MCP Server — read-only queries |
| `mcp:splunk:search` | Splunk MCP Server — SPL search execution |
| `mcp:dynatrace:read` | Dynatrace MCP Server — metrics, problems, entities |
| `mcp:s3-lake:query` | S3 Lakehouse MCP Server — Athena queries |
| `mcp:cloudwatch:read` | CloudWatch MCP Server — metrics, logs, alarms |

---

## Security Controls

| Control | Implementation |
|---------|---------------|
| **Encryption in Transit** | TLS 1.3 (ACM-managed certificates) at API Gateway |
| **Encryption at Rest** | KMS CMK (FIPS 140-2 Level 3) for Secrets, logs, S3 |
| **Network Isolation** | ECS tasks in private subnets, no public IP, security groups restrict port access |
| **Secret Rotation** | Secrets Manager auto-rotation every 30 days |
| **Audit Trail** | CloudTrail (multi-region), all API calls logged |
| **Least Privilege** | Per-MCP-server IAM task roles; resource-level policies |
| **Compliance** | FedRAMP High, ITAR, CJIS aligned (GovCloud) |

---

## What's NOT in Scope (Enterprise Network Team)

The following components are managed by the Enterprise Network Team and are **not deployed** as part of this architecture:

- AWS Shield Advanced (DDoS protection)
- AWS WAF v2 (OWASP rules, rate limiting, geo-restriction)
- Transit Gateway (cross-account routing)
- Site-to-Site VPN / Direct Connect (on-premises connectivity)
- VPC Endpoint Service / PrivateLink provider
- Network Load Balancer (PrivateLink target)
- Route 53 Hosted Zones (DNS)

---

## Comparison: Non-AgentCore vs AgentCore Deployment

| Aspect | Non-AgentCore (this) | AgentCore |
|--------|---------------------|-----------|
| **Gateway** | API Gateway + Lambda Authorizer | AgentCore Gateway (managed) |
| **Auth** | Okta OIDC + IAM (self-managed) | AgentCore CUSTOM_JWT (Okta OIDC) |
| **MCP Routing** | ALB path-based routing | AgentCore Gateway Targets |
| **Memory** | Not included (stateless) | AgentCore Episodic Memory |
| **Guardrails** | Custom (application-level) | AgentCore Guardrails Engine |
| **Agent Runtime** | N/A (MCP servers only) | AgentCore Runtime (container hosting) |
| **Scaling** | ECS Auto Scaling (self-managed) | AgentCore managed scaling |
| **Complexity** | More IaC, full control | Less IaC, managed service |
| **Vendor Lock-in** | Lower (standard AWS services) | Higher (Bedrock AgentCore) |
