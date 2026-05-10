<div align="center">

# 🔮 User Drop-Off Detection Platform

### Enterprise-Grade AI SaaS for Real-Time Churn Prediction

[![CI/CD Pipeline](https://github.com/sumanasri813-source/dropoff-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/sumanasri813-source/dropoff-detection/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask API](https://img.shields.io/badge/Flask-API-000000?logo=flask)](https://flask.palletsprojects.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?logo=render)](https://dropoff-detection.onrender.com)

<br>

**🌐 [Live API](https://dropoff-detection.onrender.com) · 📊 [Swagger Docs](https://dropoff-detection.onrender.com/apidocs/) · 📈 [Prometheus Metrics](https://dropoff-detection.onrender.com/metrics) · 🖥️ [Dashboard](https://dropoff-detection-yw9m4fokdymztwrdn5l3dm.streamlit.app)**

</div>

---

## 🎯 What This Project Does

This platform predicts whether a user will **stop using a product** (churn/drop-off) by analyzing behavioral signals like login frequency, session duration, and feature usage. It serves predictions through a **production-grade REST API** with real-time monitoring, JWT authentication, and a premium analytics dashboard.

> **Built as a thesis project, engineered as an enterprise SaaS product.**

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Streamlit Glassmorphism Dashboard                        │  │
│  │  ├─ Real-time KPI Cards & Gauges                          │  │
│  │  ├─ Interactive Predictions with SHAP Explainability      │  │
│  │  ├─ Batch Scoring & CSV Export                            │  │
│  │  └─ AI Insights Assistant & PDF Reports                   │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    SECURITY LAYER                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ CORS     │ │ HSTS/XSS │ │ Rate     │ │ JWT + API Key    │  │
│  │ Origins  │ │ Headers  │ │ Limiter  │ │ Authentication   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    API LAYER (Flask)                              │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  │
│  │/predict│ │/health │ │/metrics│ │/auth/* │ │/apidocs    │  │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    ML ENGINE                                     │
│  ┌───────────────┐ ┌──────────┐ ┌──────────────────────────┐  │
│  │ Trained Model │ │ Feature  │ │ SHAP Explainability      │  │
│  │ (.pkl)        │ │ Pipeline │ │ Engine                   │  │
│  └───────────────┘ └──────────┘ └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    DATA & MONITORING                             │
│  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌────────────────┐  │
│  │ SQLAlch. │ │ Prometheus │ │ Grafana │ │ Alert Rules    │  │
│  │ ORM (DB) │ │ Exporter   │ │ Dashbd  │ │ (5 alerts)     │  │
│  └──────────┘ └────────────┘ └─────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```text
user-dropoff-detection/
├── .github/workflows/       # CI/CD Pipeline (GitHub Actions)
├── .streamlit/              # Streamlit dark theme config
├── data/                    # Training data (synthetic + real)
├── docs/                    # API documentation
├── metrics/                 # Metrics snapshots
├── mlops/                   # MLOps observability artifacts
├── models/                  # Trained ML models (.pkl)
├── monitoring/
│   ├── prometheus.yml       # Prometheus scrape config
│   ├── alert_rules.yml      # 5 production alert rules
│   └── grafana_dashboard.json # Pre-built 11-panel Grafana dashboard
├── results/                 # Evaluation metrics, plots, reports
├── src/
│   ├── api/
│   │   ├── app.py           # Flask API (20+ endpoints)
│   │   ├── prediction_service.py # ML inference engine
│   │   ├── alerting.py      # Real-time alerting system
│   │   └── schemas.py       # Request/Response schemas
│   ├── data/                # Data loading & preprocessing
│   ├── db/                  # SQLAlchemy ORM (SQLite/PostgreSQL)
│   ├── evaluation/          # Model evaluation pipeline
│   ├── features/            # Feature engineering
│   ├── models/              # Model training
│   └── utils/
│       ├── jwt_auth.py      # JWT token authentication
│       ├── cors.py          # Cross-Origin Resource Sharing
│       ├── security_headers.py # HTTP security hardening
│       ├── prometheus_exporter.py # Prometheus metrics
│       ├── resilience.py    # Circuit breaker + rate limiter
│       ├── metrics.py       # Telemetry collector
│       └── health.py        # Health check system
├── tests/                   # Pytest suite (unit + integration + contract)
├── streamlit_dashboard.py   # Premium Analytics Dashboard (3000 lines)
├── Dockerfile               # Production container image
├── docker-compose.yml       # Multi-service orchestration
├── requirements.txt         # Python dependencies
└── README.md                # You are here
```

---

## 🚀 Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| 🔗 **Backend API** | [dropoff-detection.onrender.com](https://dropoff-detection.onrender.com) | ✅ Live |
| 📖 **Swagger Docs** | [/apidocs/](https://dropoff-detection.onrender.com/apidocs/) | ✅ Interactive |
| 📊 **Prometheus Metrics** | [/metrics](https://dropoff-detection.onrender.com/metrics) | ✅ Scraping |
| 🔐 **JWT Auth** | [/auth/login](https://dropoff-detection.onrender.com/auth/login) | ✅ Active |
| 🖥️ **Dashboard** | [Streamlit Cloud](https://dropoff-detection-yw9m4fokdymztwrdn5l3dm.streamlit.app) | ✅ Deployed |
| ⚙️ **CI/CD** | [GitHub Actions](https://github.com/sumanasri813-source/dropoff-detection/actions) | ✅ Passing |

---

## 🔧 Quick Start (Local Development)

```powershell
# 1. Clone the repository
git clone https://github.com/sumanasri813-source/dropoff-detection.git
cd dropoff-detection

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the ML pipeline (train model)
python run_pipeline.py

# 5. Start the Flask API
python -m src.api.app

# 6. Launch the Dashboard (new terminal)
streamlit run streamlit_dashboard.py
```

---

## 🔑 API Authentication

### API Key (Simple)
```bash
curl -H "X-API-Key: dropoff_demo_key_2024" https://dropoff-detection.onrender.com/health
```

### JWT Token (Advanced)
```bash
# Login → Get token
curl -X POST https://dropoff-detection.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Use token
curl -H "Authorization: Bearer <your_token>" \
  https://dropoff-detection.onrender.com/auth/me
```

| User | Password | Role | Access |
|------|----------|------|--------|
| `admin` | `admin123` | Admin | Full access |
| `analyst` | `analyst123` | Analyst | Predict + Monitor |
| `viewer` | `viewer123` | Viewer | Read-only |

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | None | Developer landing page |
| GET | `/health` | None | System health check |
| GET | `/metrics` | None | Prometheus metrics |
| GET | `/apidocs/` | None | Swagger interactive docs |
| POST | `/predict` | API Key | Single user churn prediction |
| POST | `/predict-batch` | API Key | Batch prediction (multiple users) |
| GET | `/model-info` | API Key | Model metadata & performance |
| GET | `/monitor` | API Key | Real-time API telemetry |
| POST | `/auth/login` | None | JWT token authentication |
| POST | `/auth/refresh` | None | Refresh expired token |
| GET | `/auth/me` | JWT | Current user info |
| GET | `/security/status` | API Key | Security config overview |

---

## 🛡️ Security Features

| Feature | Implementation |
|---------|---------------|
| **API Key Auth** | Header-based `X-API-Key` validation |
| **JWT Tokens** | HS256 signed access + refresh tokens |
| **Role-Based Access** | Admin / Analyst / Viewer permission tiers |
| **Rate Limiting** | 100 requests/min per API key (sliding window) |
| **CORS** | Origin whitelist (Streamlit Cloud + localhost) |
| **HSTS** | Strict-Transport-Security (1 year) |
| **XSS Protection** | X-XSS-Protection + Content-Security-Policy |
| **Clickjacking** | X-Frame-Options: SAMEORIGIN |
| **Circuit Breaker** | Fault tolerance for cascading failure prevention |

---

## 📈 Monitoring & Observability

| Component | Purpose |
|-----------|---------|
| **Prometheus Exporter** | 10+ custom metrics (latency, predictions, errors, drift) |
| **Grafana Dashboard** | 11-panel pre-built dashboard (import `monitoring/grafana_dashboard.json`) |
| **Alert Rules** | 5 production alerts (downtime, latency, drift, rate limiting) |
| **Structured Logging** | JSON-formatted logs with request IDs |
| **Background Worker** | Async metrics persistence & alert evaluation |

---

## 🤖 ML Model Details

| Attribute | Value |
|-----------|-------|
| **Algorithm** | Logistic Regression / XGBoost Ensemble |
| **ROC-AUC** | 0.973 |
| **Features** | 9 behavioral signals |
| **Threshold** | 0.5 (configurable) |
| **Risk Levels** | Low (< 0.4) · Medium (0.4-0.7) · High (> 0.7) |
| **Explainability** | SHAP feature importance |

---

## 🧪 Testing

```powershell
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html -v
```

| Test Suite | Coverage |
|------------|----------|
| Unit Tests | API endpoints, validation |
| Contract Tests | Schema validation, CRUD |
| Integration Tests | Gateway smoke, monitoring |

---

## 🎓 Thesis Defense Answer

> **"How does your project achieve production readiness?"**
>
> *"This project implements a complete MLOps lifecycle — from data engineering through deployment and monitoring. The frontend is a premium Streamlit dashboard with Explainable AI (SHAP). The backend is a modular Flask API secured with JWT authentication, API keys, rate limiting, CORS, and HTTP security headers. The ML model serves real-time predictions via a RESTful interface with Swagger documentation. The system exports Prometheus metrics, includes a pre-built Grafana dashboard with 5 automated alert rules, and runs automated tests through GitHub Actions CI/CD. It's deployed on Render (backend) and Streamlit Cloud (frontend), representing a complete, scalable, industry-standard AI SaaS platform."*

---

<div align="center">

**Built with ❤️ by Sumana Sri**

*Machine Learning · MLOps · Full-Stack Development*

</div>
