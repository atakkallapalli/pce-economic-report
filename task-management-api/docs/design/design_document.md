# Task Management API - Design Document

**Version:** 1.0
**Date:** April 2026
**Author:** Devin AI

---

## 1. System Architecture

### Architecture Diagram

```
                          ┌──────────────────────────────────────────┐
                          │              Client Layer                │
                          │  (Web App, Mobile App, CLI, Integrations)│
                          └──────────────────┬───────────────────────┘
                                             │ HTTPS
                                             ▼
                          ┌──────────────────────────────────────────┐
                          │          Load Balancer / Reverse Proxy   │
                          │              (Nginx / ALB)               │
                          └──────────────────┬───────────────────────┘
                                             │
                                             ▼
                ┌────────────────────────────────────────────────────────┐
                │                  FastAPI Application                   │
                │  ┌─────────┐  ┌──────────┐  ┌────────────────────┐   │
                │  │  Auth   │  │   Task   │  │    Comment         │   │
                │  │ Router  │  │  Router  │  │    Router          │   │
                │  └────┬────┘  └────┬─────┘  └────────┬───────────┘   │
                │       │            │                  │               │
                │  ┌────▼────────────▼──────────────────▼───────────┐   │
                │  │              Service Layer                     │   │
                │  │  AuthService | TaskService | CommentService    │   │
                │  │  NotificationService | SearchService           │   │
                │  └────┬────────────┬──────────────────┬───────────┘   │
                │       │            │                  │               │
                │  ┌────▼────────────▼──────────────────▼───────────┐   │
                │  │            Repository Layer (DAL)              │   │
                │  │  UserRepo | TaskRepo | CommentRepo | HistoryRepo│  │
                │  └───────────────────┬────────────────────────────┘   │
                │                      │                                │
                │  ┌───────────────────┼────────────────────────────┐   │
                │  │         Middleware & Cross-Cutting              │   │
                │  │  JWT Auth | RBAC | Rate Limit | Request ID     │   │
                │  │  Structured Logging | Error Handler | Metrics  │   │
                │  └────────────────────────────────────────────────┘   │
                └───────┬──────────────┬─────────────────┬──────────────┘
                        │              │                 │
              ┌─────────▼──┐    ┌──────▼──────┐   ┌─────▼───────┐
              │ PostgreSQL │    │    Redis    │   │  RabbitMQ   │
              │            │    │             │   │             │
              │ - Users    │    │ - Session   │   │ - Email     │
              │ - Tasks    │    │   Cache     │   │   Queue     │
              │ - Comments │    │ - Rate      │   │             │
              │ - History  │    │   Limits    │   └──────┬──────┘
              └────────────┘    │ - Task      │          │
                                │   Cache     │          ▼
                                └─────────────┘   ┌─────────────┐
                                                  │ Notification│
                                                  │   Worker    │
                                                  │ (Consumer)  │
                                                  └──────┬──────┘
                                                         │
                                                         ▼
                                                  ┌─────────────┐
                                                  │ SMTP Server │
                                                  └─────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **FastAPI Application** | HTTP request handling, routing, validation, serialization |
| **Auth Router** | Registration, login, token refresh, user profile |
| **Task Router** | Task CRUD, assignment, status management |
| **Comment Router** | Comment CRUD on tasks |
| **Service Layer** | Business logic, validation rules, orchestration |
| **Repository Layer** | Database queries, data access abstraction |
| **Middleware** | Cross-cutting concerns: auth, logging, metrics, rate limiting |
| **PostgreSQL** | Primary data store for all entities |
| **Redis** | Caching layer, rate limiting counters, session storage |
| **RabbitMQ** | Async message queue for email notifications |
| **Notification Worker** | Consumes queue messages and sends emails via SMTP |

### Data Flow: Create & Assign Task

```
1. Client -> POST /api/v1/tasks (JWT in header)
2. JWT Middleware validates token, extracts user
3. Rate Limiter checks request count
4. Request ID middleware generates trace ID
5. TaskRouter receives request
6. TaskService validates input, creates task via TaskRepo
7. PostgreSQL stores task record
8. Response returned to client (201 Created)

