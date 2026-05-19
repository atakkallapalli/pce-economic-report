# Enterprise MCP Hub — AWS GovCloud + Bedrock AgentCore Backbone (v2)

## Overview

This document describes the **v2 enterprise architecture** for hosting centralized MCP servers in AWS GovCloud, using **Amazon Bedrock AgentCore** as the backbone infrastructure and **Okta** as the external Identity Provider (IdP). This replaces the v1 architecture that used API Gateway + ALB + Amazon Cognito.

> **Companion Diagram**: See [`MCP_Enterprise_Architecture_AgentCore.drawio`](./MCP_Enterprise_Architecture_AgentCore.drawio) for the full visual architecture (2 pages).

---

## What Changed from v1

| Component | v1 (Previous) | v2 (AgentCore + Okta) |
|---|---|---|
| **Identity Provider** | Amazon Cognito | **Okta** (OIDC / OAuth 2.0) |
| **MCP Gateway** | API Gateway + ALB path routing | **AgentCore Gateway** (native MCP protocol) |
| **Auth Mechanism** | Cognito JWT + mTLS | **Okta JWT** (CUSTOM_JWT authorizer) |
| **MFA** | Cognito TOTP | **Okta Verify** (Push + TOTP + FIDO2) |
| **Target Routing** | ALB listener rules (`/fred/*`) | **GatewayTarget** resources |
| **Memory** | None | **AgentCore Memory** (episodic/semantic) |
| **Content Safety** | None | **AgentCore Guardrails** (PII, topics) |
| **Agent Hosting** | ECS Fargate (self-managed) | **AgentCore Runtime** + ECS Fargate |

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent Consumer Zone                               │
│                                                                             │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────────────┐  │
│  │  On-Premises  │  │  Desktop Clients │  │  Other AWS GovCloud Accounts  │  │
│  │  AI Agents    │  │  (Claude, Cursor │  │  (ECS/Lambda/SageMaker Agents │  │
│  │  (Strands SDK)│  │   VS Code, Apps) │  │   via AgentCore Runtime)      │  │
│  └──────┬───────┘  └───┬──────┬───────┘  └──────────────┬────────────────┘  │
│         │              │      │                          │                   │
│    Site-to-Site VPN    │   MCP over HTTPS          PrivateLink / TGW        │
│         │              │   + Okta JWT                    │                   │
│         │      ┌───────┘                                 │                   │
│         │      │  1. OAuth 2.0 (Auth Code/Client Creds)  │                   │
│         │      ▼                                         │                   │
│         │   ┌──────────────────────┐                     │                   │
│         │   │       OKTA IdP       │                     │                   │
│         │   │  OIDC Auth Server    │                     │                   │
│         │   │  Adaptive MFA        │                     │                   │
│         │   │  Custom Scopes       │                     │                   │
│         │   │  Groups → RBAC       │                     │                   │
│         │   └──────────┬───────────┘                     │                   │
│         │              │ 2. JWT Access Token              │                   │
└─────────┼──────────────┼─────────────────────────────────┼──────────────────┘
          │              │                                  │
┌─────────▼──────────────▼──────────────────────────────────▼──────────────────┐
│              AWS GovCloud — Centralized MCP Hub Account                       │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐    │
│  │          Amazon Bedrock AgentCore Platform                             │    │
│  │                                                                       │    │
│  │  ┌────────────────────────────────────────────────────────────┐       │    │
│  │  │  AgentCore Gateway (MCP Protocol)                          │       │    │
│  │  │  AuthorizerType: CUSTOM_JWT                                │       │    │
│  │  │  DiscoveryUrl: https://<org>.okta.com/oauth2/<id>          │       │    │
│  │  │  AllowedClients: [desktop-app, m2m-agents, research-app]   │       │    │
│  │  └───────────────────────┬────────────────────────────────────┘       │    │
│  │                          │                                            │    │
│  │  ┌─────────┐   ┌────────▼─────────────────────────────────┐          │    │
│  │  │ Memory  │   │          Gateway Targets                  │          │    │
│  │  │Episodic │   │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │          │    │
│  │  │Semantic │   │  │ FRED │ │ Jira │ │Confl.│ │GitHub│ ...│          │    │
│  │  │Summary  │   │  │ MCP  │ │ MCP  │ │ MCP  │ │ MCP  │    │          │    │
│  │  └─────────┘   │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘    │          │    │
│  │                 │     │ ECS    │ ECS    │ ECS    │ ECS     │          │    │
│  │  ┌──────────┐  │     │Fargate │Fargate │Fargate │Fargate  │          │    │
│  │  │Guardrails│  └─────┼────────┼────────┼────────┼─────────┘          │    │
│  │  │PII/Topic │        │        │        │        │                     │    │
│  │  │Governance│        └────────┴────────┴────────┘                     │    │
│  │  └──────────┘              │ (via NAT Gateway)                        │    │
│  │                            ▼                                          │    │
│  │  ┌──────────┐     Vendor APIs (FRED, Atlassian, GitHub)              │    │
│  │  │ Runtime  │                                                         │    │
│  │  │Container │                                                         │    │
│  │  │Hosting   │                                                         │    │
│  │  └──────────┘                                                         │    │
│  └───────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  Secrets Manager | KMS | ECR | CloudWatch | CloudTrail | GuardDuty           │
│  Security Hub | AWS Config | Inspector | CodePipeline | VPC Flow Logs        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Okta as Identity Provider

