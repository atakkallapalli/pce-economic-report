# Operational Runbook

## Common Issues and Resolution

### 1. High Error Rate (>1%)

**Alert:** `HighErrorRate`

**Investigation Steps:**
1. Check API logs: `docker-compose logs -f api | grep ERROR`
2. Check error distribution by endpoint: Query Prometheus for `http_requests_total{status=~"5.."}`
3. Check database connectivity: `docker-compose exec db pg_isready`
4. Check Redis connectivity: `docker-compose exec redis redis-cli ping`
5. Check RabbitMQ: `http://localhost:15672` management UI

**Resolution:**
- If DB connection errors: Restart DB or increase connection pool
- If memory issues: Scale horizontally or increase container memory
- If application errors: Check recent deployments, rollback if needed

### 2. High Latency (p95 > 100ms)

**Alert:** `HighLatency`

**Investigation Steps:**
1. Identify slow endpoints from Grafana dashboard
2. Check database query performance: Enable slow query logging
3. Check Redis cache hit rate
4. Check for lock contention in database

**Resolution:**
- Add database indexes for slow queries
- Increase Redis cache TTL for frequently accessed data
- Scale horizontally if CPU-bound
- Tune database connection pool size

### 3. Database Connection Pool Exhaustion

**Alert:** `DatabaseConnectionPoolExhaustion`

**Investigation Steps:**
1. Check active connections: `SELECT count(*) FROM pg_stat_activity`
2. Check for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start`
3. Check pool configuration: `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`

**Resolution:**
- Kill long-running queries: `SELECT pg_terminate_backend(pid)`
- Increase pool size (max recommended: 50 per instance)
- Add read replicas for read-heavy workloads

### 4. RabbitMQ Queue Backlog

**Investigation Steps:**
1. Check queue depth in management UI: `http://localhost:15672`
2. Check worker logs: `docker-compose logs -f worker`
3. Check SMTP connectivity

**Resolution:**
- Scale notification workers: `docker-compose up -d --scale worker=3`
- If SMTP is down: Investigate email provider
- If persistent: Check for message processing errors

### 5. Authentication Failures Spike

**Investigation Steps:**
1. Check for brute force attempts from specific IPs
2. Verify JWT_SECRET_KEY hasn't changed
3. Check token expiration configuration

**Resolution:**
- Block suspicious IPs at load balancer level
- Ensure JWT_SECRET_KEY is consistent across instances
- Review rate limiting configuration

## On-Call Procedures

### Severity Levels

| Level | Response Time | Examples |
|-------|--------------|---------|
| P1 - Critical | 15 min | Service down, data loss risk |
| P2 - High | 1 hour | Major feature broken, high error rate |
| P3 - Medium | 4 hours | Degraded performance, minor feature issue |
| P4 - Low | Next business day | UI issues, documentation updates |

### Escalation Path

1. On-call engineer investigates
2. If not resolved in 30 min: Escalate to team lead
3. If infrastructure issue: Engage DevOps team
4. If data issue: Engage database team

## Monitoring URLs

| Service | URL |
|---------|-----|
| API Swagger | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| RabbitMQ | http://localhost:15672 |
| MailHog | http://localhost:8025 |
