# Fed Rates Corridor - AWS Infrastructure Deployment

Deploy the Fed Rates Corridor Streamlit application on AWS ECS Fargate with Amazon Bedrock integration for LLM-powered analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           AWS Account                                │
│                                                                     │
│  ┌──────────────────── VPC (10.0.0.0/16) ────────────────────────┐ │
│  │                                                                 │ │
│  │  ┌─── Public Subnets ───┐    ┌──── Private Subnets ────────┐  │ │
│  │  │                       │    │                              │  │ │
│  │  │  ┌─────────────────┐  │    │  ┌──────────┐ ┌──────────┐  │  │ │
│  │  │  │   ALB (public)  │──┼────┼─▶│ ECS Task │ │ ECS Task │  │  │ │
│  │  │  └─────────────────┘  │    │  └────┬─────┘ └────┬─────┘  │  │ │
│  │  │  ┌─────────────────┐  │    │       │             │        │  │ │
│  │  │  │  NAT Gateway    │  │    │       ▼             ▼        │  │ │
│  │  │  └─────────────────┘  │    │  ┌──────────────────────┐   │  │ │
│  │  └───────────────────────┘    │  │  Amazon Bedrock      │   │  │ │
│  │                                │  │  (Claude 3 Haiku)    │   │  │ │
│  │                                │  └──────────────────────┘   │  │ │
│  │                                └──────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ WAF v2   │  │CloudWatch│  │ S3 Logs  │  │ VPC Flow Logs    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.5.0 installed
3. **Docker** for building the container image
4. **AWS Account** with permissions for: ECS, EC2, IAM, S3, Bedrock, WAF, CloudWatch

### Required AWS Permissions

The deploying user/role needs:
- `ecs:*`, `ec2:*`, `iam:*` (for VPC, ECS, IAM resources)
- `elasticloadbalancing:*` (for ALB)
- `s3:*` (for state bucket and log bucket)
- `wafv2:*` (for WAF)
- `logs:*` (for CloudWatch)
- `application-autoscaling:*` (for auto-scaling)

### Bedrock Model Access

Ensure the Bedrock model is enabled in your AWS account:
1. Go to AWS Console → Amazon Bedrock → Model access
2. Request access to `Anthropic Claude 3 Haiku`
3. Wait for access to be granted (usually instant)

---

## Deployment Steps

### 1. Create State Backend (one-time)

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket fed-rates-corridor-tfstate \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket fed-rates-corridor-tfstate \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket fed-rates-corridor-tfstate \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name fed-rates-corridor-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Build and Push Docker Image

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name fed-rates-corridor \
  --region us-east-1

# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Build image
cd fed-rates-corridor
docker build -t fed-rates-corridor .

# Tag and push
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
docker tag fed-rates-corridor:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/fed-rates-corridor:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/fed-rates-corridor:latest
```

### 3. Configure Terraform Variables

```bash
cd fed-rates-corridor/infra

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
# REQUIRED: Update container_image with your ECR image URI
vim terraform.tfvars
```

### 4. Deploy Infrastructure

```bash
cd fed-rates-corridor/infra

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply (creates all resources)
terraform apply

# Note the output URL
terraform output alb_url
```

### 5. Verify Deployment

```bash
# Get ALB URL
ALB_URL=$(terraform output -raw alb_url)

# Wait for tasks to be healthy (up to 2 minutes)
echo "Waiting for deployment..."
sleep 120

# Test health endpoint
curl -f ${ALB_URL}/_stcore/health

# Open the app
echo "App available at: ${ALB_URL}"
```

---

## Testing the Application

### Health Check
```bash
curl http://<ALB_DNS>/_stcore/health
# Expected: {"status":"ok"}
```

### Functional Tests
1. Open `http://<ALB_DNS>` in a browser
2. Navigate through all 6 pages:
   - **Dashboard** — Verify rate corridor chart loads with metrics
   - **Customize Chart** — Change series, colors, date range; verify chart updates
   - **Templates** — Select each of the 5 templates; verify rendering
   - **Upload Data** — Upload a CSV with date and value columns
   - **AI Summary** — Generate summaries for all 3 personas (Bedrock integration)
   - **Export Code** — Download Python/R scripts; verify they run standalone