### Why Okta (Not Cognito / Identity Center)

| Reason | Detail |
|---|---|
| **Enterprise SSO standard** | Okta is already the enterprise IdP; avoids duplicate identity silos |
| **Adaptive MFA** | Okta Verify (Push, TOTP, FIDO2), risk-based step-up authentication |
| **M2M support** | Native Client Credentials grant for agent-to-agent authentication |
| **Group-based RBAC** | Okta groups map directly to MCP scopes and access policies |
| **FedRAMP authorized** | Okta is FedRAMP Moderate; paired with GovCloud infrastructure for High |

### Okta Authorization Server Configuration

```
Authorization Server: mcp-hub-auth-server
Issuer:              https://<org>.okta.com/oauth2/<auth-server-id>
JWKS URI:            https://<org>.okta.com/oauth2/<auth-server-id>/v1/keys
Discovery URL:       https://<org>.okta.com/oauth2/<auth-server-id>/.well-known/openid-configuration
```

#### Custom Scopes

| Scope | Description | Granted To |
|---|---|---|
| `mcp:fred:read` | Read FRED economic data | analysts, readers, m2m-agents |
| `mcp:fred:search` | Search FRED series catalog | analysts, readers, m2m-agents |
| `mcp:jira:read` | Read Jira issues and sprints | analysts, admins, m2m-agents |
| `mcp:jira:write` | Create/update Jira issues | admins, m2m-agents |
| `mcp:confluence:read` | Read Confluence pages | analysts, readers, m2m-agents |
| `mcp:github:read` | Read repository data | analysts, m2m-agents |
| `mcp:github:write` | Create PRs and issues | admins, m2m-agents |

#### Access Policies

| Policy | Grant Type | MFA | Token TTL | Use Case |
|---|---|---|---|---|
| `mcp-desktop-policy` | Authorization Code + PKCE | Required (Okta Verify) | 15 min | Human users on desktop clients |
| `mcp-m2m-policy` | Client Credentials | N/A | 1 hour | Machine agents (ECS, Lambda, on-prem) |

#### Okta Groups

| Group | Role | Description |
|---|---|---|
| `mcp-admins` | Admin | Full read/write to all MCP servers |
| `mcp-analysts` | Analyst | Read access + Jira/GitHub write |
| `mcp-readers` | Reader | Read-only across all MCP servers |
| `mcp-m2m-agents` | Machine | Service accounts for AI agents |

---

## 2. AgentCore as MCP Backbone

### AgentCore Components

#### AgentCore Gateway

The **AgentCore Gateway** is the central entry point for all MCP traffic. It replaces the API Gateway + ALB combination from v1 with native MCP protocol support.

```hcl
# Terraform / CloudFormation
Resource: AWS::BedrockAgentCore::Gateway
Properties:
  Name:            "mcp-hub-Gateway"
  ProtocolType:    "MCP"
  AuthorizerType:  "CUSTOM_JWT"
  AuthorizerConfiguration:
    CustomJWTAuthorizer:
      DiscoveryUrl:   "https://<org>.okta.com/oauth2/<id>/.well-known/openid-configuration"
      AllowedClients:
        - "<okta-desktop-app-client-id>"
        - "<okta-m2m-agents-client-id>"
        - "<okta-research-app-client-id>"
```

Key capabilities:
- **Native MCP protocol** handling (no HTTP→MCP translation needed)
- **CUSTOM_JWT authorizer** validates Okta JWTs via OIDC discovery
- **AllowedClients** restricts which Okta app registrations can access the gateway
- **Managed TLS endpoint** with automatic certificate management
- **Built-in rate limiting** and request throttling

#### AgentCore Gateway Targets

Each vendor MCP server is registered as a **GatewayTarget**:

