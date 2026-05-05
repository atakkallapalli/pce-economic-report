# Task Management API

A production-ready RESTful API for managing tasks with assignment, workflow tracking, commenting, search, and notification capabilities.

## Features

- **Task CRUD** - Create, read, update, and soft-delete tasks with title, description, priority, and due dates
- **Task Assignment** - Assign and reassign tasks to users with notifications
- **Status Workflow** - Validated state transitions: TODO -> IN_PROGRESS -> IN_REVIEW -> DONE (with CANCELLED from any state)
- **Full-Text Search** - PostgreSQL-backed search on task titles and descriptions
- **Comments** - Add, list, and delete comments on tasks
- **Email Notifications** - Async notifications via RabbitMQ for assignments and status changes
- **JWT Authentication** - Secure access with access/refresh token pairs
- **Role-Based Access Control** - ADMIN, MANAGER, MEMBER roles with granular permissions
- **Observability** - Prometheus metrics, structured JSON logging, request tracing
- **API Documentation** - Auto-generated OpenAPI/Swagger docs

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Cache | Redis 7 |
| Message Queue | RabbitMQ 3 |
| Auth | JWT (python-jose) + bcrypt |
| Logging | structlog (JSON) |
| Monitoring | Prometheus + Grafana |
| Testing | pytest + httpx |
| Containerization | Docker + docker-compose |
| CI/CD | GitHub Actions |

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Run with Docker Compose

```bash
# Clone the repository
git clone https://github.com/atakkallapalli/task-management-api.git
cd task-management-api

# Start all services
docker-compose up -d

# API is available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
# RabbitMQ management at http://localhost:15672 (guest/guest)
# Grafana at http://localhost:3000 (admin/admin)
# MailHog UI at http://localhost:8025
```

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install aiosqlite  # for testing with SQLite

# Copy environment variables
cp .env.example .env

# Run database migrations (requires PostgreSQL)
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start the notification worker (in a separate terminal)
python -m app.workers.notification_worker
```

### Run Tests

```bash
# Run all tests
pytest tests/ --ignore=tests/load -v

# Run with coverage
pytest tests/ --ignore=tests/load --cov=app --cov-report=term-missing

# Run specific test categories
pytest tests/unit/ -v          # Unit tests
pytest tests/integration/ -v   # Integration tests
pytest tests/e2e/ -v          # End-to-end tests
pytest tests/security/ -v     # Security tests

# Run load tests (requires running server)
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/auth/me` | Get current user |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tasks` | Create task |
| GET | `/api/v1/tasks` | List tasks (filtered) |
| GET | `/api/v1/tasks/search?q=` | Full-text search |
| GET | `/api/v1/tasks/{id}` | Get task by ID |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Soft delete task |
| POST | `/api/v1/tasks/{id}/assign` | Assign task |
| PUT | `/api/v1/tasks/{id}/reassign` | Reassign task |
| PUT | `/api/v1/tasks/{id}/status` | Update status |
| GET | `/api/v1/tasks/{id}/history` | Get status history |

### Comments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tasks/{id}/comments` | Add comment |
| GET | `/api/v1/tasks/{id}/comments` | List comments |
| DELETE | `/api/v1/tasks/{id}/comments/{cid}` | Delete comment |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users` | List users (Manager/Admin) |
| GET | `/api/v1/users/{id}/tasks` | Get user's tasks |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/metrics` | Prometheus metrics |

## Project Structure

```
task-management-api/
├── app/
│   ├── api/v1/          # API route handlers
│   ├── core/            # Config, database, security, logging
│   ├── middleware/       # Auth, request ID, error handling
│   ├── models/          # SQLAlchemy ORM models
│   ├── repositories/    # Database access layer
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business logic layer
│   ├── templates/email/ # Email notification templates
│   ├── workers/         # Async background workers
│   └── main.py          # FastAPI application entry point
├── alembic/             # Database migrations
├── tests/               # Test suite (unit, integration, e2e, load, security)
├── monitoring/          # Prometheus & Grafana configuration
├── docs/                # Requirements & design documentation
├── .github/workflows/   # CI/CD pipeline
├── Dockerfile           # API container image
├── Dockerfile.worker    # Worker container image
└── docker-compose.yml   # Local development orchestration
```

## RBAC Permissions

| Action | ADMIN | MANAGER | MEMBER |
|--------|-------|---------|--------|
| Create task | Yes | Yes | Yes |
| View any task | Yes | Yes | Yes |
| Update any task | Yes | Yes | Own only |
| Delete any task | Yes | Yes | Own only |
| Assign task | Yes | Yes | Own created |
| List users | Yes | Yes | No |
| Delete any comment | Yes | No | Own only |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and linting before committing
4. Commit with meaningful messages
5. Push and create a Pull Request

## License

This project is licensed under the MIT License.
