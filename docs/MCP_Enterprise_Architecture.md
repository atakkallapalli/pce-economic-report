# Enterprise MCP Server Architecture — AWS GovCloud

## Overview

This document describes the enterprise architecture for hosting **centralized MCP (Model Context Protocol) servers** in a dedicated **AWS GovCloud** account using **ECS Fargate** containers. The architecture enables AI agents deployed across desktop clients, other AWS accounts, and on-premises servers to securely connect to and query vendor data sources through a unified MCP gateway.

> **Companion Diagram**: See [`MCP_Enterprise_Architecture.drawio`](./MCP_Enterprise_Architecture.drawio) for the full visual architecture (2 pages: Enterprise Overview + Security Architecture Detail).

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent Consumer Zone                               │
│                                                                             │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────────────┐  │
│  │  On-Premises  │  │  Desktop Clients │  │  Other AWS GovCloud Accounts  │  │
│  │  Datacenter   │  │  (Claude, Cursor │  │  (Analytics, Operations,      │  │
│  │  AI Agents    │  │   VS Code, Apps) │  │   Research Workloads)         │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────────┬────────────────┘  │
│         │                   │                            │                   │
│    Site-to-Site VPN    HTTPS + OAuth      PrivateLink / Transit Gateway      │
│         │               + mTLS                           │                   │
└─────────┼───────────────────┼────────────────────────────┼──────────────────┘
          │                   │                            │
┌─────────▼───────────────────▼────────────────────────────▼──────────────────┐
│              AWS GovCloud — Centralized MCP Hub Account                      │
│              (FedRAMP High | ITAR | CJIS | DoD SRG IL4/IL5)                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Network Edge: Shield Advanced → WAF v2 → API Gateway (mTLS/OAuth) │     │
│  │  Connectivity: VPN Gateway | Transit Gateway | PrivateLink          │     │
│  └────────────────────────────────┬────────────────────────────────────┘     │
│                                   │                                          │
│  ┌────────────────────────────────▼────────────────────────────────────┐     │
│  │  MCP Services VPC (10.0.0.0/16)                                     │     │
│  │                                                                     │     │
│  │  Public Subnets: NLB + ALB (path-based routing)                     │     │
│  │                                                                     │     │
│  │  Private Subnets: ECS Fargate Cluster                               │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │     │
│  │  │ FRED MCP   │ │ Jira MCP   │ │ Confluence │ │ GitHub MCP │  ...  │     │
│  │  │ Server     │ │ Server     │ │ MCP Server │ │ Server     │       │     │
│  │  │ :3000      │ │ :3001      │ │ :3002      │ │ :3003      │       │     │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘       │     │
│  │        └───────────────┴──────────────┴──────────────┘               │     │
│  │                        │ (via NAT Gateway)                           │     │
│  └────────────────────────┼────────────────────────────────────────────┘     │
│                           ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │  Supporting Services                                         │            │
│  │  Secrets Manager | KMS | SSM | ECR | CloudWatch | CloudTrail │            │
│  │  GuardDuty | Security Hub | AWS Config | Inspector            │            │
│  └──────────────────────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
   ┌──────────────┐                 ┌─────────────────────┐
   │  FRED API    │                 │  Atlassian Cloud    │
   │  GitHub API  │                 │  Vendor N API       │
   └──────────────┘                 └─────────────────────┘
```

---

## 1. Centralized MCP Hub Account

### Why Centralized?

| Benefit | Description |
|---|---|
| **Single Pane of Control** | One account to manage all MCP server deployments, secrets, and access policies |
| **Unified Security Posture** | Consistent authentication, authorization, and encryption across all vendor integrations |
| **Cost Optimization** | Shared infrastructure (ALB, NAT GW, ECR) reduces per-team overhead |
| **Compliance Simplification** | Single FedRAMP boundary to audit and certify |
| **Operational Excellence** | Centralized logging, monitoring, and incident response |

### GovCloud Selection

AWS GovCloud (US) regions are selected for:
- **FedRAMP High** baseline compliance (inherent to GovCloud)
- Physical isolation from commercial AWS regions
- Operated exclusively by US persons on US soil
- Supports ITAR, CJIS, DoD SRG IL4/IL5 workloads
- All data-at-rest and in-transit encryption meets FIPS 140-2 requirements

---

## 2. ECS Container Architecture

### Service Layout

Each MCP server runs as an independent **ECS Fargate service** within a shared ECS cluster:

| MCP Service | Container Port | CPU | Memory | Description |
|---|---|---|---|---|
| `fred-mcp-server` | 3000 | 512 | 1024 MB | FRED economic data (browse, search, get_series) |
| `atlassian-jira-mcp` | 3001 | 512 | 1024 MB | Jira issue management and sprint tracking |
| `atlassian-confluence-mcp` | 3002 | 512 | 1024 MB | Confluence knowledge base access |
| `github-mcp` | 3003 | 256 | 512 MB | GitHub repository and code search |
| `vendor-n-mcp` | 300N | 256 | 512 MB | Extensible slot for future integrations |

### Key Design Decisions

- **Fargate (serverless)**: No EC2 instances to patch; AWS manages the underlying infrastructure
- **Per-service task definitions**: Each MCP server has its own task definition with a dedicated IAM Task Role
- **Multi-AZ deployment**: Tasks distributed across at least 2 availability zones
- **Auto Scaling**: Per-service target tracking on CPU utilization (target: 70%, min: 2, max: 10)
- **Service Discovery**: AWS Cloud Map (`mcp.internal` namespace) for internal DNS resolution
- **Immutable deployments**: Blue/green via CodeDeploy with automatic rollback

### Container Image Pipeline

```
GitHub Push → CodePipeline → CodeBuild (build + unit test)
    → Inspector (CVE scan) → ECR (immutable tag)
    → CodeDeploy (blue/green to ECS)
