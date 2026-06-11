from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

APP_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = APP_ROOT / 'model.pkl'

app = FastAPI(title='Churn Scoring Service')


class CustomerFeatures(BaseModel):
    customer_id: Optional[str] = None
    total_orders: Optional[int] = Field(0, ge=0)
    total_amount: Optional[float] = Field(0.0, ge=0.0)
    avg_order_value: Optional[float] = Field(0.0, ge=0.0)
    recency_days: Optional[float] = Field(9999.0, ge=0.0)
    support_ticket_count: Optional[int] = Field(0, ge=0)


def load_model(path: Path):
    if not path.exists():
        raise FileNotFoundError(f'Model not found at {path}')
    return joblib.load(path)


try:
    model = load_model(MODEL_PATH)
except Exception:
    model = None


def predict_proba_from_features(m, df: pd.DataFrame) -> np.ndarray:
    # try predict_proba, else decision_function
    try:
        return m.predict_proba(df)[:, 1]
    except Exception:
        try:
            scores = m.decision_function(df)
            # map to 0-1
            probs = 1 / (1 + np.exp(-scores))
            return probs
        except Exception:
            # fallback: zeros
            return np.zeros(len(df))


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/predict')
def predict(payload: CustomerFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail='Model not loaded. Run `python train_model.py` to create model.pkl')
    df = pd.DataFrame([{
        'total_orders': payload.total_orders,
        'total_amount': payload.total_amount,
        'avg_order_value': payload.avg_order_value,
        'recency_days': payload.recency_days,
        'support_ticket_count': payload.support_ticket_count
    }])
    probs = predict_proba_from_features(model, df)
    prob = float(probs[0])
    threshold = 0.5
    predicted_class = int(prob >= threshold)
    if prob >= 0.7:
        risk = 'high'
    elif prob >= 0.4:
        risk = 'medium'
    else:
        risk = 'low'

    # simple rule-based explanation
    reasons = []
    if payload.recency_days is not None and payload.recency_days > 180:
        reasons.append('Long time since last purchase')
    if payload.total_orders is not None and payload.total_orders <= 1:
        reasons.append('Low purchase frequency')
    if payload.support_ticket_count and payload.support_ticket_count > 2:
        reasons.append('Multiple support tickets')
    if len(reasons) == 0:
        reasons.append('Model indicates elevated churn risk') if predicted_class == 1 else ['No immediate risk signals']

    return {
        'churn_probability': round(prob, 4),
        'predicted_class': predicted_class,
        'risk_level': risk,
        'risk_explanation': '; '.join(reasons)
    }


@app.post('/batch_predict')
def batch_predict(payload: List[CustomerFeatures]):
    if model is None:
        raise HTTPException(status_code=503, detail='Model not loaded. Run `python train_model.py` to create model.pkl')
    rows = []
    ids = []
    for p in payload:
        ids.append(p.customer_id)
        rows.append([
            p.total_orders, p.total_amount, p.avg_order_value, p.recency_days, p.support_ticket_count
        ])
    df = pd.DataFrame(rows, columns=['total_orders', 'total_amount', 'avg_order_value', 'recency_days', 'support_ticket_count'])
    probs = predict_proba_from_features(model, df)
    out = []
    for cid, prob, p in zip(ids, probs, payload):
        pred = int(prob >= 0.5)
        if prob >= 0.7:
            risk = 'high'
        elif prob >= 0.4:
            risk = 'medium'
        else:
            risk = 'low'
        out.append({
            'customer_id': cid,
            'churn_probability': float(round(float(prob), 4)),
            'predicted_class': pred,
            'risk_level': risk
        })
    return {'predictions': out}
