Part 4 — FastAPI Churn Scoring Service

This repository contains a minimal FastAPI service that loads a saved churn model and exposes prediction endpoints for single and batch scoring. The implementation files include:

- `app/main.py` — FastAPI application with `/health`, `/predict`, and `/batch_predict` endpoints.
- `train_model.py` — training script that attempts to build simple aggregated features from `data/` and save `model.pkl`. If no labels are present, it creates a synthetic fallback model so the API can run.
- `model.pkl` — example saved model (may be present in the repo). You can remove it and re-train if desired.
- `tests/test_api.py` — pytest tests for the endpoints.
- `monitoring_plan.md` — monitoring and responsible-use notes.

Quick start

1. Create a virtual environment and activate it.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. (Optional) Train or re-train the model. The script looks for data files under the `data/` folder and will save `model.pkl` by default.

```powershell
python train_model.py --out model.pkl
```

3. Run the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Project structure

- app/
	- main.py
- data/  (place dataset CSVs here: `orders.csv`, `churn_labels.csv`, etc.)
- tests/
	- test_api.py
- train_model.py
- model.pkl (optional)
- monitoring_plan.md
- requirements.txt

Endpoints

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

Run tests

```powershell
pytest -q
```

Notes and guidance

- If `model.pkl` exists in the repo, the API will load it at startup. To regenerate the model, remove or overwrite `model.pkl` then run `python train_model.py --out model.pkl`.
- The `train_model.py` script uses simple aggregations; for production use replace with a proper feature pipeline and adhere to leakage constraints (only use data available at snapshot date).
- See `monitoring_plan.md` for monitoring, drift detection, logging, and responsible-use notes.

