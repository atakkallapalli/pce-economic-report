# Technical Implementation Plan — Enterprise Observability MCP Hub (Non-AgentCore)

## Document Info

| Field | Value |
|-------|-------|
| **Project** | Enterprise Observability MCP Hub — Non-AgentCore Deployment |
| **Region** | AWS GovCloud (us-gov-west-1) |
| **Auth** | Okta OIDC / OAuth 2.0 + AWS IAM |
| **IaC** | Terraform (modular) |
| **Compliance** | FedRAMP High, ITAR, CJIS |

---

## Table of Contents

1. [Phase 0 — Prerequisites & Foundation](#phase-0--prerequisites--foundation)
2. [Phase 1 — Identity & Auth Layer](#phase-1--identity--auth-layer)
3. [Phase 2 — Networking & Compute Foundation](#phase-2--networking--compute-foundation)
4. [Phase 3 — MCP Server Development](#phase-3--mcp-server-development)
5. [Phase 4 — API Gateway & Routing](#phase-4--api-gateway--routing)
6. [Phase 5 — Secrets & Configuration](#phase-5--secrets--configuration)
7. [Phase 6 — Observability & Monitoring](#phase-6--observability--monitoring)
8. [Phase 7 — Security Hardening](#phase-7--security-hardening)
9. [Phase 8 — Testing & Validation](#phase-8--testing--validation)
10. [Phase 9 — Deployment & Go-Live](#phase-9--deployment--go-live)
11. [Terraform Module Structure](#terraform-module-structure)
12. [Risk Register](#risk-register)

---

## Phase 0 — Prerequisites & Foundation

**Duration**: 1-2 weeks

### 0.1 AWS Account Setup

| Task | Details |
|------|---------|
| GovCloud account provisioned | Dedicated account for MCP Hub workload |
| AWS Organizations enrollment | SCPs applied (deny public S3, enforce encryption) |
| Terraform state backend | S3 bucket + DynamoDB lock table in same account |
| IAM baseline | Admin role, Terraform execution role, break-glass role |

### 0.2 Okta Prerequisites

| Task | Details |
|------|---------|
| Okta Custom Authorization Server | Dedicated auth server for MCP Hub |
| OIDC Discovery URL | `https://<org>.okta.com/oauth2/<auth-server-id>/.well-known/openid-configuration` |
| Client applications registered | One per MCP client type (desktop, M2M cloud, M2M on-prem) |
| Scopes defined | `mcp:splunk:read`, `mcp:splunk:search`, `mcp:dynatrace:read`, `mcp:s3-lake:query`, `mcp:cloudwatch:read` |
| Groups created | `mcp-admins`, `mcp-analysts`, `mcp-readers`, `mcp-m2m-agents` |
| Scope-to-group mapping | Claim policies assign scopes based on group membership |
| MFA policy | Adaptive MFA for user flows; no MFA for M2M client credentials |

### 0.3 Enterprise Network Coordination

| Task | Owner | Details |
|------|-------|---------|
| VPC CIDR allocation | Network Team | Reserve `10.x.0.0/16` in enterprise IPAM |
| DNS delegation | Network Team | Subdomain for MCP API (e.g., `mcp-obs.internal.company.com`) |
| Network route confirmation | Network Team | Confirm enterprise tools (Splunk, Dynatrace, etc.) reachable from MCP VPC |
| Security group allowlisting | Network Team + MCP Team | Outbound access to vendor API endpoints |

### 0.4 Vendor API Access

| Vendor | Prerequisite |
|--------|-------------|
| Splunk | Service account with search capabilities; REST API token generated |
| Dynatrace | API token with `metrics.read`, `entities.read`, `problems.read`, `logs.read` scopes |
| S3 Lakehouse | Cross-account IAM role for Athena query execution; Glue catalog access |
| CloudWatch | Cross-account IAM role with `cloudwatch:GetMetricData`, `logs:FilterLogEvents` |

---

## Phase 1 — Identity & Auth Layer

**Duration**: 1-2 weeks

### 1.1 Lambda Authorizer Development

```
lambda-authorizer/
├── src/
│   ├── handler.py          # Lambda entry point
│   ├── jwks_validator.py   # Okta JWKS fetch + JWT validation (RS256)
│   ├── scope_mapper.py     # Scope → IAM policy document generator
│   └── cache.py            # In-memory JWKS cache (5 min TTL)
├── tests/
│   ├── test_validator.py
│   └── test_scope_mapper.py
├── requirements.txt        # PyJWT, cryptography, requests
└── Dockerfile              # For local testing
```

**Key Implementation Details:**

| Aspect | Detail |
|--------|--------|
| Runtime | Python 3.12 (Lambda) |
| JWKS Fetch | HTTP GET to Okta JWKS URI; cache keys for 5 minutes |
| Validation | Verify RS256 signature, `exp`, `iss` (Okta auth server), `aud` (MCP Hub client ID) |
| Scope Extraction | Parse `scp` claim from JWT payload |
| Policy Output | Return IAM policy document with `Allow`/`Deny` per route |
| Error Handling | 401 for invalid/expired tokens; 403 for insufficient scopes |
| Cold Start Optimization | Minimal dependencies; layer for PyJWT + cryptography |

### 1.2 IAM Role Definitions

| Role | Trust | Permissions |
|------|-------|-------------|
| `mcp-lambda-authorizer-role` | Lambda service | `logs:CreateLogGroup`, `logs:PutLogEvents` |
| `mcp-ecs-execution-role` | ECS Tasks service | `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `logs:CreateLogStream`, `secretsmanager:GetSecretValue` (scoped) |
| `mcp-splunk-task-role` | ECS Tasks service | `secretsmanager:GetSecretValue` (ARN: `*/mcp/splunk/*`), `logs:PutLogEvents` |
| `mcp-dynatrace-task-role` | ECS Tasks service | `secretsmanager:GetSecretValue` (ARN: `*/mcp/dynatrace/*`), `logs:PutLogEvents` |
| `mcp-s3lake-task-role` | ECS Tasks service | `s3:GetObject` (lakehouse bucket), `athena:StartQueryExecution`, `athena:GetQueryResults`, `glue:GetTable`, `glue:GetPartitions` |
| `mcp-cloudwatch-task-role` | ECS Tasks service | `cloudwatch:GetMetricData`, `cloudwatch:ListMetrics`, `logs:FilterLogEvents`, `logs:DescribeLogGroups` |

---

## Phase 2 — Networking & Compute Foundation

**Duration**: 2-3 weeks

### 2.1 VPC Configuration

| Resource | Specification |
|----------|--------------|
| VPC CIDR | `10.x.0.0/16` (from enterprise IPAM) |
| Public Subnets | `10.x.0.0/24` (AZ-a), `10.x.1.0/24` (AZ-b) — NAT Gateways only |
| Private Subnets | `10.x.10.0/24` (AZ-a), `10.x.11.0/24` (AZ-b) — ALB + ECS tasks |
| NAT Gateways | One per AZ (high availability) |
| VPC Endpoints | S3 (gateway), CloudWatch Logs, Secrets Manager, ECR, STS (interface) |
| DNS | Enable DNS hostnames + resolution |
| Flow Logs | Enabled → CloudWatch Logs (14-day retention) |

### 2.2 Security Groups

| SG Name | Inbound | Outbound |
|---------|---------|----------|
| `mcp-alb-sg` | TCP 443 from VPC Link ENIs | TCP 3000-3010 to `mcp-ecs-sg` |
| `mcp-ecs-sg` | TCP 3000-3010 from `mcp-alb-sg` | TCP 443 to NAT GW (vendor APIs); TCP 443 to VPC endpoints |
| `mcp-vpce-sg` | TCP 443 from `mcp-ecs-sg` | — |

### 2.3 ECS Cluster

| Configuration | Value |
|---------------|-------|
| Cluster Name | `mcp-obs-cluster` |
| Capacity Provider | FARGATE + FARGATE_SPOT (70/30 split for non-critical) |
| Container Insights | Enabled |
| Execute Command | Enabled (for debugging; restricted to admin role) |

### 2.4 Application Load Balancer

| Configuration | Value |
|---------------|-------|
| Type | Internal (not internet-facing) |
| Subnets | Private subnets (AZ-a, AZ-b) |
| Listener | HTTPS :443 (ACM certificate) |
| Health Check | HTTP GET `/health` (path per target group) |
| Idle Timeout | 60 seconds |
| Target Groups | One per MCP server (IP-based, Fargate) |

**Routing Rules:**

| Priority | Condition | Target Group |
|----------|-----------|--------------|
| 1 | Path: `/splunk/*` | `tg-splunk-mcp` |
| 2 | Path: `/dynatrace/*` | `tg-dynatrace-mcp` |
| 3 | Path: `/s3-lake/*` | `tg-s3lake-mcp` |
| 4 | Path: `/cloudwatch/*` | `tg-cloudwatch-mcp` |
| Default | — | Fixed 404 response |

### 2.5 ECR Repositories

| Repository | Lifecycle Policy |
|------------|-----------------|
| `mcp/splunk-server` | Keep last 10 images; expire untagged after 7 days |
| `mcp/dynatrace-server` | Same |
| `mcp/s3-lake-server` | Same |
| `mcp/cloudwatch-server` | Same |
| `mcp/lambda-authorizer` | Same |

---

## Phase 3 — MCP Server Development

**Duration**: 4-6 weeks (parallel development)

### 3.1 Common MCP Server Template

All MCP servers share a consistent structure:

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
│   │   └── provider.ts        # Secrets Manager fetch + cache
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

### 3.2 MCP Server Specifications

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

### 3.3 ECS Task Definitions

| Parameter | Splunk | Dynatrace | S3 Lake | CloudWatch |
|-----------|--------|-----------|---------|-----------|
| CPU | 512 | 512 | 1024 | 512 |
| Memory | 1024 MB | 1024 MB | 2048 MB | 1024 MB |
| Port | 3000 | 3001 | 3002 | 3003 |
| Min Tasks | 2 | 2 | 2 | 2 |
| Max Tasks | 10 | 10 | 6 | 10 |
| Scale Target | CPU 70% | CPU 70% | CPU 70% | CPU 70% |
| Task Role | `mcp-splunk-task-role` | `mcp-dynatrace-task-role` | `mcp-s3lake-task-role` | `mcp-cloudwatch-task-role` |

### 3.4 Dockerfile (Common Pattern)

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

## Phase 4 — API Gateway & Routing

**Duration**: 1-2 weeks

### 4.1 HTTP API Configuration

| Setting | Value |
|---------|-------|
| Protocol | HTTP (v2 API) |
| Endpoint Type | Regional |
| Custom Domain | `mcp-obs.internal.company.com` (ACM cert) |
| Default Throttle | 1000 requests/second, 2000 burst |
| CORS | Disabled (server-to-server) |
| Access Logging | Enabled → CloudWatch Logs |

### 4.2 Routes

| Method | Path | Integration | Auth |
|--------|------|-------------|------|
| POST | `/mcp/splunk/{proxy+}` | VPC Link → ALB → `/splunk/{proxy+}` | JWT Authorizer |
| POST | `/mcp/dynatrace/{proxy+}` | VPC Link → ALB → `/dynatrace/{proxy+}` | JWT Authorizer |
| POST | `/mcp/s3-lake/{proxy+}` | VPC Link → ALB → `/s3-lake/{proxy+}` | JWT Authorizer |
| POST | `/mcp/cloudwatch/{proxy+}` | VPC Link → ALB → `/cloudwatch/{proxy+}` | JWT Authorizer |
| GET | `/health` | Mock (200 OK) | None |

### 4.3 JWT Authorizer Configuration

| Setting | Value |
|---------|-------|
| Authorizer Type | JWT (or Lambda for custom scope mapping) |
| Issuer | `https://<org>.okta.com/oauth2/<auth-server-id>` |
| Audience | `mcp-hub-api` (registered in Okta) |
| Identity Source | `$request.header.Authorization` |
| Token Cache TTL | 300 seconds |

### 4.4 VPC Link

| Setting | Value |
|---------|-------|
| Target | Internal ALB ARN |
| Subnets | Private subnets |
| Security Groups | `mcp-alb-sg` |

---

## Phase 5 — Secrets & Configuration

**Duration**: 1 week

### 5.1 Secrets Manager

| Secret Path | Content | Rotation |
|-------------|---------|----------|
| `/mcp/splunk/api-token` | Splunk REST API bearer token | 30 days |
| `/mcp/splunk/endpoint-url` | `https://splunk.internal:8089` | Manual |
| `/mcp/dynatrace/api-token` | Dynatrace API token | 30 days |
| `/mcp/dynatrace/environment-id` | Dynatrace env ID | Manual |
| `/mcp/cloudwatch/cross-account-role-arn` | IAM role ARN for cross-account access | Manual |

### 5.2 SSM Parameter Store

| Parameter Path | Type | Value |
|----------------|------|-------|
| `/mcp/config/splunk/endpoint` | SecureString | Splunk base URL |
| `/mcp/config/dynatrace/endpoint` | SecureString | Dynatrace base URL |
| `/mcp/config/s3-lake/catalog-database` | String | Glue catalog database name |
| `/mcp/config/s3-lake/output-bucket` | String | Athena query results bucket |
| `/mcp/config/cloudwatch/accounts` | StringList | Target account IDs for cross-account |
| `/mcp/config/feature-flags/rate-limit-per-user` | String | `100` |

### 5.3 KMS

| Key | Alias | Usage |
|-----|-------|-------|
| CMK | `alias/mcp-obs-key` | Encrypts: Secrets Manager secrets, CloudWatch Logs, S3 audit logs |
| Key Policy | — | Grants to ECS execution role, Lambda authorizer role, CloudWatch Logs service |
| Rotation | Annual automatic rotation | — |

---

## Phase 6 — Observability & Monitoring

**Duration**: 1-2 weeks

### 6.1 CloudWatch

| Resource | Configuration |
|----------|--------------|
| Container Insights | Enabled on ECS cluster |
| Log Groups | `/ecs/mcp-splunk`, `/ecs/mcp-dynatrace`, `/ecs/mcp-s3lake`, `/ecs/mcp-cloudwatch`, `/lambda/mcp-authorizer` |
| Log Retention | 90 days (compliant with FedRAMP audit requirements) |
| Custom Metrics | Namespace: `MCP/ObservabilityHub` |

**Custom Metrics:**

| Metric | Dimensions | Description |
|--------|-----------|-------------|
| `ToolInvocationCount` | `Server`, `ToolName` | Count of MCP tool_call requests |
| `ToolLatencyMs` | `Server`, `ToolName` | End-to-end tool execution latency |
| `ToolErrorRate` | `Server`, `ToolName` | Percentage of failed tool calls |
| `AuthFailureCount` | `Reason` | JWT validation failures |
| `VendorApiLatencyMs` | `Server`, `VendorEndpoint` | External API call latency |

**Alarms:**

| Alarm | Threshold | Action |
|-------|-----------|--------|
| High Error Rate | > 5% for 5 minutes | SNS → PagerDuty |
| High Latency | P99 > 10s for 5 minutes | SNS → PagerDuty |
| Task Count Low | < 2 running tasks for 3 minutes | SNS → Ops team |
| Auth Failure Spike | > 50 failures in 5 minutes | SNS → Security team |
| 5xx on ALB | > 10 per minute | SNS → PagerDuty |

### 6.2 X-Ray Tracing

| Configuration | Value |
|---------------|-------|
| Sampling Rate | 10% (production), 100% (non-prod) |
| Trace Segments | API GW → Lambda Auth → ALB → ECS Task → Vendor API |
| Service Map | Auto-generated from trace data |
| Annotations | `mcp.server`, `mcp.tool`, `user.id`, `client.type` |

### 6.3 CloudTrail

| Configuration | Value |
|---------------|-------|
| Trail Scope | Multi-region, management + data events |
| S3 Logging | Enabled (dedicated audit bucket with KMS encryption) |
| Data Events | S3 object-level, Lambda invocations |
| Log File Validation | Enabled |
| Insights | Enabled (unusual API activity detection) |

---

## Phase 7 — Security Hardening

**Duration**: 1-2 weeks

### 7.1 Network Security

| Control | Implementation |
|---------|---------------|
| No public IPs on ECS tasks | `assignPublicIp: DISABLED` |
| VPC endpoints for AWS services | Avoids NAT for AWS API calls |
| Security group references | SG-to-SG rules (not CIDR-based) |
| NACLs | Default deny; allow established connections |
| VPC Flow Logs | Enabled; reject-only filter for alerting |

### 7.2 Container Security

| Control | Implementation |
|---------|---------------|
| Non-root user | `USER mcp` in Dockerfile |
| Read-only filesystem | `readonlyRootFilesystem: true` in task definition |
| No privileged mode | `privileged: false` |
| ECR image scanning | On-push scanning; block deployment on CRITICAL findings |
| Image signing | Notation/Cosign for image provenance |
| Resource limits | CPU/memory hard limits prevent noisy-neighbor |

### 7.3 Application Security

| Control | Implementation |
|---------|---------------|
| Input validation | JSON Schema validation on all MCP tool inputs |
| Output sanitization | Strip PII/PHI from tool_result before returning |
| Rate limiting (application) | Per-user token bucket in addition to API GW throttling |
| Timeout enforcement | 30s per vendor API call; 60s total per MCP request |
| Error masking | Internal errors return generic message; details logged only |

### 7.4 Compliance

| Framework | Control Mapping |
|-----------|----------------|
| FedRAMP High AC-2 | IAM roles + Okta groups for access control |
| FedRAMP High AU-2 | CloudTrail + CloudWatch Logs for audit |
| FedRAMP High SC-8 | TLS 1.3 encryption in transit |
| FedRAMP High SC-28 | KMS encryption at rest |
| FedRAMP High SI-4 | CloudWatch alarms + X-Ray for monitoring |

---

## Phase 8 — Testing & Validation

**Duration**: 2-3 weeks

### 8.1 Testing Strategy

| Level | Scope | Tools |
|-------|-------|-------|
| Unit | Individual tool handlers, credential provider, response formatter | Jest / Pytest |
| Integration | MCP protocol compliance (tools/list, tools/call flow) | MCP Inspector, custom test client |
| Contract | Vendor API response schemas | Pact / schema validation |
| End-to-End | Full request path: Client → API GW → ALB → ECS → Vendor | Custom E2E suite |
| Load | Sustained 1000 rps; burst 2000 rps | k6 / Artillery |
| Security | OWASP API Security Top 10 | OWASP ZAP, Burp Suite |
| Chaos | Task failures, vendor API timeouts | AWS FIS (Fault Injection) |

### 8.2 MCP Protocol Compliance

| Test Case | Expected |
|-----------|----------|
| `initialize` request | Returns capabilities (tools, streaming) |
| `tools/list` | Returns all registered tools with JSON Schema |
| `tools/call` with valid input | Returns `tool_result` with content |
| `tools/call` with invalid input | Returns error with schema violation details |
| `tools/call` with expired JWT | Returns 401 |
| `tools/call` with insufficient scope | Returns 403 |
| Streaming response (SSE) | Partial results streamed for long queries |

### 8.3 Load Test Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| P50 Latency | < 500ms | Responsive agent experience |
| P99 Latency | < 5s | Acceptable for complex queries |
| Throughput | 1000 rps sustained | Enterprise-wide agent usage |
| Error Rate | < 0.1% | Reliability SLO |
| Cold Start (ECS) | < 30s | New task registration |

---

## Phase 9 — Deployment & Go-Live

**Duration**: 1-2 weeks

### 9.1 Deployment Strategy

| Aspect | Approach |
|--------|----------|
| IaC | Terraform apply via pipeline (Atlantis or TF Cloud) |
| Container deployment | ECS rolling update (minimum healthy 100%, maximum 200%) |
| Rollback | Previous task definition revision (automatic on health check failure) |
| Feature flags | SSM Parameter Store toggles per MCP server |
| Canary | Route 10% traffic to new version via weighted target group |

### 9.2 Go-Live Checklist

- [ ] All Terraform plans reviewed and approved
- [ ] Okta authorization server tested with all client types
- [ ] Lambda Authorizer validated with valid/invalid/expired tokens
- [ ] All 4 MCP servers passing health checks
- [ ] Vendor API connectivity confirmed from ECS tasks
- [ ] Secrets rotation tested end-to-end
- [ ] CloudWatch dashboards showing metrics
- [ ] Alarms validated (triggered and resolved)
- [ ] X-Ray traces visible end-to-end
- [ ] Load test passed (1000 rps, P99 < 5s)
- [ ] Security scan (ECR image scan, no CRITICAL findings)
- [ ] MCP Inspector validation for all tools
- [ ] Runbook documented for common failure scenarios
- [ ] On-call rotation established
- [ ] Enterprise Network Team confirmed routing active

### 9.3 Day-2 Operations

| Process | Cadence | Owner |
|---------|---------|-------|
| Secret rotation monitoring | Daily (automated) | Platform Team |
| Image vulnerability scanning | On every push | CI/CD Pipeline |
| Capacity review | Weekly | Platform Team |
| SLO review | Monthly | SRE Team |
| Okta scope audit | Quarterly | Security Team |
| Disaster recovery drill | Semi-annual | Platform + SRE |

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
│   ├── ecs-cluster/
│   │   ├── main.tf           # ECS cluster, capacity providers
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── mcp-service/           # Reusable per MCP server
│   │   ├── main.tf           # Task def, service, target group, auto-scaling
│   │   ├── variables.tf      # server_name, port, cpu, memory, image, task_role
│   │   └── outputs.tf
│   ├── api-gateway/
│   │   ├── main.tf           # HTTP API, routes, VPC link, JWT authorizer
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── lambda-authorizer/
│   │   ├── main.tf           # Lambda function, IAM role, layers
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── alb/
│   │   ├── main.tf           # ALB, listener, default action
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
| 1 | Vendor API rate limits exceeded | High | Medium | Per-tool rate limiting in MCP server; caching for repeated queries |
| 2 | Okta outage prevents authentication | Critical | Low | JWKS cache (5 min); consider local JWKS backup |
| 3 | ECS task cold start affects latency | Medium | Medium | Min 2 tasks always running; provisioned concurrency alternative |
| 4 | Cross-account network routing failure | High | Low | Health checks detect; runbook for network team escalation |
| 5 | Secret rotation breaks vendor connectivity | High | Medium | Staged rotation (new secret valid before old expires); automated validation |
| 6 | MCP protocol breaking changes | Medium | Low | Pin MCP SDK version; protocol version negotiation in `initialize` |
| 7 | Vendor API schema changes | Medium | Medium | Contract tests in CI; alerting on unexpected response formats |
| 8 | Single region deployment | High (DR) | — | Document multi-region expansion path; S3 cross-region replication for state |

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0 — Prerequisites | Weeks 1-2 | Okta admin, Network Team, Vendor teams |
| Phase 1 — Auth Layer | Weeks 2-4 | Phase 0 complete |
| Phase 2 — Network + Compute | Weeks 3-5 | Phase 0 complete (parallel with Phase 1) |
| Phase 3 — MCP Servers | Weeks 3-8 | Phase 2 complete (parallel development) |
| Phase 4 — API Gateway | Weeks 5-6 | Phase 1 + 2 complete |
| Phase 5 — Secrets | Weeks 5-6 | Phase 2 complete |
| Phase 6 — Observability | Weeks 6-8 | Phase 3+ in progress |
| Phase 7 — Security | Weeks 7-9 | Phase 3-6 complete |
| Phase 8 — Testing | Weeks 8-10 | All phases functionally complete |
| Phase 9 — Go-Live | Weeks 10-11 | Phase 8 passed |

**Total Estimated Duration: 10-12 weeks** (with parallel execution)
