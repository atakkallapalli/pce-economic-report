# Architecture & Technical Documentation

## Stock Market Dashboard - R Shiny Application on AWS ECS

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Application Architecture](#application-architecture)
3. [Infrastructure Architecture](#infrastructure-architecture)
4. [Data Flow](#data-flow)
5. [Terraform Module Reference](#terraform-module-reference)
6. [Deployment Pipeline](#deployment-pipeline)
7. [Security Architecture](#security-architecture)
8. [Monitoring & Observability](#monitoring--observability)
9. [Scaling & Performance](#scaling--performance)
10. [Configuration Reference](#configuration-reference)
11. [Disaster Recovery](#disaster-recovery)

---

## System Overview

The Stock Market Dashboard is an interactive R Shiny web application that provides time series analysis and forecasting for stocks organized into four thematic categories tracking market trends since the COVID-19 pandemic. The application is containerized with Docker and deployed on AWS ECS Fargate behind an Application Load Balancer.

### Key Characteristics

| Property | Value |
|---|---|
| Language | R 4.4.x |
| Framework | Shiny + shinydashboard |
| Container Runtime | AWS ECS Fargate |
| Container Port | 3838 |
| Data Source | Yahoo Finance (live via `quantmod`) |
| Forecasting Models | ARIMA, ETS, TBATS |
| Infrastructure as Code | Terraform >= 1.5.0 |
| AWS Provider | ~> 5.0 |

---

## Application Architecture

### Component Diagram

```
+----------------------------------------------------------+
|                    R Shiny Application                    |
|                        (app.R)                           |
+----------------------------------------------------------+
|                                                          |
|  +------------------+  +-----------------------------+   |
|  |   UI Layer       |  |   Server Layer              |   |
|  |  (dashboardPage) |  |   (reactive logic)          |   |
|  |                  |  |                             |   |
|  |  - Sidebar       |  |  - Stock data fetching      |   |
|  |    - Category    |  |  - Returns computation      |   |
|  |    - Tickers     |  |  - Volatility calculation   |   |
|  |    - Date range  |  |  - Correlation analysis     |   |
|  |                  |  |  - Forecast generation      |   |
|  |  - 7 Tab Panels  |  |  - Reactive data binding    |   |
|  +------------------+  +-----------------------------+   |
|                                                          |
+----------------------------------------------------------+
|                   R Package Dependencies                  |
|  shiny, shinydashboard, quantmod, forecast, plotly,      |
|  dplyr, tidyr, DT, xts, zoo, tseries, shinycssloaders   |
+----------------------------------------------------------+
```

### Stock Categories

| Category | Tickers | Description |
|---|---|---|
| AI & Machine Learning | NVDA, MSFT, GOOGL, META, AMD, AMZN, CRM, PLTR, SNOW, AVGO | Companies leading artificial intelligence innovation |
| Capital Expenditure | CAT, DE, URI, ETN, EMR, VMC, MLM, PCAR, ROK, AME | Infrastructure and industrial companies benefiting from capex cycles |
| Data Storage & Cloud | STX, WDC, NTAP, PURE, NET, DDOG, MDB, DELL, HPE, IBM | Data storage, cloud infrastructure, and enterprise technology |
| Pandemic Market Drivers | AAPL, TSLA, MSFT, AMZN, GOOGL, META, NVDA, NFLX, COST, UNH | Mega-cap stocks shaping post-COVID market trends |

### Dashboard Tabs

| Tab | Purpose | Key Visualizations |
|---|---|---|
| Overview | Category summary and performance metrics | Normalized price chart, value boxes, summary table |
| Time Series Analysis | Individual stock deep-dive | Price/volume/returns charts with moving averages, descriptive stats, return distribution |
| Comparative Analysis | Cross-stock comparison | Cumulative returns overlay, monthly returns heatmap |
| Volatility Analysis | Risk assessment | Rolling annualized volatility with S&P 500 benchmark, volatility rankings |
| Correlation Matrix | Relationship analysis | Interactive heatmap with adjustable time windows (3m, 6m, 12m, full) |
| Forecasting | Trend prediction | ARIMA/ETS/TBATS models with confidence intervals, residual diagnostics |
| Data Explorer | Raw data access | Searchable OHLCV table with CSV download |

### Key Helper Functions

| Function | Purpose |
|---|---|
| `fetch_stock_data()` | Downloads OHLCV data from Yahoo Finance via `quantmod::getSymbols()` |
| `compute_returns()` | Calculates log returns from price series |
| `compute_rolling_volatility()` | Computes rolling annualized volatility (default 21-day window) |
| `normalize_prices()` | Converts prices to percentage change from start date |

---

## Infrastructure Architecture

### AWS Architecture Diagram

```
                         Internet
                            |
                     +------+------+
                     |  AWS WAF    |
                     |  (Optional) |
                     +------+------+
                            |
                     +------+------+
                     |     ALB     |  <-- Public Subnets (2 AZs)
                     | (Port 80/  |      Security Group: HTTP/HTTPS inbound
                     |  443)      |
                     +------+------+
                            |
              +-------------+-------------+
              |                           |
       +------+------+            +------+------+
       |  ECS Task   |            |  ECS Task   |  <-- Private Subnets (2 AZs)
       |  (Fargate)  |            |  (Fargate)  |      Security Group: ALB-only inbound
       |  Port 3838  |            |  Port 3838  |
       +------+------+            +------+------+
              |                           |
              +-------------+-------------+
                            |
                     +------+------+
                     | NAT Gateway |  <-- Outbound internet (Yahoo Finance API)
                     +------+------+
                            |
                     +------+------+
                     |   Internet  |
                     |   Gateway   |
                     +-------------+
```

### Network Architecture

| Component | CIDR / Range | Purpose |
|---|---|---|
| VPC | `10.1.0.0/16` | Isolated network for all resources |
| Public Subnet AZ-a | `10.1.0.0/24` | ALB, NAT Gateway |
| Public Subnet AZ-b | `10.1.1.0/24` | ALB (multi-AZ) |
| Private Subnet AZ-a | `10.1.10.0/24` | ECS tasks |
| Private Subnet AZ-b | `10.1.11.0/24` | ECS tasks (multi-AZ) |

### AWS Resources Created

| Resource | Count | Purpose |
|---|---|---|
| VPC | 1 | Network isolation |
| Public Subnets | 2 | ALB placement (2 AZs) |
| Private Subnets | 2 | ECS task placement (2 AZs) |
| Internet Gateway | 1 | Public subnet internet access |
| NAT Gateway | 1 | Private subnet outbound access |
| Elastic IP | 1 | Static IP for NAT Gateway |
| Application Load Balancer | 1 | Traffic distribution |
| Target Group | 1 | Health-checked ECS targets |
| ECS Cluster | 1 | Fargate container orchestration |
| ECS Service | 1 | Task lifecycle management |
| ECS Task Definition | 1 | Container specification |
| ECR Repository | 1 | Docker image storage |
| Security Groups | 2 | ALB and ECS network rules |
| WAF Web ACL | 1 | DDoS and attack protection |
| CloudWatch Log Groups | 2 | Application and VPC flow logs |
| IAM Roles | 3 | Task execution, task, flow log |
| S3 Bucket | 1 | ALB access logs |
| Auto Scaling Policies | 2 | CPU and memory scaling |

---

## Data Flow

### Request Flow

```
User Browser
    |
    | HTTP/HTTPS request
    v
AWS WAF (rate limiting, managed rules)
    |
    | Allowed requests
    v
Application Load Balancer (port 80/443)
    |
    | Forward to healthy target (port 3838)
    v
ECS Fargate Task (R Shiny Server)
    |
    | Fetch stock data
    v
Yahoo Finance API (via quantmod/getSymbols)
    |
    | OHLCV price data
    v
R Shiny App processes data reactively
    |
    | Rendered HTML/JavaScript (Plotly charts)
    v
User Browser (interactive dashboard)
```

### Data Processing Pipeline

1. **Data Ingestion**: `quantmod::getSymbols()` fetches OHLCV data from Yahoo Finance for selected tickers from pandemic start date (2020-01-01) to present
2. **Reactive Caching**: Stock data is stored in `reactiveVal()` and re-fetched only when the user changes the category or date range
3. **Computations**: Log returns, rolling volatility, correlations, and normalizations are computed on demand
4. **Forecasting**: ARIMA/ETS/TBATS models fit on historical closing prices, then project forward with confidence intervals
5. **Rendering**: Plotly generates interactive charts; DT renders sortable/searchable tables

---

## Terraform Module Reference

### Module Structure

```
stock-market-dashboard/infra/
  main.tf              # Module composition and locals
  variables.tf         # Input variables with defaults and validation
  outputs.tf           # Output values (ALB DNS, cluster name, etc.)
  versions.tf          # Terraform/provider version constraints, S3 backend
  terraform.tfvars     # Default variable values for dev environment
  modules/
    vpc/               # VPC, subnets, NAT, route tables, flow logs
    security/          # Security groups, WAF
    alb/               # Load balancer, target group, listeners, S3 logs
    ecr/               # Container registry, lifecycle policies
    ecs/               # Cluster, task definition, service, auto-scaling
```

### Module: VPC (`modules/vpc/`)

Creates an isolated network with public and private subnets across 2 availability zones.

| Resource | Description |
|---|---|
| `aws_vpc` | VPC with DNS hostnames and DNS support enabled |
| `aws_internet_gateway` | Internet access for public subnets |
| `aws_subnet.public[2]` | Public subnets for ALB (one per AZ) |
| `aws_subnet.private[2]` | Private subnets for ECS tasks (one per AZ) |
| `aws_nat_gateway` | Outbound internet for private subnets (single AZ) |
| `aws_eip` | Static IP for NAT Gateway |
| `aws_route_table` (x2) | Public (IGW) and private (NAT) routing |
| `aws_flow_log` | VPC flow logs to CloudWatch (90-day retention) |

**Inputs**: `name_prefix`, `vpc_cidr`, `aws_region`
**Outputs**: `vpc_id`, `public_subnet_ids`, `private_subnet_ids`

### Module: Security (`modules/security/`)

Network access control and web application firewall.

| Resource | Description |
|---|---|
| `aws_security_group.alb` | ALB SG: HTTP/HTTPS inbound (multi-CIDR via `for_each`) |
| `aws_security_group.ecs` | ECS SG: inbound only from ALB on container port |
| `aws_wafv2_web_acl` | Optional WAF with rate limiting (2000 req/5min per IP) |

**WAF Rules**:
1. Rate limiting: Block IPs exceeding 2000 requests per 5 minutes
2. AWS Managed Common Rule Set: Protection against common web exploits
3. AWS Managed Known Bad Inputs: Block requests with known-bad patterns

**Inputs**: `name_prefix`, `vpc_id`, `container_port`, `allowed_cidr_blocks`, `enable_waf`
**Outputs**: `alb_security_group_id`, `ecs_security_group_id`, `waf_acl_arn`

### Module: ALB (`modules/alb/`)

Application Load Balancer with health checking and logging.

| Resource | Description |
|---|---|
| `aws_lb` | Internet-facing ALB with invalid header dropping |
| `aws_lb_target_group` | IP-based target group, health check on `/` |
| `aws_lb_listener.http` | Port 80 listener (forward or redirect to HTTPS) |
| `aws_lb_listener.https` | Port 443 listener (optional, requires ACM cert) |
| `aws_s3_bucket` | Encrypted S3 bucket for ALB access logs (90-day expiry) |
| `aws_wafv2_web_acl_association` | WAF association (conditional) |

**Health Check Configuration**:
- Path: `/`
- Interval: 30s
- Timeout: 10s
- Healthy threshold: 3
- Unhealthy threshold: 3

**Inputs**: `name_prefix`, `vpc_id`, `public_subnets`, `security_group`, `container_port`, `certificate_arn`, `waf_acl_arn`
**Outputs**: `alb_dns_name`, `alb_arn`, `target_group_arn`

### Module: ECR (`modules/ecr/`)

Container image registry with security scanning.

| Resource | Description |
|---|---|
| `aws_ecr_repository` | Immutable tags, scan-on-push, AES256 encryption |
| `aws_ecr_lifecycle_policy` | Expire untagged images after 7 days; keep last 10 `v`-prefixed images |

**Inputs**: `name_prefix`
**Outputs**: `repository_url`, `repository_arn`

### Module: ECS (`modules/ecs/`)

Container orchestration with auto-scaling.

| Resource | Description |
|---|---|
| `aws_ecs_cluster` | Fargate cluster with Container Insights |
| `aws_ecs_task_definition` | Fargate task (1024 CPU, 2048 MiB memory default) |
| `aws_ecs_service` | Service with circuit breaker, rolling deploy, ALB integration |
| `aws_appautoscaling_target` | Scaling target (min = desired, max = 3x desired) |
| `aws_appautoscaling_policy.cpu` | Scale at 70% CPU utilization |
| `aws_appautoscaling_policy.memory` | Scale at 80% memory utilization |
| `aws_cloudwatch_log_group` | Container logs (90-day retention) |
| `aws_iam_role` (x2) | Task execution role and task role |

**Task Definition**:
- Network mode: `awsvpc`
- Launch type: Fargate
- Health check: `curl -f http://localhost:3838/`
- Start period: 120 seconds (allows R packages to load)
- Log driver: `awslogs`

**Inputs**: `name_prefix`, `vpc_id`, `private_subnets`, `security_group`, `target_group_arn`, `container_image`, `container_port`, `cpu`, `memory`, `desired_count`, `aws_region`
**Outputs**: `cluster_name`, `service_name`, `log_group_name`

---

## Deployment Pipeline

### Prerequisites

1. **AWS Account** with permissions to create VPC, ECS, ECR, ALB, IAM, WAF, S3, CloudWatch resources
2. **Terraform >= 1.5.0** installed locally or in CI
3. **Docker** installed for building the container image
4. **S3 Bucket** for Terraform state: `stock-market-dashboard-tfstate`
5. **DynamoDB Table** for state locking: `stock-market-dashboard-tflock`

### Step-by-Step Deployment

```bash
# 1. Create Terraform state backend (one-time)
aws s3api create-bucket \
  --bucket stock-market-dashboard-tfstate \
  --region us-east-1

aws dynamodb create-table \
  --table-name stock-market-dashboard-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# 2. Initialize Terraform
cd stock-market-dashboard/infra
terraform init

# 3. Plan infrastructure
terraform plan -out=tfplan

# 4. Apply infrastructure
terraform apply tfplan

# 5. Build and push Docker image
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

cd ..
docker build -t $ECR_URL:v1.0.0 .
docker push $ECR_URL:v1.0.0

# 6. Update ECS service to use new image
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment

# 7. Access the application
echo "Dashboard URL: $(terraform output -raw alb_url)"
```

### Docker Build Details

The Dockerfile uses a multi-stage build:

| Stage | Base Image | Purpose |
|---|---|---|
| `builder` | `rocker/shiny:4.4.0` | Install R packages (shinydashboard, quantmod, plotly, forecast, etc.) |
| `production` | `rocker/shiny:4.4.0` | Copy compiled packages, application code, custom Shiny Server config |

**Shiny Server Configuration**:
- Runs as `shiny` user (non-root)
- Listens on port 3838
- `app_idle_timeout = 0` (keeps app alive)
- `app_init_timeout = 120` (allows time for R package loading)
- Log preservation enabled

---

## Security Architecture

### Network Security

| Layer | Control | Description |
|---|---|---|
| WAF | Rate limiting | Block IPs exceeding 2000 requests per 5 minutes |
| WAF | Managed rules | AWS Common Rule Set + Known Bad Inputs |
| ALB SG | Ingress rules | HTTP/HTTPS only, optionally restricted to specific CIDRs |
| ALB | Header validation | Drop invalid HTTP headers |
| ECS SG | Ingress rules | Only accept traffic from ALB security group on port 3838 |
| VPC | Private subnets | ECS tasks not directly accessible from internet |
| VPC | Flow logs | All network traffic logged to CloudWatch |

### IAM Roles

| Role | Purpose | Permissions |
|---|---|---|
| Task Execution Role | Pull images, write logs | `AmazonECSTaskExecutionRolePolicy` (managed) |
| Task Role | Application runtime | Minimal (no additional policies needed) |
| Flow Log Role | VPC flow log delivery | CloudWatch Logs write permissions |

### Data Security

| Control | Implementation |
|---|---|
| Encryption at rest | S3 (AES256), ECR (AES256) |
| Encryption in transit | Optional HTTPS via ACM certificate |
| Image security | ECR scan-on-push, immutable tags |
| S3 bucket security | Public access blocked, bucket policy scoped to ELB service account |
| Container runtime | Non-root user (`shiny`), no privileged mode (Fargate default) |

---

## Monitoring & Observability

### CloudWatch Log Groups

| Log Group | Source | Retention |
|---|---|---|
| `/ecs/stock-market-dashboard-{env}` | Container stdout/stderr (Shiny Server logs) | 90 days |
| `/aws/vpc/flow-log/stock-market-dashboard-{env}` | VPC network flow logs | 90 days |

### ALB Access Logs

Stored in S3 bucket `stock-market-dashboard-{env}-alb-logs-{account_id}` with 90-day lifecycle expiration.

### Container Insights

ECS Container Insights is enabled on the cluster, providing:
- CPU and memory utilization per task
- Network traffic metrics
- Task count and service metrics

### WAF Metrics

CloudWatch metrics are enabled for all WAF rules:
- `stock-market-dashboard-{env}-rate-limit` - Rate limit hits
- `stock-market-dashboard-{env}-common-rules` - Common rule set matches
- `stock-market-dashboard-{env}-bad-inputs` - Bad input matches
- `stock-market-dashboard-{env}-waf` - Overall WAF metrics

### Health Checks

| Level | Mechanism | Path | Interval |
|---|---|---|---|
| ALB Target Group | HTTP health check | `/` | 30s |
| ECS Task | Docker HEALTHCHECK | `curl -f http://localhost:3838/` | 30s |

---

## Scaling & Performance

### Auto Scaling Configuration

| Parameter | Value |
|---|---|
| Minimum tasks | `desired_count` (default: 2) |
| Maximum tasks | `desired_count * 3` (default: 6) |
| CPU scale-out threshold | 70% average utilization |
| Memory scale-out threshold | 80% average utilization |
| Scale-out cooldown | 60 seconds |
| Scale-in cooldown | 300 seconds |

### Task Resources

| Environment | CPU | Memory | Recommended For |
|---|---|---|---|
| Dev | 1024 (1 vCPU) | 2048 MiB | Testing, low traffic |
| Staging | 1024 (1 vCPU) | 2048 MiB | Pre-production validation |
| Production | 2048 (2 vCPU) | 4096 MiB | Production traffic with many concurrent users |

### Deployment Strategy

- **Rolling deployment**: `deployment_maximum_percent = 200`, `deployment_minimum_healthy_percent = 100`
- **Circuit breaker**: Enabled with automatic rollback on deployment failures
- **Health check grace period**: 120 seconds (allows R Shiny to fully initialize)
- **Deregistration delay**: 60 seconds (allows in-flight requests to complete)

---

## Configuration Reference

### Terraform Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `aws_region` | string | `us-east-1` | AWS deployment region |
| `environment` | string | `dev` | Environment name (dev/staging/prod) |
| `project_name` | string | `stock-market-dashboard` | Project name for resource naming |
| `vpc_cidr` | string | `10.1.0.0/16` | VPC CIDR block |
| `container_port` | number | `3838` | R Shiny container port |
| `desired_count` | number | `2` | Number of ECS tasks |
| `cpu` | number | `1024` | CPU units (1024 = 1 vCPU) |
| `memory` | number | `2048` | Memory in MiB |
| `enable_waf` | bool | `true` | Enable WAF on ALB |
| `allowed_cidr_blocks` | list(string) | `[]` | Restrict ALB access (empty = open) |
| `certificate_arn` | string | `""` | ACM certificate for HTTPS |
| `image_tag` | string | `v1.0.0` | Docker image tag to deploy |

### Terraform Outputs

| Output | Description |
|---|---|
| `alb_dns_name` | ALB DNS name for DNS CNAME records |
| `alb_url` | Full URL to access the application |
| `ecs_cluster_name` | ECS cluster name (for AWS CLI commands) |
| `ecs_service_name` | ECS service name (for deployments) |
| `vpc_id` | VPC ID |
| `cloudwatch_log_group` | CloudWatch log group name |
| `ecr_repository_url` | ECR repository URL for `docker push` |

---

## Disaster Recovery

### State Management

- Terraform state is stored in S3 with encryption and versioning
- DynamoDB table provides state locking to prevent concurrent modifications
- State file path: `infra/terraform.tfstate`

### Recovery Procedures

| Scenario | Recovery |
|---|---|
| Task failure | ECS service automatically replaces unhealthy tasks |
| Deployment failure | Circuit breaker triggers automatic rollback |
| AZ failure | ALB routes traffic to healthy AZ (tasks in 2 AZs) |
| Full region failure | Re-deploy Terraform in alternate region (update `aws_region`) |
| Corrupted state | Restore from S3 bucket versioning |

### Backup Considerations

- **Application data**: No persistent data; all stock data is fetched live from Yahoo Finance
- **Infrastructure**: Fully reproducible via Terraform (no manual configuration)
- **Container images**: Stored in ECR with lifecycle policies retaining last 10 tagged images
