# YouTube DataOps Platform (2026 Edition)

Modern End-to-End Data Engineering Platform analyzing YouTube video metrics and category engagement.

## Architecture & Tech Stack

- **Data Modeling:** Medallion Architecture (Bronze -> Silver -> Gold)
- **Transformation Engine:** Python / DuckDB / PySpark (Vectorized)
- **Orchestration:** Apache Airflow (Code-as-DAG)
- **Monitoring & Observability:** Prometheus & Grafana
- **Infrastructure:** Docker Compose (Reproducible container environment)
- **DataOps Lifecycle:** Local Dev -> Git -> PR / CI/CD -> Release

## Directory Structure

```
DE_Capstone_2026/
├── dags/          # Airflow DAGs for pipeline orchestration
├── data/          # Local data directory (ignored by Git)
│   ├── raw/       # Original USvideos.csv and US_category_id.json
│   └── sample/    # 500-row lightweight dataset for fast development
├── docker/        # Docker Compose, Airflow & Grafana configurations
├── src/           # Python source code (Medallion transformations)
└── tests/         # Unit and integration tests
```