### Load Testing
```bash
# Simple load test with Apache Bench
ab -n 100 -c 10 http://<ALB_DNS>/

# Or with hey (Go-based load tester)
hey -n 200 -c 20 http://<ALB_DNS>/
```

### Bedrock Integration Test
```bash
# Verify Bedrock connectivity from ECS task
aws ecs execute-command \
  --cluster fed-rates-corridor-dev-cluster \
  --task <TASK_ID> \
  --container fed-rates-corridor-dev-app \
  --interactive \
  --command "python -c \"import boto3; c=boto3.client('bedrock-runtime',region_name='us-east-1'); print('Bedrock OK')\""
```

---

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `environment` | `dev` | Environment (dev/staging/prod) |
| `container_image` | — | ECR image URI (required) |
| `desired_count` | `2` | Number of ECS tasks |
| `cpu` | `512` | CPU units (512 = 0.5 vCPU) |
| `memory` | `1024` | Memory in MiB |
| `bedrock_model_id` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model |
| `enable_waf` | `true` | Enable AWS WAF |
| `allowed_cidr_blocks` | `[]` | Restrict ALB access (empty = public) |
| `certificate_arn` | `""` | ACM cert for HTTPS |

---

## Security Features

- **Network isolation**: ECS tasks in private subnets, only ALB in public
- **WAF protection**: Rate limiting (2000 req/5min), AWS Managed Rules (Common + Bad Inputs)
- **IAM least privilege**: Task role scoped to specific Bedrock model only
- **Encryption**: S3 AES-256, TLS 1.3 on ALB (when cert provided)
- **Non-root container**: Application runs as `appuser`
- **VPC Flow Logs**: All traffic logged for forensic analysis
- **Container health checks**: Both Docker HEALTHCHECK and ALB target group health checks
- **Auto-scaling**: CPU-based scaling 2→4 tasks at 70% utilization
- **Deployment safety**: Circuit breaker with automatic rollback on failure

---

## Monitoring

### CloudWatch Dashboards
```bash
# View ECS logs
aws logs tail /ecs/fed-rates-corridor-dev --follow

# View VPC flow logs
aws logs tail /aws/vpc/flow-log/fed-rates-corridor-dev --since 1h
```

### Alarms (recommended additions)
```bash
# Create CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name fed-rates-corridor-high-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Cleanup

```bash
# Destroy all infrastructure
cd fed-rates-corridor/infra
terraform destroy

# Remove ECR repository
aws ecr delete-repository --repository-name fed-rates-corridor --force

# Remove state backend (optional)
aws s3 rb s3://fed-rates-corridor-tfstate --force
aws dynamodb delete-table --table-name fed-rates-corridor-tflock
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tasks not starting | Check CloudWatch logs: `aws logs tail /ecs/fed-rates-corridor-dev` |
| Health check failing | Verify container port 8501 is correct, check security group rules |
| Bedrock errors | Verify model access is enabled in AWS Console → Bedrock → Model access |
| 503 from ALB | Tasks may still be starting (60s startup period), check target group health |
| WAF blocking requests | Check WAF logs, may need to tune rate limit threshold |

---

## Unit Tests

### Application Tests
```bash
cd fed-rates-corridor
pip install pytest pandas matplotlib numpy
python -m pytest tests/ -v
```

### Terraform Validation
```bash
cd fed-rates-corridor/infra
terraform init
terraform validate
terraform fmt -check -recursive
```

### Security Scans
```bash
# Python SAST
pip install bandit
bandit -r fed-rates-corridor/app/

# IaC Security
pip install checkov
checkov -d fed-rates-corridor/infra/ --framework terraform

# Dockerfile Security
checkov -f fed-rates-corridor/Dockerfile --framework dockerfile
```

See [SAST_REPORT.md](./SAST_REPORT.md) for the full security analysis report.