```

- Images stored in **ECR** with immutable tags and lifecycle policies
- **Inspector** continuous scanning for CVEs
- No `latest` tag; all deployments reference digest-pinned images

---

## 3. Network Architecture

### VPC Design

```
MCP Services VPC: 10.0.0.0/16
├── Public Subnets (ALB/NLB):  10.0.0.0/24 (AZ-a), 10.0.1.0/24 (AZ-b)
├── Private Subnets (ECS):     10.0.10.0/24 (AZ-a), 10.0.11.0/24 (AZ-b)
└── Isolated Subnets (Data):   10.0.20.0/24 (AZ-a), 10.0.21.0/24 (AZ-b)
```

### Connectivity Patterns

#### Desktop AI Clients (Claude Desktop, Cursor, VS Code, Custom Apps)

```
Desktop Client → Internet → Shield → WAF → API Gateway (mTLS + OAuth 2.0)
    → VPC Link → ALB (path routing) → ECS Task
```

- **Transport**: HTTPS with TLS 1.3
- **Authentication**: OAuth 2.0 Client Credentials + mTLS client certificate
- **Rate Limiting**: WAF (1000 req/min) + API Gateway usage plans

#### Cross-Account AI Agents (Other GovCloud Accounts)

```
Agent (Account B) → VPC Interface Endpoint → PrivateLink
    → NLB → ALB → ECS Task
```

- **Transport**: AWS PrivateLink — traffic never leaves AWS backbone
- **Authentication**: IAM AssumeRole with ExternalId + SigV4
- **Access Control**: VPC Endpoint Service principal allowlisting per account

#### On-Premises AI Agents

```
On-Prem Agent → VPN Gateway (IPSec/IKEv2) → Virtual Private Gateway
    → Transit Gateway → NLB → ALB → ECS Task