9. Client -> POST /api/v1/tasks/{id}/assign (assignee_id in body)
10. TaskService validates assignment permissions
11. TaskRepo updates assignee_id
12. TaskService publishes "task_assigned" event to RabbitMQ
13. NotificationWorker consumes event, renders email template
14. Email sent to assignee via SMTP
```

---

## 2. Database Schema

### Entity Relationship Diagram

```
┌──────────────────────┐       ┌──────────────────────────────────┐
│        users         │       │             tasks                │
├──────────────────────┤       ├──────────────────────────────────┤
│ id          UUID  PK │◄──┐   │ id              UUID  PK        │
│ email       VARCHAR  │   │   │ title           VARCHAR(200)    │
│ password_hash VARCHAR│   │   │ description     TEXT             │
│ full_name   VARCHAR  │   ├───│ creator_id      UUID  FK→users  │
│ role        ENUM     │   ├───│ assignee_id     UUID  FK→users  │
│ is_active   BOOLEAN  │   │   │ status          ENUM            │
│ created_at  TIMESTAMP│   │   │ priority        ENUM            │
│ updated_at  TIMESTAMP│   │   │ due_date        TIMESTAMP       │
└──────────────────────┘   │   │ created_at      TIMESTAMP       │
                           │   │ updated_at      TIMESTAMP       │
                           │   │ deleted_at      TIMESTAMP       │
                           │   └─────────┬────────────────────────┘
                           │             │
                           │             │ task_id FK
                           │             ▼
                           │   ┌──────────────────────────────────┐
                           │   │         task_history             │
                           │   ├──────────────────────────────────┤
                           │   │ id              UUID  PK        │
                           │   │ task_id         UUID  FK→tasks  │
                           ├───│ changed_by      UUID  FK→users  │
                           │   │ old_status      ENUM            │
                           │   │ new_status      ENUM            │
                           │   │ change_type     VARCHAR         │
                           │   │ details         JSONB           │
                           │   │ changed_at      TIMESTAMP       │
                           │   └──────────────────────────────────┘
                           │
                           │   ┌──────────────────────────────────┐
                           │   │          comments               │
                           │   ├──────────────────────────────────┤
                           │   │ id              UUID  PK        │
                           │   │ task_id         UUID  FK→tasks  │
                           ├───│ user_id         UUID  FK→users  │
                           │   │ content         TEXT             │
                               │ created_at      TIMESTAMP       │
                               │ updated_at      TIMESTAMP       │
                               │ deleted_at      TIMESTAMP       │
                               └──────────────────────────────────┘
```

### Table Definitions

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'MEMBER',  -- ADMIN, MANAGER, MEMBER
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### tasks
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    creator_id UUID NOT NULL REFERENCES users(id),
    assignee_id UUID REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'TODO',  -- TODO, IN_PROGRESS, IN_REVIEW, DONE, CANCELLED
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',  -- LOW, MEDIUM, HIGH, URGENT
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

#### task_history
```sql
CREATE TABLE task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    changed_by UUID NOT NULL REFERENCES users(id),
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    change_type VARCHAR(50) NOT NULL,  -- STATUS_CHANGE, ASSIGNMENT, REASSIGNMENT, CREATED, UPDATED
    details JSONB,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### comments
