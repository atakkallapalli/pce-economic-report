# Troubleshooting Guide

## API Not Starting

### Symptoms
- Container exits immediately
- Health check fails

### Steps
1. Check logs: `docker-compose logs api`
2. Verify environment variables are set
3. Check database is accessible
4. Verify port 8000 is not in use

### Common Causes
- Missing `DATABASE_URL`
- Database not ready (race condition) - docker-compose `depends_on` with healthcheck should handle this
- Invalid JWT_SECRET_KEY format

## Database Connection Errors

### Symptoms
- 500 errors on all endpoints
- Logs show "connection refused" or "too many connections"

### Steps
1. Check PostgreSQL is running: `docker-compose ps db`
2. Test connection: `docker-compose exec db psql -U postgres -d taskmanager -c "SELECT 1"`
3. Check connection count: `SELECT count(*) FROM pg_stat_activity`
4. Review pool settings

## Notification Worker Not Processing

### Symptoms
- Emails not being sent
- Queue depth growing

### Steps
1. Check worker logs: `docker-compose logs worker`
2. Verify RabbitMQ connection
3. Check SMTP settings
4. Test SMTP manually

## Slow API Responses

### Steps
1. Check Grafana for latency breakdown by endpoint
2. Enable PostgreSQL slow query logging
3. Check Redis connectivity and hit rate
4. Review recent code changes
5. Check container resource limits