```

- **Transport**: IPSec VPN tunnel (or AWS Direct Connect for dedicated bandwidth)
- **Authentication**: mTLS + OAuth 2.0 (tokens obtained via Cognito Client Credentials)
- **Routing**: Transit Gateway with isolated route tables per connectivity domain

### Load Balancing

| Component | Role |
|---|---|
| **NLB (Network Load Balancer)** | PrivateLink target; TLS passthrough for cross-account traffic |
| **ALB (Application Load Balancer)** | Path-based routing to individual MCP services (`/fred/*`, `/jira/*`, etc.) |

---

## 4. Security Architecture

### 4.1 Authentication (AuthN)

| Mechanism | Use Case | Details |
|---|---|---|
| **OAuth 2.0 Client Credentials** | Machine-to-machine (M2M) | Cognito issues JWT tokens with custom scopes per MCP service |
| **SAML 2.0 / OIDC Federation** | Human users via corporate IdP | Federated identity for interactive desktop clients |
| **Mutual TLS (mTLS)** | High-trust clients | API Gateway validates client certificates; truststore in S3 |
| **IAM SigV4** | Cross-account AWS workloads | AssumeRole with ExternalId; temporary credentials only |
| **API Keys** | Throttling identifier (not auth) | Usage plans enforce per-consumer rate limits and quotas |
| **MFA** | All human access | TOTP enforced via Cognito for interactive sessions |

#### Token Scopes (Cognito Custom Scopes)

```
fred:read       - Read FRED economic data
fred:search     - Search FRED series catalog
jira:read       - Read Jira issues and sprints
jira:write      - Create/update Jira issues
confluence:read - Read Confluence pages
github:read     - Read repository data
github:write    - Create PRs and issues
```

### 4.2 Authorization (AuthZ)

| Control | Description |
|---|---|
| **Cognito RBAC** | Groups (admin, analyst, reader) mapped to IAM roles and API scopes |
| **Per-Service Task Roles** | Each MCP server has a unique IAM Task Role scoped to only its vendor secrets |
| **API Gateway Resource Policies** | Allowlist specific AWS accounts and VPC endpoints |
| **VPC Endpoint Policies** | Restrict which principals can invoke through PrivateLink |
| **Service Control Policies (SCPs)** | Org-wide guardrails: deny non-GovCloud regions, require encryption, enforce tagging |
| **Deny-by-default** | All access denied unless explicitly granted |

#### IAM Task Role Example (FRED MCP)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws-us-gov:secretsmanager:*:*:secret:mcp/fred-*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/service": "fred-mcp"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws-us-gov:kms:*:*:key/<fred-kms-key-id>"
    }
  ]
}
```

### 4.3 Network Segmentation

| Layer | Control | Rule |
|---|---|---|
| **WAF v2** | OWASP Top 10, rate limiting, geo-restriction | US-only, 1000 req/min, IP allowlisting |
| **Shield Advanced** | DDoS protection | L3/L4/L7 with 24/7 DRT |
| **Security Groups** | Stateful firewall | ALB SG: 443 from WAF; ECS SG: 3000-3010 from ALB SG only |
| **NACLs** | Stateless firewall | Private subnets deny all except ALB subnet CIDRs |
| **VPC Isolation** | ECS in private subnets | No public IPs; outbound only via NAT Gateway |
| **PrivateLink** | Cross-account connectivity | No internet transit; unidirectional |
| **Transit Gateway** | Route isolation | Separate route tables per connectivity domain |
| **VPN/Direct Connect** | On-premises connectivity | IPSec/IKEv2 encrypted tunnels |

### 4.4 Data Protection

| Control | Details |
|---|---|
| **Encryption in Transit** | TLS 1.3 on all endpoints; FIPS-compliant cipher suites |
| **Encryption at Rest** | KMS CMK (FIPS 140-2 Level 3); annual key rotation |
| **Secrets Management** | AWS Secrets Manager with 30-day auto-rotation |
| **Secret Injection** | Secrets injected at ECS task launch (not in env vars or code) |
| **Per-Service Key Aliases** | Each MCP server uses its own KMS key alias |
| **Container Image Signing** | ECR image signing with Notation/Cosign |

### 4.5 Observability & Compliance

| Service | Purpose | Retention |
|---|---|---|
| **CloudTrail** | API audit trail (management + data events) | 365 days |
| **VPC Flow Logs** | Network traffic logging | 90 days |
| **CloudWatch Logs** | ECS container logs + API Gateway execution logs | 90 days |
| **CloudWatch Metrics** | Container Insights, custom MCP latency/error metrics | 15 months |
| **GuardDuty** | ECS runtime threat detection + anomaly detection | Continuous |
| **Security Hub** | NIST 800-53 automated compliance checks | Continuous |
| **AWS Config** | Resource compliance and drift detection | Continuous |
| **Inspector** | Container CVE scanning (continuous) | Continuous |
| **S3 Access Logs** | ALB access logs (tamper-proof with Object Lock) | 90 days |

---

## 5. Mandatory Resource Tagging

All resources in the MCP Hub account must carry these tags (enforced by SCP):

| Tag Key | Example Value | Purpose |
|---|---|---|
| `env` | `prod`, `staging`, `dev` | Environment isolation |
| `service` | `fred-mcp`, `jira-mcp` | Service identification and cost allocation |
| `owner` | `platform-team@org.gov` | Ownership and incident routing |
| `compliance` | `fedramp-high` | Compliance framework tracking |
| `data-classification` | `internal`, `cui` | Data sensitivity level |
| `cost-center` | `CC-12345` | Financial allocation |

---

## 6. Adding a New MCP Server

To onboard a new vendor MCP server:

1. **Build container image** following the existing Dockerfile patterns
2. **Create ECR repository** with immutable tags and scanning enabled
3. **Create ECS task definition** with dedicated IAM Task Role
4. **Store vendor credentials** in Secrets Manager (tagged with `service: <name>-mcp`)
5. **Create KMS key alias** for the new service's secrets
6. **Add ALB listener rule** for path-based routing (`/<vendor>/*`)
7. **Register in Cloud Map** service discovery namespace
8. **Create Cognito scopes** (`<vendor>:read`, `<vendor>:write`)
9. **Update API Gateway** with new resource/method routes
10. **Update VPC Endpoint Service** allowed principals (if cross-account)
11. **Deploy via CodePipeline** (blue/green with automatic rollback)

---

## 7. Diagram Files

| File | Description |
|---|---|
| [`MCP_Enterprise_Architecture.drawio`](./MCP_Enterprise_Architecture.drawio) | Full draw.io diagram (open in diagrams.net or VS Code draw.io extension) |
| Page 1: "Enterprise Overview" | Complete infrastructure view with all components and connectivity |
| Page 2: "Security Architecture Detail" | Defense-in-depth layers with request flow walkthroughs |
