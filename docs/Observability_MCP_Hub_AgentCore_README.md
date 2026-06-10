# Enterprise Observability MCP Hub — AgentCore Deployment

## Overview

The Enterprise Observability MCP Hub is a centralized gateway deployed in AWS GovCloud that provides unified [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tool access for AI agents across the enterprise. This deployment variant uses **Amazon Bedrock AgentCore** as the managed MCP backbone with **Okta** as the external Identity Provider, delivering native MCP protocol handling, episodic memory, content guardrails, and managed agent runtime.

AI agents (desktop coding tools, cloud applications, on-premises servers) connect to the AgentCore Gateway via HTTPS with Okta-issued JWT tokens and invoke observability tools against enterprise systems — Splunk, Dynatrace, S3 Lakehouse, and CloudWatch — all accessible within the enterprise cloud network boundary.

---

## Architecture Diagrams

See [`Observability_MCP_Hub_C4.drawio`](./Observability_MCP_Hub_C4.drawio) for full C4 architecture diagrams:

| Diagram | Description |
|---------|-------------|
| **C4 Level 1 — System Context** | High-level view of people, MCP clients, the hub system, Okta IdP, and enterprise data sources |
| **C4 Level 2 — Container** | Internal containers: AgentCore Gateway, Memory, Guardrails, Runtime, ECS Fargate targets, network edge |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **AgentCore Gateway** | Native MCP protocol handling; no HTTP→MCP translation; managed TLS endpoint; built-in rate limiting |
| **Okta OIDC (no Cognito)** | Enterprise standardized on Okta; CUSTOM_JWT authorizer with OIDC discovery; adaptive MFA |
| **AgentCore Memory** | Episodic + semantic memory enables cross-session incident learning and context retention |
| **AgentCore Guardrails** | PII/PHI detection, topic restrictions, governance policies for observability data |
| **AgentCore Runtime** | Managed container hosting with auto-scaling, health monitoring for agent workloads |
| **ECS Fargate Targets** | Self-hosted vendor MCP servers registered as Gateway Targets; independent scaling per vendor |
| **Enterprise tools on internal network** | Splunk, Dynatrace, S3 Lakehouse, CloudWatch reachable via enterprise network routing |
| **Network components not in application scope** | Transit Gateway, Site-to-Site VPN, PrivateLink, Shield, WAF managed by Enterprise Network Team |

---

## System Context (C4 Level 1)

### People

| Actor | Role |
|-------|------|
| **SRE / Platform Engineer** | Uses AI agents to investigate incidents, query logs/metrics, automate runbooks |
| **Observability Admin** | Manages MCP Gateway targets, Okta scopes, AgentCore config, vendor integrations |

### MCP Clients

| Client Type | Description | Auth Flow |
|-------------|-------------|-----------|
| **Desktop AI Coding Agents** | Claude Desktop, Cursor, VS Code, Kiro, Devin | OAuth 2.0 Authorization Code + PKCE → Okta JWT |
| **Enterprise Cloud Application Agents** | ECS, Lambda, SageMaker in other AWS accounts (AgentCore Runtime) | OAuth 2.0 Client Credentials → Okta M2M JWT |
| **On-Premises Ops Agents** | Datacenter servers running Strands SDK + Bedrock LLMs | OAuth 2.0 Client Credentials → Okta JWT |

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
MCP Client → [HTTPS + Okta JWT] → AgentCore Gateway (CUSTOM_JWT Authorizer)
                                        ↓
                          ┌─────────────┼──────────────┐
                          ↓             ↓              ↓
                    AgentCore       AgentCore      AgentCore
                     Memory        Guardrails      Runtime
                          ↓             ↓              ↓
                          └─────────────┼──────────────┘
                                        ↓
                              Gateway Targets (routing)
                                        ↓
                        ┌───────────────┼───────────────┬───────────────┐
                        ↓               ↓               ↓               ↓
                  Splunk MCP      Dynatrace MCP    S3 Lake MCP     CloudWatch MCP
                  (ECS :3000)     (ECS :3001)      (ECS :3002)     (ECS :3003)
                        ↓               ↓               ↓               ↓
                   Splunk API     Dynatrace API    S3+Athena       CloudWatch API
                   (enterprise network — internal routing)
```

### AgentCore Platform Components

| Component | Purpose |
|-----------|---------|
| **AgentCore Gateway** | Native MCP protocol endpoint; CUSTOM_JWT authorizer (Okta OIDC discovery); managed TLS 1.3; AllowedClients enforcement; built-in rate limiting; tool discovery & routing |
| **AgentCore Memory** | Episodic memory (full interaction episodes); semantic memory (extracted facts); session summaries; user preferences; cross-session incident learning; 90-day event expiry |
| **AgentCore Guardrails** | PII/PHI detection in observability data; topic restrictions (prevent queries outside approved domains); governance policies (DynamoDB-backed); action approval thresholds |
| **AgentCore Runtime** | Container-based agent hosting; HTTP protocol config; auto-scaling; health monitoring; automatic restarts |

### Gateway Targets (ECS Fargate MCP Servers)

| Target | Backend | Port | Tools | Credential Provider |
|--------|---------|------|-------|-------------------|
| `splunk-mcp-target` | ECS Fargate | 3000 | `splunk_search`, `splunk_get_alerts`, `splunk_list_indexes`, `splunk_saved_searches` | `GATEWAY_IAM_ROLE` |
| `dynatrace-mcp-target` | ECS Fargate | 3001 | `dt_get_problems`, `dt_query_metrics`, `dt_get_entities`, `dt_get_logs` | `GATEWAY_IAM_ROLE` |
| `s3lake-mcp-target` | ECS Fargate | 3002 | `lake_query_athena`, `lake_list_tables`, `lake_get_partitions`, `lake_describe_schema` | `GATEWAY_IAM_ROLE` |
| `cloudwatch-mcp-target` | ECS Fargate | 3003 | `cw_get_metrics`, `cw_query_logs`, `cw_describe_alarms`, `cw_get_dashboards` | `GATEWAY_IAM_ROLE` |

### Supporting AWS Services

| Container | Technology | Purpose |
|-----------|-----------|---------|
| **Secrets Manager** | AWS Managed | Vendor API tokens; 30-day auto-rotation; per-target scoping |
| **KMS** | CMK (FIPS 140-2 L3) | Envelope encryption for secrets, logs, S3 |
| **SSM Parameter Store** | SecureString | MCP server configs, endpoint URLs, feature flags |
| **ECR** | Container Registry | MCP server images; on-push vulnerability scanning |
| **CloudWatch** | Container Insights | Custom metrics, alarms, log aggregation |
| **X-Ray** | Distributed Tracing | Service map, latency breakdown per MCP tool call |
| **CloudTrail** | API Audit | Management + data events, compliance trail |
| **GuardDuty** | Threat Detection | ECS runtime anomaly detection |
| **Security Hub** | Compliance | NIST 800-53 conformance checks |

---

## Authentication & Authorization

### Okta Configuration

| Setting | Value |
|---------|-------|
| Authorization Server | `mcp-obs-auth-server` (custom) |
| Issuer | `https://<org>.okta.com/oauth2/<auth-server-id>` |
| JWKS URI | `https://<org>.okta.com/oauth2/<auth-server-id>/v1/keys` |
| Discovery URL | `https://<org>.okta.com/oauth2/<auth-server-id>/.well-known/openid-configuration` |

### AgentCore Gateway Auth Configuration

```hcl
Resource: AWS::BedrockAgentCore::Gateway
Properties:
  Name:            "obs-mcp-hub-gateway"
  ProtocolType:    "MCP"
  AuthorizerType:  "CUSTOM_JWT"
  AuthorizerConfiguration:
    CustomJWTAuthorizer:
      DiscoveryUrl:   "https://<org>.okta.com/oauth2/<id>/.well-known/openid-configuration"
      AllowedClients:
        - "<okta-desktop-app-client-id>"
        - "<okta-m2m-agents-client-id>"
        - "<okta-onprem-agents-client-id>"
```

### Okta Scopes

| Scope | Access |
|-------|--------|
| `mcp:splunk:read` | Splunk MCP — read-only queries |
| `mcp:splunk:search` | Splunk MCP — SPL search execution |
| `mcp:dynatrace:read` | Dynatrace MCP — metrics, problems, entities, logs |
| `mcp:s3-lake:query` | S3 Lakehouse MCP — Athena queries |
| `mcp:cloudwatch:read` | CloudWatch MCP — metrics, logs, alarms, dashboards |

### Access Policies

| Policy | Grant Type | MFA | Token TTL | Use Case |
|--------|------------|-----|-----------|----------|
| `mcp-desktop-policy` | Authorization Code + PKCE | Required (Okta Verify) | 15 min | Human users on desktop |
| `mcp-m2m-policy` | Client Credentials | N/A | 1 hour | Machine agents |

### Auth Flow

1. **Token Acquisition**: MCP client obtains JWT from Okta
2. **Token Presentation**: `Authorization: Bearer <JWT>` with MCP request to AgentCore Gateway URL
3. **Gateway Validation**: CUSTOM_JWT authorizer fetches Okta JWKS → validates RS256 signature, exp, iss, aud, AllowedClients
4. **Scope Enforcement**: Gateway checks JWT `scp` claim against target access requirements
5. **Target Routing**: Gateway routes to appropriate GatewayTarget
6. **Guardrails Check**: Content passes through guardrails before/after vendor API call
7. **Memory Update**: Interaction stored in episodic memory for context retention

---

## AgentCore Memory for Observability

| Strategy | Namespace | Use Case |
|----------|-----------|----------|
| **Episodic Memory** | `/episodes/{actorId}/{sessionId}/` | Full incident investigation history — what was queried, what was found |
| **Semantic Memory** | `/facts/{actorId}/` | Learned facts: "Production database is in us-east-1", "Alert X is always a false positive" |
| **Session Summaries** | `/summaries/{actorId}/{sessionId}/` | Compressed session history for long investigations |
| **User Preferences** | `/preferences/{actorId}/` | "Prefer Splunk for security logs", "Default CloudWatch region: us-gov-west-1" |

**Retention**: 90-day event expiry (configurable per compliance requirements)

---

## Security Controls

| Control | Implementation |
|---------|---------------|
| **Encryption in Transit** | TLS 1.3 (managed by AgentCore Gateway) |
| **Encryption at Rest** | KMS CMK (FIPS 140-2 Level 3) for secrets, logs, S3 |
| **Network Isolation** | ECS tasks in private subnets; no public IP; AgentCore-managed ingress |
| **Secret Rotation** | Secrets Manager 30-day auto-rotation |
| **Content Filtering** | AgentCore Guardrails (PII/PHI, topic restrictions) |
| **Audit Trail** | CloudTrail (multi-region) + AgentCore audit events |
| **Threat Detection** | GuardDuty (ECS runtime) + Security Hub (NIST 800-53) |
| **Least Privilege** | Per-target IAM task roles; GATEWAY_IAM_ROLE credential provider |
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

## Adding a New Observability MCP Server

1. **Build container image** → push to ECR
2. **Store vendor credentials** in Secrets Manager (`/mcp/<vendor>/api-token`)
3. **Create IAM Task Role** scoped to the new target's secrets
4. **Deploy ECS service** in private subnets (Fargate)
5. **Register GatewayTarget** on AgentCore Gateway:
   ```hcl
   Resource: AWS::BedrockAgentCore::GatewayTarget
   Properties:
     Name: "<vendor>-mcp-target"
     GatewayIdentifier: <gateway-id>
     CredentialProviderConfigurations:
       - CredentialProviderType: "GATEWAY_IAM_ROLE"
     TargetConfiguration:
       McpServer:
         Url: "http://<ecs-service>.mcp-obs.internal:300N/mcp"
   ```
6. **Add Okta scopes** (`mcp:<vendor>:read`)
7. **Update access policies** to grant scopes to appropriate groups
8. **Configure guardrails** for new vendor data types

---

## Comparison: AgentCore vs Non-AgentCore Deployment

| Aspect | AgentCore (this) | Non-AgentCore |
|--------|-----------------|---------------|
| **Gateway** | AgentCore Gateway (managed MCP) | API Gateway + Lambda Authorizer |
| **Auth** | CUSTOM_JWT (Okta OIDC, managed) | Okta OIDC (self-managed validation) |
| **MCP Routing** | Gateway Targets (declarative) | ALB path-based routing |
| **Memory** | AgentCore Episodic/Semantic Memory | Not included (stateless) |
| **Guardrails** | AgentCore Guardrails (PII, topics) | Custom (application-level) |
| **Agent Runtime** | AgentCore Runtime (managed hosting) | N/A (MCP servers only) |
| **Scaling** | AgentCore managed + ECS Auto Scaling | ECS Auto Scaling only |
| **TLS** | Managed by AgentCore | Managed by ACM + API Gateway |
| **Complexity** | Less IaC, managed service | More IaC, full control |
| **Vendor Lock-in** | Higher (Bedrock AgentCore) | Lower (standard AWS services) |
| **Time to Market** | Faster (managed components) | Slower (build everything) |