| Target | Backend | Credential Provider | Description |
|---|---|---|---|
| `fred-mcp-target` | ECS Fargate (:3000) or Lambda | `GATEWAY_IAM_ROLE` | FRED economic data tools |
| `jira-mcp-target` | ECS Fargate (:3001) | `GATEWAY_IAM_ROLE` | Jira issue management |
| `confluence-mcp-target` | ECS Fargate (:3002) | `GATEWAY_IAM_ROLE` | Confluence knowledge base |
| `github-mcp-target` | ECS Fargate (:3003) | `GATEWAY_IAM_ROLE` | GitHub repository operations |

Target configuration example:

```hcl
Resource: AWS::BedrockAgentCore::GatewayTarget
Properties:
  Name:              "fred-mcp-target"
  GatewayIdentifier: <gateway-id>
  CredentialProviderConfigurations:
    - CredentialProviderType: "GATEWAY_IAM_ROLE"
  TargetConfiguration:
    Mcp:
      Lambda:
        LambdaArn: <fred-mcp-lambda-arn>
        ToolSchema:
          InlinePayload:
            - Name: "fred_browse"
            - Name: "fred_search"
            - Name: "fred_get_series"
```

For ECS-based targets, use `McpServer.Url` pointing to the internal ECS service endpoint.

#### AgentCore Memory

Enables cross-session learning and context retention for AI agents:

| Strategy | Namespace | Purpose |
|---|---|---|
| **Semantic Memory** | `/facts/{actorId}/` | Long-term facts extracted from interactions |
| **User Preferences** | `/preferences/{actorId}/` | Agent behavior customization per user |
| **Session Summaries** | `/summaries/{actorId}/{sessionId}/` | Compressed session history |
| **Episodic Memory** | `/episodes/{actorId}/{sessionId}/` | Full interaction episodes with reflection |

#### AgentCore Guardrails

Content safety and governance enforcement:

- **PII/PHI detection**: Blocks sensitive data in MCP responses
- **Topic restrictions**: Prevents queries outside approved domains
- **Governance policies**: DynamoDB-backed rules for action approval thresholds
- **Audit logging**: All agent decisions recorded to DynamoDB audit table

#### AgentCore Runtime

Container-based agent hosting with:

- HTTP protocol configuration
- Auto-scaling based on request volume
- Health monitoring and automatic restarts
- Container image from ECR with environment variable injection

---

## 3. Authentication Flows

### Flow A — Desktop AI Client (Human User)

```
1. User opens Claude Desktop / Cursor / VS Code
2. MCP client redirects to Okta login page
3. User authenticates with Okta (username + Adaptive MFA)
4. Okta returns authorization code
5. Client exchanges code for JWT access token (PKCE)
   → Token includes: sub, groups, scp (e.g., mcp:fred:read)
6. Client sends MCP request to AgentCore Gateway URL
   → Authorization: Bearer <okta-jwt>
7. Gateway CUSTOM_JWT authorizer:
   a. Fetches JWKS keys from Okta discovery URL
   b. Validates JWT signature (RS256)
   c. Checks: exp, iss, aud, AllowedClients
   d. Extracts scopes and groups
8. Gateway routes to appropriate GatewayTarget
9. Target retrieves vendor secrets from Secrets Manager
10. Target calls vendor API and returns MCP response
```

### Flow B — Machine Agent (Cross-Account / On-Prem)

```
1. Agent reads Okta client_id + client_secret from Secrets Manager
2. Agent POSTs to Okta /token endpoint:
   → grant_type: client_credentials
   → scope: mcp:fred:read mcp:jira:read
3. Okta returns JWT access token (1hr TTL)
4. Agent sends MCP request:
   → Cross-account: via VPC Interface Endpoint (PrivateLink)
   → On-prem: via Site-to-Site VPN → Transit Gateway
   → Authorization: Bearer <okta-jwt>
5. Gateway validates JWT (same CUSTOM_JWT flow)
6. Gateway routes to GatewayTarget
7. Target executes vendor API call
8. Response returns via same private network path
```

---

## 4. Network Architecture

### Connectivity Patterns

| Consumer Type | Network Path | Authentication |
|---|---|---|
| **Desktop clients** | HTTPS (internet) → Shield → WAF → AgentCore Gateway | Okta JWT (Auth Code + PKCE + MFA) |
| **Cross-account agents** | VPC Endpoint → PrivateLink → NLB → AgentCore Gateway | Okta JWT (Client Credentials) |
| **On-premises agents** | VPN Gateway → Transit Gateway → AgentCore Gateway | Okta JWT (Client Credentials) |
| **MCP targets → Vendors** | ECS → NAT Gateway → Internet → Vendor API | Per-vendor API keys (Secrets Manager) |

