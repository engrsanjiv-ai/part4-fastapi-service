# 📌 Part 4 — FastAPI Churn Scoring Service

## D2C Customer Churn Intelligence — Capstone Project

---

# 📖 Project Overview

This project is a **FastAPI-based ML service** that predicts customer churn probability using behavioral features.

It provides:

- Real-time single customer prediction
- Batch prediction support
- ML model trained using scikit-learn pipeline
- Observability using OpenTelemetry
- Data drift detection script
- Dockerized deployment

---

# ⚙️ Setup Instructions

## 1. Clone repository

```powershell
git clone https://github.com/engrsanjiv-ai/part4-fastapi-service.git
cd part4-fastapi-service
```

## 2. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

API will run at:

http://localhost:8000

Swagger UI:

http://localhost:8000/docs

---

# 📡 Endpoint Details

## 1. Health Check

**Endpoint**
```
GET /health
```

**Response**
```json
{
  "status": "ok"
}
```

---

## 2. Predict Single Customer

**Endpoint**
```
POST /predict
```

**Request**
```json
{
  "customer_id": "C123",
  "total_orders": 2,
  "total_amount": 120.0,
  "avg_order_value": 60.0,
  "recency_days": 45,
  "support_ticket_count": 1
}
```

**Response**
```json
{
  "churn_probability": 0.4321,
  "predicted_class": 0,
  "risk_level": "medium",
  "risk_explanation": "No immediate risk signals"
}
```

---

## 3. Batch Predict

**Endpoint**
```
POST /batch_predict
```

**Request**
```json
[
  {
    "customer_id": "C123",
    "total_orders": 2,
    "total_amount": 120.0,
    "avg_order_value": 60.0,
    "recency_days": 45,
    "support_ticket_count": 1
  },
  
  {
    "customer_id": "C456",
    "total_orders": 1,
    "total_amount": 50.0,
    "avg_order_value": 50.0,
    "recency_days": 400,
    "support_ticket_count": 3
  }
]
```

**Response**
```json
{
  "predictions": [
    {
      "customer_id": "C123",
      "churn_probability": 0.4321,
      "predicted_class": 0,
      "risk_level": "medium",
      "risk_explanation": "No immediate risk signals"
    },
    {
      "customer_id": "C456",
      "churn_probability": 0.8912,
      "predicted_class": 1,
      "risk_level": "high",
      "risk_explanation": "High recency and low purchase activity"
    }
  ]
}
```

---

# 🧪 Test Execution Instructions

```bash
pytest -q
```

### Run with coverage

```bash
pytest --cov=app --cov-report=xml
```

---

# 📦 Install Dependencies Command

```bash
pip install -r requirements.txt
```

---

# 🧠 Model / Data Source Notes

## Model Details
- Algorithm: Logistic Regression (sklearn pipeline)
- Saved as: model.pkl

## Input features:
- total_orders  
- total_amount  
- avg_order_value  
- recency_days  
- support_ticket_count  

## Training Logic
- Uses train_model.py
- If data/churn_labels.csv exists → real training
- If missing → synthetic fallback model is created
- If training fails → DummyClassifier fallback is used

## Data Sources
- data/orders.csv → order aggregation features
- data/churn_labels.csv → target labels
- data/support_tickets.csv → support signal features

---


# 📊 Observability with OpenTelemetry

## What is captured:
The service and supporting scripts emit the following metrics (OTLP):

- API health / request metrics:
	- `http.server.requests` — count of incoming requests
	- `http.server.duration_ms` — request latency histogram (derive p95, p50)
	- `http.server.errors` — count of internal/5xx errors

- Model prediction metrics:
	- `model.predictions.total` — total predictions (single + batch)
	- `model.predictions.positive` — count of positive churn predictions
	- `model.churn_probability` — histogram of churn probability scores
	- `model.batch_predictions.total` — batch prediction counts

- Data drift metrics (from `scripts/drift_check.py`):
	- `drift.ks_stat` — KS statistic per feature (attribute: `feature`)
	- `drift.mean_shift` — absolute mean shift per feature (attribute: `feature`)

- Business outcome metrics:
	- `business.campaign_interactions.total` — campaign interaction counts (labels: `campaign_id`, `risk_level`)
	- `business.campaign_conversion.total` — campaign conversions (labels: `campaign_id`, `risk_level`)
	- `business.revenue.retained` — revenue retained after intervention (histogram)
	- `business.churn_lift` — observed churn-lift values (histogram)

Derived signals and alerts (configure in your metrics backend):

- Positive prediction rate = `model.predictions.positive / model.predictions.total`
- p95 latency from `http.server.duration_ms`
- Drift alert when `drift.ks_stat > 0.2` or mean-shift exceeds policy threshold
- Retraining triggers based on label/performance shifts (configure in backend)

## OpenTelemetry (OTEL) Integration

This service includes optional OpenTelemetry instrumentation for traces, metrics, and logs. To enable OTEL exporting, install the extra dependencies and set the OTLP exporter endpoint before starting the service.

Example environment variables (defaults export to console if not set):

```powershell
set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
set OTEL_SERVICE_NAME=churn-scoring-service
set OTEL_EXPORTER_OTLP_INSECURE=true
```

Then run the API as usual:

```powershell
uvicorn app.main:app --reload --port 8000
```

See `app/otel.py` and `app/main.py` for the instrumentation implementation and `monitoring_plan.md` for monitoring guidance.


## How it works:
- OpenTelemetry SDK instruments FastAPI routes
- Traces are exported via OTLP exporter
- Compatible with tools like:
 - Jaeger
 - Prometheus + Grafana
 - Elastic APM

## Benefits:
- Debug production issues faster
- Identify bottlenecks in ML inference pipeline
- Monitor system health in real-time


# 📉 Data Drift 
There is a small KS-based drift check script at `scripts/drift_check.py` that compares `data/baseline_features.csv` to `data/recent_features.csv` and writes results to `metrics/drift_metrics.json`.

Run it locally with:

```powershell
& ".venv/Scripts/python.exe" scripts/drift_check.py --baseline data/baseline_features.csv --recent data/recent_features.csv
```

In production you should run a scheduled job that writes the results to your monitoring backend (OTEL collector or metrics API) and triggers alerts based on thresholds in `monitoring_plan.md`.

# 🐳Docker + CI/CD Ready Structure

This repository includes Docker support and a local OpenTelemetry collector for development.

- `Dockerfile` — container image for the FastAPI app
- `docker-compose.yml` — starts the app and a local `otel-collector` for OTLP ingestion
- `otel-collector-config.yaml` — basic collector config that logs received telemetry

Quick start with Docker Compose:

```powershell
docker compose up --build
```

The app will be reachable at `http://localhost:8000` and the collector will expose OTLP endpoints on `4317` (gRPC) and `4318` (HTTP).


# 📌 Summary

This project demonstrates:

- FastAPI ML deployment
- Batch + real-time inference
- Data preprocessing pipeline
- Model training 
- Observability with OpenTelemetry
- Data drift monitoring
- Docker + CI/CD ready structure