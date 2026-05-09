# User Drop-Off Detection SaaS Platform

An enterprise-grade, industry-standard MLOps application that predicts user churn risk in real-time. Built with a modular Flask API, an advanced Streamlit Glassmorphism Dashboard, and comprehensive CI/CD pipelines.

---

## 🏗️ Clean Folder Structure

```text
user-dropoff-detection/
├── src/
│   ├── api/          # Flask backend API (Blueprints, Swagger, Caching, Middleware)
│   ├── db/           # SQLAlchemy ORM (SQLite / PostgreSQL ready)
│   ├── models/       # ML Pipeline, Feature Engineering, Training Logic
│   └── utils/        # Telemetry, Background Workers, Config Parsers
├── tests/            # Pytest suite for unit and integration testing
├── .streamlit/       # Frontend configuration (Dark Mode, layout overrides)
├── .github/          # CI/CD Workflow configuration (GitHub Actions)
├── docs/             # Documentation and diagrams
├── run_complete_project.ps1 # Local Orchestrator Script
├── streamlit_dashboard.py   # Premium Frontend Dashboard (React/Streamlit)
├── docker-compose.yml       # Container Orchestration
├── Dockerfile               # Production Container Image Spec
└── Postman_Collection.json  # Pre-configured API Routes for testing
```

---

## 🚀 Deployment Guide (Cloud Setup)

### 1. Database (MongoDB Atlas / PostgreSQL)
- **Action**: Provision a database on Render or ElephantSQL.
- **Config**: Set the connection string in the `.env` file or `config.yaml` (`DATABASE_URL=postgresql+psycopg2://user:pass@host/db`).

### 2. Backend API (Render / Railway)
- **Platform**: Deploy the `Dockerfile` to Render as a "Web Service".
- **Environment Variables**:
  - `API_KEY=your_secure_secret`
  - `DATABASE_URL=your_database_url`
- **Scale**: Gunicorn handles concurrent requests efficiently.

### 3. Frontend Dashboard (Streamlit Cloud)
- **Platform**: Connect your GitHub repository to Streamlit Community Cloud.
- **Secret Management**: Set the `DROPOFF_API_URL` secret in Streamlit settings to point to your live Render API URL.

---

## 🤖 Architecture Explanation (Beginner Friendly)

Imagine the system as a **High-End Restaurant**:
1. **The Waiter (Streamlit UI)**: The beautiful dashboard that takes your input (the user's behavioral data).
2. **The Kitchen Manager (Flask API)**: Securely receives the data from the waiter, checks if the request is valid, and prevents spam (Rate Limiting).
3. **The Chef (ML Model)**: The highly trained algorithm (`.pkl` file) that takes the ingredients, calculates the drop-off risk, and outputs a score.
4. **The Receipt (Database)**: Every transaction is logged into PostgreSQL for historical tracking and performance metrics.

---

## 🎓 Viva-Ready Explanation (For Defense)

**"How does your project achieve production readiness?"**

> *"My project transcends a standard notebook experiment by implementing a full MLOps lifecycle. 
> On the frontend, I engineered a highly responsive, premium Streamlit dashboard with advanced Explainable AI (SHAP) and data visualization (Plotly). 
> For the backend, I built a modular Flask API wrapped in a robust rate-limiter, secured by API keys, and documented dynamically via Swagger/Flasgger. 
> To ensure low latency, the API employs In-Memory Request Caching (`Flask-Caching`), preventing redundant ML inference. 
> The architecture is completely containerized via Docker, persistently logs metrics to an abstract SQLAlchemy database (capable of seamlessly swapping between SQLite and PostgreSQL), and is guarded by automated `pytest` suites triggered via GitHub Actions CI/CD. 
> Finally, a background cron-worker asynchronously polls metrics to alert stakeholders via webhooks if anomalous churn spikes occur. This represents a complete, scalable, industry-standard AI SaaS platform."*
