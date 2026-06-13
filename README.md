# Part 4 — FastAPI Churn Scoring Service

## D2C Customer Churn Intelligence — Capstone Project

### Overview
This repository contains FastAPI service that loads a saved churn model and exposes prediction endpoints for single and batch scoring. The implementation files include:

- `app/main.py` — FastAPI application with `/health`, `/predict`, and `/batch_predict` endpoints.
- `train_model.py` — training script that attempts to build simple aggregated features from `data/` and save `model.pkl`. If no labels are present, it creates a synthetic fallback model so the API can run.
- `model.pkl` —  saved model 
- `tests/test_api.py` — pytest tests for the endpoints.
- `monitoring_plan.md` — monitoring and responsible-use notes.
---

## Setup

1. Clone the repository and change into the project folder.

```powershell
git clone https://github.com/engrsanjiv-ai/part4-fastapi-service.git
cd part4-fastapi-service
```

2. Use Python 3.x (preferred) and create a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies.

```powershell
pip install -r requirements.txt
```

## Quick start

1. (Optional) Train or re-train the model. The script looks for data files under the `data/` folder and will save `model.pkl` by default.

```powershell
python train_model.py --out model.pkl
```

3. Run the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

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

## Docker

This repository includes Docker support and a local OpenTelemetry collector for development.

- `Dockerfile` — container image for the FastAPI app
- `docker-compose.yml` — starts the app and a local `otel-collector` for OTLP ingestion
- `otel-collector-config.yaml` — basic collector config that logs received telemetry

Quick start with Docker Compose:

```powershell
docker compose up --build
```

The app will be reachable at `http://localhost:8000` and the collector will expose OTLP endpoints on `4317` (gRPC) and `4318` (HTTP).

## Drift check script

There is a small KS-based drift check script at `scripts/drift_check.py` that compares `data/baseline_features.csv` to `data/recent_features.csv` and writes results to `metrics/drift_metrics.json`.

Run it locally with:

```powershell
& ".venv/Scripts/python.exe" scripts/drift_check.py --baseline data/baseline_features.csv --recent data/recent_features.csv
```

In production you should run a scheduled job that writes the results to your monitoring backend (OTEL collector or metrics API) and triggers alerts based on thresholds in `monitoring_plan.md`.

## Project structure

- app/
	- main.py
- data/  (place dataset CSVs here: `orders.csv`, `churn_labels.csv`, etc.)
- tests/
	- test_api.py
- train_model.py
- model.pkl (optional)
- monitoring_plan.md
- requirements.txt

## Endpoints

- `GET /health`
	- Response: `{ "status": "ok" }`

- `POST /predict`
	- Input: single customer features JSON. Example:

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

	- Example Response:

```json
{
	"churn_probability": 0.4321,
	"predicted_class": 0,
	"risk_level": "medium",
	"risk_explanation": "No immediate risk signals"
}
```

- `POST /batch_predict`
	- Input: list of customer feature payloads (same schema as `/predict`).
	- Response: `{ "predictions": [ { "customer_id": ..., "churn_probability": ..., "predicted_class": ..., "risk_level": ... }, ... ] }`

## Run tests

```powershell

```

Notes and guidance

- If `model.pkl` exists in the repo, the API will load it at startup. To regenerate the model, remove or overwrite `model.pkl` then run `python train_model.py --out model.pkl`.
- The `train_model.py` script uses simple aggregations; for production use replace with a proper feature pipeline and adhere to leakage constraints (only use data available at snapshot date).
- See `monitoring_plan.md` for monitoring, drift detection, logging, and responsible-use notes.

