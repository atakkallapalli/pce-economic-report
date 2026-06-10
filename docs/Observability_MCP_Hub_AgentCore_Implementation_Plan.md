# Technical Implementation Plan — Enterprise Observability MCP Hub (AgentCore)

## Document Info

| Field | Value |
|-------|-------|
| **Project** | Enterprise Observability MCP Hub — AgentCore Deployment |
| **Region** | AWS GovCloud (us-gov-west-1) |
| **MCP Backbone** | Amazon Bedrock AgentCore (Gateway, Memory, Guardrails, Runtime) |
| **Auth** | Okta OIDC / OAuth 2.0 (CUSTOM_JWT) + AWS IAM |
| **IaC** | Terraform (modular) |
| **Compliance** | FedRAMP High, ITAR, CJIS |

---

## Table of Contents

1. [Phase 0 — Prerequisites & Foundation](#phase-0--prerequisites--foundation)
2. [Phase 1 — Identity & Auth Layer (Okta)](#phase-1--identity--auth-layer-okta)
3. [Phase 2 — AgentCore Platform Setup](#phase-2--agentcore-platform-setup)
4. [Phase 3 — Networking & Compute Foundation](#phase-3--networking--compute-foundation)
5. [Phase 4 — MCP Server Development](#phase-4--mcp-server-development)
6. [Phase 5 — Gateway Target Registration](#phase-5--gateway-target-registration)
7. [Phase 6 — Memory & Guardrails Configuration](#phase-6--memory--guardrails-configuration)
8. [Phase 7 — Secrets & Configuration](#phase-7--secrets--configuration)
9. [Phase 8 — Observability & Monitoring](#phase-8--observability--monitoring)
10. [Phase 9 — Security Hardening](#phase-9--security-hardening)
11. [Phase 10 — Testing & Validation](#phase-10--testing--validation)
12. [Phase 11 — Deployment & Go-Live](#phase-11--deployment--go-live)
13. [Terraform Module Structure](#terraform-module-structure)
14. [Risk Register](#risk-register)

---

## Phase 0 — Prerequisites & Foundation

**Duration**: 1-2 weeks

### 0.1 AWS Account Setup

| Task | Details |
|------|---------|
| GovCloud account provisioned | Dedicated account for MCP Hub workload |
| Bedrock AgentCore access | Request AgentCore service access in GovCloud region |
| AWS Organizations enrollment | SCPs applied (deny public S3, enforce encryption) |
| Terraform state backend | S3 bucket + DynamoDB lock table |
| IAM baseline | Admin role, Terraform execution role, break-glass role |

### 0.2 Okta Prerequisites

| Task | Details |
|------|---------|
| Okta Custom Authorization Server | Dedicated: `mcp-obs-auth-server` |
| OIDC Discovery URL | `https://<org>.okta.com/oauth2/<auth-server-id>/.well-known/openid-configuration` |
| Client applications registered | Desktop app (Auth Code + PKCE), M2M cloud agents, M2M on-prem agents |
| Scopes defined | `mcp:splunk:read`, `mcp:splunk:search`, `mcp:dynatrace:read`, `mcp:s3-lake:query`, `mcp:cloudwatch:read` |
| Groups created | `mcp-admins`, `mcp-analysts`, `mcp-readers`, `mcp-m2m-agents` |
| Scope-to-group mapping | Claim policies assign scopes based on group membership |
| MFA policy | Adaptive MFA (Okta Verify Push/TOTP/FIDO2) for user flows; no MFA for M2M |
| Access policies | `mcp-desktop-policy` (15 min TTL), `mcp-m2m-policy` (1 hr TTL) |

### 0.3 Enterprise Network Coordination

| Task | Owner | Details |
|------|-------|---------|
| VPC CIDR allocation | Network Team | Reserve `10.x.0.0/16` in enterprise IPAM |
| DNS delegation | Network Team | Subdomain for internal service discovery |
| Network route confirmation | Network Team | Confirm enterprise tools reachable from MCP VPC |
| AgentCore Gateway accessibility | Network Team | Confirm inbound paths (TGW, VPN, PrivateLink) to AgentCore endpoint |

### 0.4 Vendor API Access

| Vendor | Prerequisite |
|--------|-------------|
| Splunk | Service account; REST API token; search capability |
| Dynatrace | API token with `metrics.read`, `entities.read`, `problems.read`, `logs.read` |
| S3 Lakehouse | Cross-account IAM role for Athena + Glue catalog access |
| CloudWatch | Cross-account IAM role with `cloudwatch:GetMetricData`, `logs:FilterLogEvents` |

---

## Phase 1 — Identity & Auth Layer (Okta)

**Duration**: 1 week

### 1.1 Okta Authorization Server Configuration

| Setting | Value |
|---------|-------|
| Name | `mcp-obs-auth-server` |
| Audience | `mcp-obs-hub-api` |
| Issuer | `https://<org>.okta.com/oauth2/<auth-server-id>` |
| Token Signing | RS256 |
| Access Token Lifetime | 15 min (user), 1 hr (M2M) |
| Refresh Token | Enabled for user flows only |

### 1.2 Custom Scopes

| Scope | Description | Granted To Groups |
|-------|-------------|-------------------|
| `mcp:splunk:read` | Splunk read-only queries | analysts, readers, m2m-agents |
| `mcp:splunk:search` | Splunk SPL search execution | analysts, admins, m2m-agents |
| `mcp:dynatrace:read` | Dynatrace metrics, problems, entities | analysts, readers, m2m-agents |
| `mcp:s3-lake:query` | S3 Lakehouse Athena queries | analysts, admins, m2m-agents |
| `mcp:cloudwatch:read` | CloudWatch metrics, logs, alarms | analysts, readers, m2m-agents |

### 1.3 Client Application Registrations

| Client | Grant Type | Redirect URIs | Notes |
|--------|-----------|---------------|-------|
| `mcp-desktop-app` | Authorization Code + PKCE | `http://localhost:*/callback` | For Claude, Cursor, VS Code |
| `mcp-m2m-cloud-agents` | Client Credentials | N/A | For ECS/Lambda agents |
| `mcp-m2m-onprem-agents` | Client Credentials | N/A | For datacenter agents |

### 1.4 Group Assignments

| Group | Members | Default Scopes |
|-------|---------|----------------|
| `mcp-admins` | Platform engineers | All scopes |
| `mcp-analysts` | SREs, incident responders | All read + search scopes |
| `mcp-readers` | General engineers | Read-only scopes |
| `mcp-m2m-agents` | Service accounts | All read scopes |

---

## Phase 2 — AgentCore Platform Setup

**Duration**: 2-3 weeks

### 2.1 AgentCore Gateway

```hcl
resource "aws_bedrockagentcore_gateway" "obs_mcp_gateway" {
  name          = "obs-mcp-hub-gateway"
  protocol_type = "MCP"

  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url   = "https://<org>.okta.com/oauth2/<id>/.well-known/openid-configuration"
      allowed_clients = [
        "<okta-desktop-app-client-id>",
        "<okta-m2m-cloud-client-id>",
        "<okta-m2m-onprem-client-id>"
      ]
    }
  }
}
```

**Gateway Outputs:**

| Output | Usage |
|--------|-------|
| Gateway URL | `https://<gateway-id>.bedrock-agentcore.us-gov-west-1.amazonaws.com` — MCP clients connect here |
| Gateway ID | Used in GatewayTarget registrations |
| Gateway ARN | Used in IAM policies |

### 2.2 AgentCore Memory

```hcl
resource "aws_bedrockagentcore_memory" "obs_memory" {
  name = "obs-mcp-memory"

  memory_strategies {
    episodic {
      namespace_prefix = "/episodes/"
      event_expiry_days = 90
    }
    semantic {
      namespace_prefix = "/facts/"
    }
    summary {
      namespace_prefix = "/summaries/"
    }
    user_preferences {
      namespace_prefix = "/preferences/"
    }
  }
}
```

**Memory Use Cases for Observability:**

| Scenario | Memory Type | Example |
|----------|-------------|---------|
| Incident investigation | Episodic | "In last session, user queried Splunk for error X and found root cause was service Y" |
| Learned context | Semantic | "prod-db-cluster is the primary PostgreSQL cluster in us-gov-west-1" |
| User preferences | Preferences | "User prefers Dynatrace for APM queries and Splunk for security logs" |
| Long investigation | Summary | Compressed 50-message investigation into 5 key findings |

### 2.3 AgentCore Guardrails

```hcl
resource "aws_bedrockagentcore_guardrail" "obs_guardrails" {
  name = "obs-mcp-guardrails"

  content_policy {
    filters {
      type       = "PII"
      action     = "BLOCK"
      categories = ["SSN", "CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER"]
    }
  }

  topic_policy {
    topics {
      name       = "restricted-environments"
      definition = "Queries about classified or restricted environments not in the approved list"
      action     = "BLOCK"
    }
  }

  word_policy {
    managed_word_lists = ["PROFANITY"]
  }
}
```

**Guardrail Rules for Observability:**

| Rule | Type | Action | Rationale |
|------|------|--------|-----------|
| PII in log queries | Content Filter | BLOCK | Prevent accidental PII exposure from Splunk logs |
| PHI detection | Content Filter | BLOCK | Healthcare-related PII in CloudWatch logs |
| Restricted environments | Topic | BLOCK | Prevent queries against classified systems |
| Excessive data retrieval | Governance | WARN | Alert when Athena query scans > 1TB |
| Cross-account boundary | Governance | BLOCK | Prevent access to non-approved AWS accounts |

### 2.4 AgentCore Runtime (Optional — for managed agent hosting)

```hcl
resource "aws_bedrockagentcore_runtime" "obs_runtime" {
  name = "obs-mcp-runtime"

  container_configuration {
    image_uri = "${aws_ecr_repository.obs_agent.repository_url}:latest"
    protocol  = "HTTP"
  }

  scaling_configuration {
    min_instances = 2
    max_instances = 10
  }

  health_check {
    path     = "/health"
    interval = 30
  }
}
```

---

## Phase 3 — Networking & Compute Foundation

**Duration**: 2-3 weeks

### 3.1 VPC Configuration

| Resource | Specification |
|----------|--------------|
| VPC CIDR | `10.x.0.0/16` (from enterprise IPAM) |
| Public Subnets | `10.x.0.0/24` (AZ-a), `10.x.1.0/24` (AZ-b) — NAT Gateways |
| Private Subnets | `10.x.10.0/24` (AZ-a), `10.x.11.0/24` (AZ-b) — ECS tasks |
| NAT Gateways | One per AZ (for vendor API egress if needed) |
| VPC Endpoints | S3 (gateway), CloudWatch Logs, Secrets Manager, ECR, STS, Bedrock (interface) |
| DNS | Enable DNS hostnames + resolution |
| Flow Logs | Enabled → CloudWatch Logs (14-day retention) |

### 3.2 Security Groups

| SG Name | Inbound | Outbound |
|---------|---------|----------|
| `mcp-ecs-sg` | TCP 3000-3010 from AgentCore Gateway (managed) | TCP 443 to VPC endpoints + enterprise network |
| `mcp-vpce-sg` | TCP 443 from `mcp-ecs-sg` | — |

> **Note**: AgentCore Gateway manages its own ingress. ECS tasks only need to allow traffic from AgentCore's internal routing.

### 3.3 ECS Cluster

| Configuration | Value |
|---------------|-------|
| Cluster Name | `mcp-obs-cluster` |
| Capacity Provider | FARGATE (100% — managed targets need predictable performance) |
| Container Insights | Enabled |
| Execute Command | Enabled (restricted to admin role) |

### 3.4 ECR Repositories

| Repository | Lifecycle Policy |
|------------|-----------------|
| `mcp/splunk-server` | Keep last 10 images; expire untagged after 7 days |
| `mcp/dynatrace-server` | Same |
| `mcp/s3-lake-server` | Same |
| `mcp/cloudwatch-server` | Same |

---

## Phase 4 — MCP Server Development

**Duration**: 4-6 weeks (parallel development)

### 4.1 Common MCP Server Template

```
mcp-server-template/
├── src/
│   ├── server.ts              # MCP server initialization (MCP SDK)
│   ├── transport.ts           # HTTP/SSE transport (Streamable HTTP)
│   ├── health.ts              # GET /health endpoint
│   ├── tools/
│   │   ├── index.ts           # Tool registry
│   │   └── <tool_name>.ts     # Individual tool implementations
│   ├── clients/
│   │   └── vendor_client.ts   # Vendor API client (retry, pooling)
│   ├── credentials/
│   │   └── provider.ts        # Secrets Manager fetch + cache (GATEWAY_IAM_ROLE)
│   ├── middleware/
│   │   ├── logging.ts         # Structured JSON logging
│   │   ├── tracing.ts         # X-Ray trace segments
│   │   └── metrics.ts         # CloudWatch EMF metrics
│   └── config.ts              # SSM Parameter Store config loader
├── Dockerfile
├── package.json
├── tsconfig.json
└── tests/
    ├── unit/
    └── integration/
```

### 4.2 MCP Server Specifications

#### Splunk MCP Server

| Tool | Input Schema | Vendor API |
|------|-------------|-----------|
| `splunk_search` | `{ query: string, earliest: string, latest: string, max_results: number }` | `POST /services/search/jobs` + `GET /services/search/jobs/{sid}/results` |
| `splunk_get_alerts` | `{ severity: string, count: number }` | `GET /services/alerts/fired_alerts` |
| `splunk_list_indexes` | `{}` | `GET /services/data/indexes` |
| `splunk_saved_searches` | `{ owner: string }` | `GET /services/saved/searches` |

#### Dynatrace MCP Server

| Tool | Input Schema | Vendor API |
|------|-------------|-----------|
| `dt_get_problems` | `{ from: string, to: string, status: string }` | `GET /api/v2/problems` |
| `dt_query_metrics` | `{ selector: string, from: string, to: string, resolution: string }` | `GET /api/v2/metrics/query` |
| `dt_get_entities` | `{ entitySelector: string, fields: string[] }` | `GET /api/v2/entities` |
| `dt_get_logs` | `{ query: string, from: string, to: string, limit: number }` | `POST /api/v2/logs/search` |

#### S3 Lakehouse MCP Server

| Tool | Input Schema | Vendor API |
|------|-------------|-----------|
| `lake_query_athena` | `{ sql: string, database: string, output_location: string }` | Athena `StartQueryExecution` + `GetQueryResults` |
| `lake_list_tables` | `{ database: string }` | Glue `GetTables` |
| `lake_get_partitions` | `{ database: string, table: string }` | Glue `GetPartitions` |
| `lake_describe_schema` | `{ database: string, table: string }` | Glue `GetTable` |

#### CloudWatch MCP Server

| Tool | Input Schema | Vendor API |
|------|-------------|-----------|
| `cw_get_metrics` | `{ namespace: string, metric_name: string, dimensions: object, period: number, stat: string, start: string, end: string }` | `GetMetricData` |
| `cw_query_logs` | `{ log_group: string, query: string, start_time: number, end_time: number, limit: number }` | `StartQuery` + `GetQueryResults` |
| `cw_describe_alarms` | `{ state: string, prefix: string }` | `DescribeAlarms` |
| `cw_get_dashboards` | `{ prefix: string }` | `ListDashboards` + `GetDashboard` |

### 4.3 ECS Task Definitions

| Parameter | Splunk | Dynatrace | S3 Lake | CloudWatch |
|-----------|--------|-----------|---------|-----------|
| CPU | 512 | 512 | 1024 | 512 |
| Memory | 1024 MB | 1024 MB | 2048 MB | 1024 MB |
| Port | 3000 | 3001 | 3002 | 3003 |
| Min Tasks | 2 | 2 | 2 | 2 |
| Max Tasks | 10 | 10 | 6 | 10 |
| Scale Target | CPU 70% | CPU 70% | CPU 70% | CPU 70% |
| Task Role | `mcp-splunk-task-role` | `mcp-dynatrace-task-role` | `mcp-s3lake-task-role` | `mcp-cloudwatch-task-role` |

### 4.4 Dockerfile (Common Pattern)

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY src/ ./src/
COPY tsconfig.json ./
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 1001 -S mcp && adduser -S mcp -u 1001
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER mcp
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

---

## Phase 5 — Gateway Target Registration

**Duration**: 1-2 weeks

### 5.1 Register Each MCP Server as a Gateway Target

```hcl
resource "aws_bedrockagentcore_gateway_target" "splunk" {
  name               = "splunk-mcp-target"
  gateway_identifier = aws_bedrockagentcore_gateway.obs_mcp_gateway.id

  credential_provider_configurations {
    credential_provider_type = "GATEWAY_IAM_ROLE"
  }

  target_configuration {
    mcp_server {
      url = "http://splunk-mcp.mcp-obs.internal:3000/mcp"
    }
  }
}

resource "aws_bedrockagentcore_gateway_target" "dynatrace" {
  name               = "dynatrace-mcp-target"
  gateway_identifier = aws_bedrockagentcore_gateway.obs_mcp_gateway.id

  credential_provider_configurations {
    credential_provider_type = "GATEWAY_IAM_ROLE"
  }

  target_configuration {
    mcp_server {
      url = "http://dynatrace-mcp.mcp-obs.internal:3001/mcp"
    }
  }
}

resource "aws_bedrockagentcore_gateway_target" "s3lake" {
  name               = "s3lake-mcp-target"
  gateway_identifier = aws_bedrockagentcore_gateway.obs_mcp_gateway.id

  credential_provider_configurations {
    credential_provider_type = "GATEWAY_IAM_ROLE"
  }

  target_configuration {
    mcp_server {
      url = "http://s3lake-mcp.mcp-obs.internal:3002/mcp"
    }
  }
}

resource "aws_bedrockagentcore_gateway_target" "cloudwatch" {
  name               = "cloudwatch-mcp-target"
  gateway_identifier = aws_bedrockagentcore_gateway.obs_mcp_gateway.id

  credential_provider_configurations {
    credential_provider_type = "GATEWAY_IAM_ROLE"
  }

  target_configuration {
    mcp_server {
      url = "http://cloudwatch-mcp.mcp-obs.internal:3003/mcp"
    }
  }
}
```

### 5.2 Tool Schema Registration

Each target includes a tool schema so the Gateway can handle `tools/list` discovery:

```hcl
  tool_schema {
    inline_payload = [
      {
        name        = "splunk_search"
        description = "Execute an SPL search query against Splunk"
        input_schema = jsonencode({
          type = "object"
          properties = {
            query       = { type = "string", description = "SPL query string" }
            earliest    = { type = "string", description = "Start time (e.g., -24h)" }
            latest      = { type = "string", description = "End time (e.g., now)" }
            max_results = { type = "number", description = "Maximum results to return" }
          }
          required = ["query"]
        })
      },
      // ... additional tools
    ]
  }
```

### 5.3 Cloud Map Service Discovery

| Namespace | Service | Target |
|-----------|---------|--------|
| `mcp-obs.internal` | `splunk-mcp` | ECS service (port 3000) |
| `mcp-obs.internal` | `dynatrace-mcp` | ECS service (port 3001) |
| `mcp-obs.internal` | `s3lake-mcp` | ECS service (port 3002) |
| `mcp-obs.internal` | `cloudwatch-mcp` | ECS service (port 3003) |

---

## Phase 6 — Memory & Guardrails Configuration

**Duration**: 1-2 weeks

### 6.1 Memory Configuration

| Setting | Value |
|---------|-------|
| Episodic Memory | Enabled; 90-day retention |
| Semantic Memory | Enabled; extract facts about infrastructure |
| Session Summaries | Enabled; compress after 20 messages |
| User Preferences | Enabled; learn tool preferences |
| Namespace Pattern | `/{strategy}/{actorId}/{sessionId}/` |

**Memory Integration in MCP Servers:**

Each MCP server includes memory context by reading from AgentCore Memory API before executing tool calls, enabling:
- "Last time you investigated this alert, the root cause was X"
- "Based on your previous queries, checking Splunk index `security` first"

### 6.2 Guardrails Configuration

| Rule Name | Type | Config | Action |
|-----------|------|--------|--------|
| `pii-in-logs` | Content Filter (PII) | SSN, Credit Card, Email, Phone | BLOCK |
| `phi-in-logs` | Content Filter (PHI) | Medical record numbers, diagnoses | BLOCK |
| `restricted-envs` | Topic | Classified/restricted system names | BLOCK |
| `data-volume-limit` | Governance (custom) | Athena scan > 1TB | WARN + require confirmation |
| `cross-account-boundary` | Governance (custom) | Access non-approved account IDs | BLOCK |
| `profanity` | Word Policy | Managed profanity list | BLOCK |

### 6.3 Guardrails Integration Points

| Point | When | Action |
|-------|------|--------|
| Pre-tool-call | Before executing vendor API call | Validate input doesn't reference restricted systems |
| Post-tool-call | After receiving vendor API response | Scan response for PII/PHI; redact if found |
| Memory write | Before storing to episodic memory | Strip any detected PII from stored context |

---

## Phase 7 — Secrets & Configuration

**Duration**: 1 week

### 7.1 Secrets Manager

| Secret Path | Content | Rotation |
|-------------|---------|----------|
| `/mcp/splunk/api-token` | Splunk REST API bearer token | 30 days |
| `/mcp/dynatrace/api-token` | Dynatrace API token | 30 days |
| `/mcp/cloudwatch/cross-account-role-arn` | IAM role ARN | Manual |
| `/mcp/okta/client-secrets` | Okta client secrets (for rotation validation) | Manual |

### 7.2 SSM Parameter Store

| Parameter Path | Type | Value |
|----------------|------|-------|
| `/mcp/config/splunk/endpoint` | SecureString | Splunk base URL |
| `/mcp/config/dynatrace/endpoint` | SecureString | Dynatrace environment URL |
| `/mcp/config/s3-lake/catalog-database` | String | Glue catalog database name |
| `/mcp/config/s3-lake/output-bucket` | String | Athena query results bucket |
| `/mcp/config/cloudwatch/accounts` | StringList | Target account IDs |
| `/mcp/config/agentcore/gateway-id` | String | AgentCore Gateway ID |
| `/mcp/config/agentcore/memory-id` | String | AgentCore Memory resource ID |

### 7.3 KMS

| Key | Alias | Usage |
|-----|-------|-------|
| CMK | `alias/mcp-obs-key` | Encrypts: Secrets Manager, CloudWatch Logs, S3 audit bucket |
| Key Policy | — | Grants to ECS execution role, AgentCore service role |
| Rotation | Annual automatic | — |

### 7.4 IAM Roles

| Role | Trust | Permissions |
|------|-------|-------------|
| `mcp-agentcore-service-role` | Bedrock AgentCore | ECS task invocation, Secrets Manager, KMS, Cloud Map |
| `mcp-ecs-execution-role` | ECS Tasks | ECR pull, Secrets Manager (execution secrets), CloudWatch Logs |
| `mcp-splunk-task-role` | ECS Tasks | `secretsmanager:GetSecretValue` (ARN: `*/mcp/splunk/*`) |
| `mcp-dynatrace-task-role` | ECS Tasks | `secretsmanager:GetSecretValue` (ARN: `*/mcp/dynatrace/*`) |
| `mcp-s3lake-task-role` | ECS Tasks | S3, Athena, Glue (scoped to lakehouse resources) |
| `mcp-cloudwatch-task-role` | ECS Tasks | `sts:AssumeRole` (cross-account), `cloudwatch:*`, `logs:*` |

---

## Phase 8 — Observability & Monitoring

**Duration**: 1-2 weeks

### 8.1 CloudWatch

| Resource | Configuration |
|----------|--------------|
| Container Insights | Enabled on ECS cluster |
| Log Groups | `/ecs/mcp-splunk`, `/ecs/mcp-dynatrace`, `/ecs/mcp-s3lake`, `/ecs/mcp-cloudwatch` |
| Log Retention | 90 days |
| Custom Metrics Namespace | `MCP/ObservabilityHub` |

**Custom Metrics:**

| Metric | Dimensions | Description |
|--------|-----------|-------------|
| `ToolInvocationCount` | `Server`, `ToolName` | Count of MCP tool_call requests |
| `ToolLatencyMs` | `Server`, `ToolName` | End-to-end tool execution latency |
| `ToolErrorRate` | `Server`, `ToolName` | Percentage of failed tool calls |
| `GuardrailBlockCount` | `RuleType`, `Server` | Guardrail-blocked requests |
| `MemoryHitRate` | `MemoryType` | Percentage of requests with relevant memory context |
| `VendorApiLatencyMs` | `Server`, `Vendor` | External API call latency |

**Alarms:**

| Alarm | Threshold | Action |
|-------|-----------|--------|
| High Error Rate | > 5% for 5 min | SNS → PagerDuty |
| High Latency | P99 > 10s for 5 min | SNS → PagerDuty |
| Task Count Low | < 2 running for 3 min | SNS → Ops team |
| Guardrail Spike | > 20 blocks in 5 min | SNS → Security team |
| Gateway 5xx | > 10 per minute | SNS → PagerDuty |

### 8.2 X-Ray Tracing

| Configuration | Value |
|---------------|-------|
| Sampling Rate | 10% (prod), 100% (non-prod) |
| Trace Path | AgentCore GW → ECS Task → Vendor API |
| Annotations | `mcp.server`, `mcp.tool`, `user.id`, `client.type`, `guardrail.action` |

### 8.3 CloudTrail

| Configuration | Value |
|---------------|-------|
| Scope | Multi-region, management + data events |
| S3 Logging | Dedicated audit bucket with KMS encryption |
| Insights | Enabled (unusual API activity) |
| AgentCore Events | Gateway access, target invocations, memory reads/writes |

### 8.4 AgentCore-Specific Monitoring

| Metric | Source | Significance |
|--------|--------|-------------|
| Gateway Request Count | AgentCore metrics | Total MCP traffic volume |
| Gateway Auth Failures | AgentCore metrics | Unauthorized access attempts |
| Memory Utilization | AgentCore metrics | Episodic memory storage growth |
| Guardrail Actions | AgentCore metrics | Content policy enforcement rate |
| Target Health | AgentCore health checks | Backend MCP server availability |

---

## Phase 9 — Security Hardening

**Duration**: 1-2 weeks

### 9.1 Network Security

| Control | Implementation |
|---------|---------------|
| No public IPs on ECS tasks | `assignPublicIp: DISABLED` |
| VPC endpoints for AWS services | Avoids internet for AWS API calls |
| Security group references | SG-to-SG rules (not CIDR-based) |
| VPC Flow Logs | Reject-only filter for security alerting |

### 9.2 Container Security

| Control | Implementation |
|---------|---------------|
| Non-root user | `USER mcp` in Dockerfile |
| Read-only filesystem | `readonlyRootFilesystem: true` |
| No privileged mode | `privileged: false` |
| ECR image scanning | On-push scanning; block on CRITICAL |
| Image signing | Notation/Cosign for provenance |
| GuardDuty ECS Runtime | Detect anomalous process/network behavior |
| Inspector | Continuous vulnerability scanning |

### 9.3 Application Security

| Control | Implementation |
|---------|---------------|
| Input validation | JSON Schema on all tool inputs |
| Output sanitization | AgentCore Guardrails (PII/PHI stripping) |
| Rate limiting | AgentCore Gateway built-in + per-user scope limits |
| Timeout enforcement | 30s per vendor call; 60s total |
| Error masking | Generic errors to client; details in logs only |

### 9.4 Compliance Controls

| Framework | Requirement | Implementation |
|-----------|------------|----------------|
| FedRAMP High AC-2 | Account Management | IAM roles + Okta groups |
| FedRAMP High AU-2 | Audit Events | CloudTrail + AgentCore audit logs |
| FedRAMP High SC-8 | Transmission Confidentiality | TLS 1.3 (AgentCore managed) |
| FedRAMP High SC-28 | Protection at Rest | KMS CMK encryption |
| FedRAMP High SI-4 | System Monitoring | CloudWatch + GuardDuty + Security Hub |
| FedRAMP High SI-10 | Input Validation | JSON Schema + Guardrails |

---

## Phase 10 — Testing & Validation

**Duration**: 2-3 weeks

### 10.1 Testing Strategy

| Level | Scope | Tools |
|-------|-------|-------|
| Unit | Tool handlers, credential provider, response formatter | Jest / Pytest |
| Integration | MCP protocol compliance; AgentCore Gateway connectivity | MCP Inspector, custom client |
| Contract | Vendor API response schemas | Pact / schema validation |
| End-to-End | Client → AgentCore GW → Target → Vendor | Custom E2E suite |
| Memory | Episodic recall accuracy, semantic extraction | Custom memory test suite |
| Guardrails | PII detection, topic blocking, governance rules | Adversarial test inputs |
| Load | 1000 rps sustained; burst 2000 rps | k6 / Artillery |
| Security | OWASP API Top 10, JWT manipulation | OWASP ZAP, Burp Suite |
| Chaos | Task failures, vendor timeouts, AgentCore failover | AWS FIS |

### 10.2 AgentCore-Specific Tests

| Test Case | Expected |
|-----------|----------|
| Gateway with valid Okta JWT | Routes to correct target, returns tool_result |
| Gateway with expired JWT | Returns 401 Unauthorized |
| Gateway with wrong audience | Returns 401 Unauthorized |
| Gateway with unknown client ID | Returns 403 Forbidden |
| Target with tool_result containing PII | Guardrail blocks/redacts PII |
| Memory recall after previous session | Context from prior investigation available |
| Target down (health check fail) | Gateway returns service unavailable |
| New target registration | Immediately discoverable via tools/list |

### 10.3 Load Test Targets

| Metric | Target |
|--------|--------|
| P50 Latency | < 500ms |
| P99 Latency | < 5s |
| Throughput | 1000 rps sustained |
| Error Rate | < 0.1% |
| Memory Recall Latency | < 200ms |
| Guardrail Check Latency | < 50ms overhead |

---

## Phase 11 — Deployment & Go-Live

**Duration**: 1-2 weeks

### 11.1 Deployment Strategy

| Aspect | Approach |
|--------|----------|
| IaC | Terraform apply via pipeline |
| AgentCore resources | Terraform (Gateway, Targets, Memory, Guardrails) |
| ECS services | Rolling update (min healthy 100%, max 200%) |
| Rollback | Previous task def revision (auto on health check failure); target URL revert |
| Feature flags | SSM Parameter Store toggles |

### 11.2 Go-Live Checklist

- [ ] AgentCore Gateway deployed and accessible
- [ ] Okta authorization server tested (all 3 client types)
- [ ] CUSTOM_JWT validating tokens correctly (valid/invalid/expired)
- [ ] All 4 Gateway Targets registered and healthy
- [ ] All 4 ECS MCP servers passing health checks
- [ ] Vendor API connectivity confirmed from ECS tasks
- [ ] Memory working (write + recall across sessions)
- [ ] Guardrails tested (PII blocked, topic restricted, governance enforced)
- [ ] Secrets rotation tested end-to-end
- [ ] CloudWatch dashboards showing all custom metrics
- [ ] Alarms validated (triggered and resolved)
- [ ] X-Ray traces visible end-to-end (Gateway → Target → Vendor)
- [ ] Load test passed (1000 rps, P99 < 5s)
- [ ] Security scan (ECR image scan, Inspector, no CRITICAL findings)
- [ ] MCP Inspector validation for all tools via Gateway URL
- [ ] GuardDuty enabled on ECS cluster
- [ ] Security Hub compliance score > 90%
- [ ] Runbook documented for common failures
- [ ] On-call rotation established
- [ ] Enterprise Network Team confirmed all ingress paths active

### 11.3 Day-2 Operations

| Process | Cadence | Owner |
|---------|---------|-------|
| Secret rotation monitoring | Daily (automated) | Platform Team |
| Memory utilization review | Weekly | Platform Team |
| Guardrail rule tuning | Bi-weekly | Security + Platform |
| Image vulnerability scanning | On every push | Pipeline |
| Capacity review | Weekly | Platform Team |
| SLO review | Monthly | SRE Team |
| Okta scope audit | Quarterly | Security Team |
| AgentCore service updates | As released | Platform Team |
| DR drill | Semi-annual | Platform + SRE |

---

## Terraform Module Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   │   ├── main.tf           # VPC, subnets, NAT GW, VPC endpoints
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── agentcore-gateway/
│   │   ├── main.tf           # Gateway, authorizer config
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── agentcore-memory/
│   │   ├── main.tf           # Memory strategies, namespaces
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── agentcore-guardrails/
│   │   ├── main.tf           # Content policies, topic policies, governance
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── agentcore-target/      # Reusable per MCP server target
│   │   ├── main.tf           # GatewayTarget, tool schema, credentials
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── ecs-cluster/
│   │   ├── main.tf           # ECS cluster, capacity providers
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── mcp-service/           # Reusable per MCP server (ECS service)
│   │   ├── main.tf           # Task def, service, auto-scaling, Cloud Map
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── secrets/
│   │   ├── main.tf           # Secrets Manager, KMS key, SSM parameters
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── observability/
│   │   ├── main.tf           # CloudWatch dashboards, alarms, X-Ray, CloudTrail
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── iam/
│       ├── main.tf           # All IAM roles and policies
│       ├── variables.tf
│       └── outputs.tf
└── README.md
```

---

## Risk Register

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|-----------|-----------|
| 1 | AgentCore service not GA in GovCloud | Critical | Medium | Monitor AWS roadmap; have Non-AgentCore architecture as fallback |
| 2 | AgentCore API breaking changes | High | Medium | Pin Terraform provider version; test in staging before prod |
| 3 | Vendor API rate limits exceeded | High | Medium | Per-tool rate limiting; caching for repeated queries |
| 4 | Okta outage prevents authentication | Critical | Low | JWKS cache in Gateway; monitor Okta status |
| 5 | Memory storage costs grow unbounded | Medium | Medium | 90-day expiry; monitor utilization; adjust retention |
| 6 | Guardrails false positives block legitimate queries | Medium | Medium | Tune rules iteratively; WARN mode before BLOCK |
| 7 | ECS task cold start affects latency | Medium | Medium | Min 2 tasks always running |
| 8 | AgentCore Gateway throughput limits | High | Low | Monitor Gateway metrics; request limit increase if needed |
| 9 | Vendor API schema changes break MCP tools | Medium | Medium | Contract tests in CI; alerting on unexpected responses |
| 10 | Single region deployment (DR) | High | — | Document multi-region path; state replication |

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0 — Prerequisites | Weeks 1-2 | Okta admin, Network Team, AWS (AgentCore access) |
| Phase 1 — Okta Auth | Weeks 2-3 | Phase 0 complete |
| Phase 2 — AgentCore Platform | Weeks 2-4 | Phase 0 + AgentCore access granted |
| Phase 3 — Networking + Compute | Weeks 3-5 | Phase 0 complete |
| Phase 4 — MCP Servers | Weeks 3-8 | Phase 3 complete (parallel dev) |
| Phase 5 — Target Registration | Weeks 6-7 | Phase 2 + 4 complete |
| Phase 6 — Memory & Guardrails | Weeks 5-7 | Phase 2 complete |
| Phase 7 — Secrets | Weeks 5-6 | Phase 3 complete |
| Phase 8 — Observability | Weeks 6-8 | Phase 4+ in progress |
| Phase 9 — Security | Weeks 7-9 | Phase 4-8 complete |
| Phase 10 — Testing | Weeks 8-11 | All phases functionally complete |
| Phase 11 — Go-Live | Weeks 11-12 | Phase 10 passed |

**Total Estimated Duration: 11-13 weeks** (with parallel execution)

---

## AgentCore vs Non-AgentCore — Implementation Effort Comparison

| Area | AgentCore (this) | Non-AgentCore |
|------|-----------------|---------------|
| Gateway setup | ~1 week (declarative) | ~2 weeks (API GW + Lambda Auth + ALB) |
| Auth integration | Built-in CUSTOM_JWT | Build Lambda Authorizer from scratch |
| MCP Routing | Gateway Targets (config only) | ALB rules + VPC Link + target groups |
| Memory | Managed (config only) | N/A (not available) |
| Guardrails | Managed (config only) | Custom application code |
| MCP Server dev | Same | Same |
| Total IaC lines | ~40% less | Baseline |
| Operational burden | Lower (managed components) | Higher (all self-managed) |
| Vendor lock-in | Higher | Lower |
