# Monorepo - Application Suite

This repository hosts four independent applications. Each lives in its own directory with dedicated documentation, dependencies, and configuration.

## Applications

| Application | Directory | Description | Tech Stack |
|---|---|---|---|
| [Task Management API](./task-management-api/) | `task-management-api/` | Production-ready RESTful API for task management with JWT auth, RBAC, async notifications, and observability | Python 3.11, FastAPI, PostgreSQL, Redis, RabbitMQ |
| [ETL Pipeline](./etl_pipeline/) | `etl_pipeline/` | PySpark ETL pipeline implementing medallion architecture (Bronze/Silver/Gold) with Delta Lake and Hive catalog | Python 3.10+, PySpark, Delta Lake, Hive, Streamlit |
| [PCE Analytics](./pce_analytics/) | `pce_analytics/` | Data pipeline for FRED macroeconomic data ingestion, inflation analysis, and chart generation | Python 3.x, Pandas, Matplotlib, NumPy |
| [Stock Market Dashboard](./stock-market-dashboard/) | `stock-market-dashboard/` | R Shiny dashboard for time series analysis and forecasting of AI, Capex, Storage, and pandemic-era market-driving stocks | R 4.1+, Shiny, quantmod, forecast, plotly |

---

## Code Metrics Report

### Summary

| Metric | Task Management API | ETL Pipeline | PCE Analytics | Total |
|---|--:|--:|--:|--:|
| Python Files | 62 | 12 | 3 | 77 |
| Total Lines (Python) | 4,041 | 1,572 | 590 | 6,203 |
| Source Lines (non-blank, non-comment) | 3,373 | 1,268 | 455 | 5,096 |
| Source LOC (app only) | 2,437 | 1,388 | 455 | 4,280 |
| Test LOC | 1,397 | 184 | -- | 1,581 |
| Test Count | 117 | 11 | -- | 128 |
| Documentation Files (Markdown) | 8 | 1 | 1 | 10 |

### Code Quality

| Metric | Task Management API | ETL Pipeline | PCE Analytics |
|---|---|---|---|
| **Cyclomatic Complexity (Avg)** | A (2.07) | A (2.27) | A (1.53) |
| **Maintainability Index (Avg)** | A (75.83) | A (68.14) | A (62.81) |
| **Complexity Grade** | A - Low | A - Low | A - Low |
| **Max CC Block** | B (9) - `_check_task_permission` | B (7) - `check_bronze_quality` | A (4) - `main` |

> **Grading Scale** (Cyclomatic Complexity): **A** (1-5) Low risk | **B** (6-10) Moderate | **C** (11-20) High | **D** (21-50) Very High
>
> **Maintainability Index**: **A** (20-100) Good | **B** (10-19) Moderate | **C** (0-9) Poor

### Code Coverage

| Metric | Task Management API | ETL Pipeline | PCE Analytics |
|---|---|---|---|
| **Coverage Target** | 80% (enforced) | -- | -- |
| **Coverage Source** | `app/` (excl. workers, templates, logging, rabbitmq) | -- | -- |
| **CI Test Runner** | pytest + coverage | pytest | -- |

### Test Breakdown (Task Management API)

| Category | Description |
|---|---|
| Unit Tests | Models, schemas, security utilities |
| Integration Tests | Auth, Task, Comment, User, Health API endpoints |
| End-to-End Tests | Full task workflow lifecycle |
| Security Tests | Auth bypass, injection, privilege escalation |
| Load Tests | Locust-based performance testing |

### Infrastructure & Configuration

| Metric | Task Management API | ETL Pipeline | PCE Analytics |
|---|---|---|---|
| **Containerization** | Docker + docker-compose (7 services) | -- | -- |
| **CI/CD** | GitHub Actions (lint, test, build, deploy) | -- | -- |
| **Monitoring** | Prometheus + Grafana | -- | -- |
| **Database Migrations** | Alembic | -- | -- |
| **Pre-commit Hooks** | Black, isort, flake8, trailing whitespace, YAML check | -- | -- |
| **Config Files** | 5 (YAML, TOML, INI) | 1 (YAML) | 0 |

---

## Repository Structure

```
.
├── README.md                    # This file - repository summary
├── .github/workflows/ci.yml    # CI/CD pipeline
├── .pre-commit-config.yaml      # Pre-commit hook configuration
├── .gitignore
│
├── task-management-api/         # Task Management API application
│   ├── README.md
│   ├── app/                     # FastAPI application source
│   │   ├── api/v1/              # Route handlers
│   │   ├── core/                # Config, database, security
│   │   ├── middleware/          # Auth, error handling, request ID
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── repositories/       # Data access layer
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # Business logic layer
│   │   ├── templates/           # Email templates
│   │   └── workers/             # Async notification worker
│   ├── tests/                   # Unit, integration, e2e, security, load tests
│   ├── alembic/                 # Database migrations
│   ├── monitoring/              # Prometheus + Grafana configs
│   ├── docs/                    # Design docs, deployment guide, runbook
│   ├── Dockerfile               # API container image
│   ├── Dockerfile.worker        # Worker container image
│   ├── docker-compose.yml       # Full stack (API, DB, Redis, RabbitMQ, etc.)
│   ├── requirements.txt
│   └── pyproject.toml           # Tool configs (pytest, black, mypy, coverage)
│
├── etl_pipeline/                # NYC Taxi ETL Pipeline
│   ├── README.md
│   ├── src/                     # Spark ETL stages (extract, transform, load)
│   ├── client/                  # Hive client + Streamlit dashboard
│   ├── config/                  # Pipeline configuration
│   ├── tests/                   # Pipeline tests
│   └── requirements.txt
│
├── pce_analytics/               # PCE Analytics
│   ├── README.md
│   ├── TECHNICAL_SUMMARY.md     # Detailed technical documentation
│   ├── __init__.py
│   ├── analyze_pce.py           # Analysis engine + chart generator
│   └── download_data.py         # FRED data acquisition
│
└── stock-market-dashboard/      # Stock Market R Dashboard
    ├── README.md
    └── app.R                    # R Shiny application
```

---

## Getting Started

Each application is self-contained. Navigate to the respective directory and follow its README for setup instructions:

```bash
# Task Management API
cd task-management-api && cat README.md

# ETL Pipeline
cd etl_pipeline && cat README.md

# PCE Analytics
cd pce_analytics && cat README.md

# Stock Market R Dashboard
cd stock-market-dashboard && cat README.md
```