```sql
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

### Indexes

```sql
-- users
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- tasks
CREATE INDEX idx_tasks_status ON tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_priority ON tasks(priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_creator ON tasks(creator_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_due_date ON tasks(due_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_search ON tasks USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- task_history
CREATE INDEX idx_history_task ON task_history(task_id, changed_at DESC);

-- comments
CREATE INDEX idx_comments_task ON comments(task_id, created_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_comments_user ON comments(user_id) WHERE deleted_at IS NULL;
```

### Migration Strategy
- Use Alembic for schema migrations
- Each migration is reversible (upgrade/downgrade)
- Migrations run automatically on deployment
- Data migrations are separate from schema migrations

---

## 3. API Design

### Base URL
`/api/v1`

### Authentication Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login, get JWT tokens | No |
| POST | `/auth/refresh` | Refresh access token | Yes (refresh token) |
| GET | `/auth/me` | Get current user profile | Yes |

### Task Endpoints

| Method | Path | Description | Auth | Roles |
|--------|------|-------------|------|-------|
| POST | `/tasks` | Create task | Yes | Any |
| GET | `/tasks` | List tasks (filtered) | Yes | Any |
| GET | `/tasks/search` | Full-text search | Yes | Any |
| GET | `/tasks/{id}` | Get task by ID | Yes | Any |
| PUT | `/tasks/{id}` | Update task | Yes | Creator/Assignee/Manager/Admin |
| DELETE | `/tasks/{id}` | Soft delete task | Yes | Creator/Manager/Admin |
| POST | `/tasks/{id}/assign` | Assign task | Yes | Creator/Manager/Admin |
| PUT | `/tasks/{id}/reassign` | Reassign task | Yes | Creator/Manager/Admin |
| PUT | `/tasks/{id}/status` | Update status | Yes | Creator/Assignee/Manager/Admin |
| GET | `/tasks/{id}/history` | Get status history | Yes | Any |

### Comment Endpoints

| Method | Path | Description | Auth | Roles |
|--------|------|-------------|------|-------|
| POST | `/tasks/{id}/comments` | Add comment | Yes | Any |
| GET | `/tasks/{id}/comments` | List comments | Yes | Any |
| DELETE | `/tasks/{id}/comments/{comment_id}` | Delete comment | Yes | Author/Admin |

### User Endpoints

| Method | Path | Description | Auth | Roles |
|--------|------|-------------|------|-------|
| GET | `/users/{id}/tasks` | Get tasks by assignee | Yes | Self/Manager/Admin |
| GET | `/users` | List users | Yes | Manager/Admin |

### Health Endpoint

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/health/ready` | Readiness check | No |

### Request/Response Schemas

#### Task Create Request
```json
{
  "title": "string (1-200 chars, required)",
  "description": "string (optional)",
  "priority": "LOW|MEDIUM|HIGH|URGENT (default: MEDIUM)",
  "due_date": "ISO 8601 datetime (optional)",
  "assignee_id": "UUID (optional)"
}
```

#### Task Response
```json
{
  "id": "UUID",
  "title": "string",
  "description": "string|null",
  "status": "TODO|IN_PROGRESS|IN_REVIEW|DONE|CANCELLED",
  "priority": "LOW|MEDIUM|HIGH|URGENT",
  "creator": { "id": "UUID", "full_name": "string", "email": "string" },
  "assignee": { "id": "UUID", "full_name": "string", "email": "string" } | null,
  "due_date": "ISO 8601|null",
  "is_overdue": "boolean",
  "comment_count": "integer",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

#### Paginated Response
```json
{
  "items": [],
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "pages": "integer"
}
```

#### Error Response
```json
{
  "detail": "string",
  "error_code": "string",
  "timestamp": "ISO 8601",
  "request_id": "string"
}
```

---

## 4. Security Design

### Authentication Flow

```
1. User registers: POST /auth/register
   -> Password hashed with bcrypt (12 rounds)
   -> User stored in DB
   -> JWT access token (30min) + refresh token (7 days) returned

2. User logs in: POST /auth/login
   -> Verify email + password
   -> Return new JWT tokens

3. Authenticated requests:
   -> Authorization: Bearer <access_token>
   -> Middleware decodes JWT, validates expiry, extracts user_id and role
   -> User object attached to request state

4. Token refresh: POST /auth/refresh
   -> Validate refresh token
   -> Return new access token
```

### RBAC Permission Matrix

| Resource / Action | ADMIN | MANAGER | MEMBER |
|-------------------|-------|---------|--------|
| Create task | Y | Y | Y |
| View any task | Y | Y | Y |
| Update any task | Y | Y | Own only |
| Delete any task | Y | Y | Own only |
| Assign task | Y | Y | Own created |
| Change status | Y | Y | Assigned/Created |
| Add comment | Y | Y | Y |
| Delete any comment | Y | N | Own only |
| List users | Y | Y | N |
| Manage user roles | Y | N | N |

### Input Validation Strategy
- All inputs validated via Pydantic models with strict types
- String lengths enforced at model level
- SQL injection prevented by parameterized queries (SQLAlchemy ORM)
- XSS prevented by not rendering user input as HTML (JSON API)
- Request body size limited to 1MB
- File uploads not supported (no attack surface)

### Rate Limiting Strategy
- Global: 1000 requests/minute per IP
- Per-user: 100 requests/minute
- Auth endpoints: 10 requests/minute per IP (login/register)
- Implemented via Redis-backed sliding window counter

---

## 5. Observability Design

### Metrics (Prometheus)
| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency by endpoint |
| `db_query_duration_seconds` | Histogram | Database query latency |
| `tasks_created_total` | Counter | Tasks created |
| `tasks_completed_total` | Counter | Tasks moved to DONE |
| `notifications_sent_total` | Counter | Notifications sent |
| `notifications_failed_total` | Counter | Failed notifications |
| `active_db_connections` | Gauge | Database connection pool usage |
| `redis_hit_ratio` | Gauge | Cache hit ratio |
| `rabbitmq_queue_depth` | Gauge | Notification queue depth |

### Structured Logging Format
```json
{
  "timestamp": "2026-04-27T12:00:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "user_id": "uuid",
  "method": "POST",
  "path": "/api/v1/tasks",
  "status_code": 201,
  "duration_ms": 45,
  "message": "Task created"
}
```

### Log Levels
| Level | Usage |
|-------|-------|
| DEBUG | Detailed flow tracing (disabled in production) |
| INFO | Successful operations, state changes |
| WARNING | Recoverable issues, deprecated usage |
| ERROR | Failed operations requiring attention |
| CRITICAL | System failures requiring immediate action |

### Distributed Tracing
- Request ID generated at middleware level (UUID v4)
- Propagated via `X-Request-ID` header
- Included in all log entries and error responses
- Passed to RabbitMQ messages for end-to-end tracing

### Alerting Rules
| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | error_rate > 1% for 5 minutes | Critical |
| High Latency | p95 > 100ms for 5 minutes | Warning |
| DB Pool Exhaustion | active_connections > 80% pool | Critical |
| Queue Backlog | queue_depth > 1000 for 10 minutes | Warning |
| Auth Failures | failed_logins > 50/min | Warning |
