# User Drop-Off Detection: System Workflow

This document outlines how data flows through the User Drop-Off Detection system, from raw behavioral events down to real-time risk predictions in the dashboard.

## 1. End-to-End MLOps Pipeline Workflow

This workflow represents the offline process of generating data, extracting features, and training the model.

```mermaid
graph TD
    %% Data Generation
    A[Raw User Events] -->|run_pipeline.py| B(Data Preprocessor)
    
    %% Feature Engineering
    B --> C{Feature Engine}
    C -->|Extract| D[Session Duration]
    C -->|Extract| E[Recency & Frequency]
    C -->|Encode| F[User Segment]
    
    %% Training
    D --> G(Model Training Module)
    E --> G
    F --> G
    
    G -->|Logistic Regression / XGBoost| H{Evaluation}
    H -->|Metrics Calculation| I[ROC-AUC, F1-Score]
    H -->|Save Best Model| J[(final_model.pkl)]
```

## 2. Real-Time Inference Workflow (API & Dashboard)

This workflow represents the online process when a user interacts with the Streamlit dashboard or sends a request from the web tracker.

```mermaid
sequenceDiagram
    participant U as User / Tracker.js
    participant S as Streamlit Dashboard
    participant A as Flask API Server
    participant M as Model (final_model.pkl)
    participant D as SQLite Database

    U->>S: Inputs User Behavior (e.g. Session=15m)
    S->>A: POST /predict (JSON Payload)
    
    A->>A: Validate Input Schema
    A->>M: Transform Features & Predict
    M-->>A: Return Probability (e.g. 85%)
    
    A->>D: Log Prediction Result
    A-->>S: Return JSON Response
    
    S->>S: Interpret Risk (Low/Medium/High)
    S-->>U: Display Premium UI (SHAP, Gauges)
```

## 3. Automated Alerting Workflow

This details how the background alerting script interacts with the API to notify the retention team of high-risk users.

```mermaid
graph LR
    A[alerting.py Background Job] -->|Polls every 60s| B(Flask API /predictions)
    B -->|Fetch recent results| A
    A --> C{Is Risk > 75%?}
    C -- Yes --> D[Extract Factors]
    D --> E[Trigger Slack/Email Webhook]
    C -- No --> F[Wait 60s]
    E --> F
```
