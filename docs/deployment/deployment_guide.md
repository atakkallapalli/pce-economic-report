# Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- PostgreSQL 16 (or use containerized version)
- Redis 7+
- RabbitMQ 3+
- SMTP server (or MailHog for development)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `RABBITMQ_URL` | Yes | - | RabbitMQ connection string |
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT signing (min 32 chars) |
| `SMTP_HOST` | Yes | - | SMTP server hostname |
| `SMTP_PORT` | Yes | - | SMTP server port |
| `SMTP_FROM_EMAIL` | No | noreply@taskmanager.local | Sender email |
| `LOG_LEVEL` | No | INFO | Logging level |
| `LOG_FORMAT` | No | json | Log format (json/console) |

## Docker Deployment

### Build Images

```bash
docker build -t task-api -f Dockerfile .
docker build -t task-worker -f Dockerfile.worker .
```

### Run with Docker Compose

```bash
# Production
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker
```

### Database Migrations

```bash
# Run inside the API container
docker-compose exec api alembic upgrade head
```

## Zero-Downtime Deployment Strategy

### Blue-Green Deployment

1. Deploy new version (green) alongside current (blue)
2. Run health checks against green deployment
3. Switch load balancer traffic from blue to green
4. Monitor error rates for 5 minutes
5. If healthy, drain and remove blue deployment
6. If unhealthy, switch back to blue (rollback)

### Rolling Update (Kubernetes)

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

## Rollback Procedure

1. Identify the issue from monitoring/alerts
2. Switch traffic back to previous version
3. If database migration is involved:
   ```bash
   alembic downgrade -1
   ```
4. Investigate root cause before re-deploying

## Health Checks

- **Liveness**: `GET /health/ready` - Returns 200 if app is running
- **Readiness**: `GET /health` - Returns status of all dependencies (DB, Redis, RabbitMQ)