### Network Segmentation

| Control | Configuration |
|---|---|
| **VPC** | Dedicated MCP VPC (10.0.0.0/16); private subnets for ECS targets |
| **Security Groups** | ECS SG: inbound from AgentCore Gateway only; no public IPs |
| **PrivateLink** | Cross-account access without internet transit; principal allowlisting |
| **Transit Gateway** | Isolated route tables per connectivity domain; shared via AWS RAM |
| **NAT Gateway** | Outbound-only for vendor API calls from ECS targets |
| **WAF v2** | OWASP rules, rate limiting (1000 req/min), geo-restriction (US only) |
| **Shield Advanced** | DDoS protection at L3/L4/L7 |

---

## 5. Security Best Practices Summary

### Authentication

- All authentication via **Okta OIDC** — no Cognito or Identity Center
- **Adaptive MFA** enforced for all human users (Okta Verify push, TOTP, or FIDO2)
- **Client Credentials** for M2M agents with short-lived JWT tokens
- **No long-lived API keys** — all access via time-limited Okta JWTs
- AgentCore Gateway **AllowedClients** restricts to registered Okta app client IDs

### Authorization

- **JWT scope enforcement** at AgentCore Gateway (e.g., `mcp:fred:read`)
- **Okta groups** mapped to RBAC roles (admin, analyst, reader, m2m-agent)
- **Per-target IAM Task Roles** scoped to only each target's vendor secrets
- **Service Control Policies** enforce org-wide guardrails (deny non-GovCloud, require encryption)
- **AgentCore Guardrails** for content filtering and governance policies

### Data Protection

- **TLS 1.3** on all endpoints (FIPS-compliant cipher suites)
- **KMS CMK** (FIPS 140-2 Level 3) for all encryption at rest
- **Secrets Manager** with 30-day auto-rotation for vendor API keys
- Secrets injected at ECS task launch — never in environment variables or code
- Container image signing and continuous CVE scanning (Inspector)

### Observability & Compliance

| Service | Purpose | Retention |
|---|---|---|
| CloudTrail | API audit trail | 365 days |
| VPC Flow Logs | Network traffic | 90 days |
| CloudWatch | AgentCore + ECS metrics/logs | 90 days |
| GuardDuty | ECS runtime threat detection | Continuous |
| Security Hub | NIST 800-53 compliance | Continuous |
| AWS Config | Drift detection | Continuous |
| Inspector | Container CVE scanning | Continuous |

---

## 6. Adding a New MCP Server Target

1. **Build container image** and push to ECR (or package as Lambda)
2. **Store vendor credentials** in Secrets Manager (tagged `service: <vendor>-mcp`)
3. **Create IAM Task Role** scoped to the new target's secrets
4. **Register GatewayTarget** on the AgentCore Gateway:
   ```hcl
   Resource: AWS::BedrockAgentCore::GatewayTarget
   Properties:
     Name: "<vendor>-mcp-target"
     GatewayIdentifier: <gateway-id>
     CredentialProviderConfigurations:
       - CredentialProviderType: "GATEWAY_IAM_ROLE"
     TargetConfiguration:
       McpServer:
         Url: "https://<internal-ecs-endpoint>/mcp"
   ```
5. **Add Okta scopes** (`mcp:<vendor>:read`, `mcp:<vendor>:write`)
6. **Update Okta access policies** to grant scopes to appropriate groups
7. **Add AllowedClients** entry on the Gateway if new Okta apps need access
8. **Deploy via CodePipeline** (blue/green with automatic rollback)

---

## 7. Diagram Files

| File | Description |
|---|---|
| [`MCP_Enterprise_Architecture_AgentCore.drawio`](./MCP_Enterprise_Architecture_AgentCore.drawio) | Draw.io diagram (open in diagrams.net or VS Code draw.io extension) |
| Page 1: "AgentCore MCP Enterprise Overview" | Full infrastructure view with AgentCore backbone and Okta IdP |
| Page 2: "Security & Auth Flow Detail" | Okta auth flows, AgentCore JWT config, defense-in-depth layers, v1 vs v2 comparison |
| [`MCP_Enterprise_Architecture.drawio`](./MCP_Enterprise_Architecture.drawio) | v1 diagram (Cognito + API Gateway — for reference) |
| [`MCP_Enterprise_Architecture.md`](./MCP_Enterprise_Architecture.md) | v1 documentation (for reference) |
