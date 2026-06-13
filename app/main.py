import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from opentelemetry import metrics, trace

"""FastAPI churn scoring service with OpenTelemetry instrumentation."""
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pydantic import BaseModel, Field

APP_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = APP_ROOT / 'model.pkl'
MODEL_VERSION = os.getenv('MODEL_VERSION', None)

logger = logging.getLogger('app')

app = FastAPI(title='Churn Scoring Service')


def configure_otel() -> None:
    """Configure OpenTelemetry tracing, metrics, and logging providers."""
    service_name = os.getenv('OTEL_SERVICE_NAME', 'churn-scoring-service')
    resource = Resource.create({'service.name': service_name})
    otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
    otlp_insecure = os.getenv('OTEL_EXPORTER_OTLP_INSECURE', 'true').lower() in ('1', 'true', 'yes')
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    trace_provider = TracerProvider(resource=resource)
    span_exporter = ConsoleSpanExporter()
    if otlp_endpoint:
        try:
            span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=otlp_insecure)
        except Exception:
            logger.warning('OTLP trace exporter unavailable; falling back to console exporter')
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    metric_exporter = ConsoleMetricExporter()
    if otlp_endpoint:
        try:
            metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=otlp_insecure)
        except Exception:
            logger.warning('OTLP metric exporter unavailable; falling back to console exporter')
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    log_exporter = ConsoleLogExporter()
    if otlp_endpoint:
        try:
            log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=otlp_insecure)
        except Exception:
            logger.warning('OTLP log exporter unavailable; falling back to console exporter')
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    LoggingInstrumentor().instrument(set_logging_format=True)

    logger.info('OpenTelemetry configured', extra={'service.name': service_name})


configure_otel()

meter = metrics.get_meter('churn-scoring-service', version='1.0.0')
# Core API metrics
request_counter = meter.create_counter('http.server.requests', description='Total incoming HTTP requests')
request_latency_histogram = meter.create_histogram('http.server.duration_ms', unit='ms', description='HTTP request latency in milliseconds')
prediction_counter = meter.create_counter('model.predictions.total', description='Total model predictions')
batch_prediction_counter = meter.create_counter('model.batch_predictions.total', description='Total batch model predictions')
error_counter = meter.create_counter('http.server.errors', description='Total internal server errors')
# Prediction-specific metrics
churn_histogram = meter.create_histogram('model.churn_probability', description='Distribution of churn probability', unit='1')
positive_predictions = meter.create_counter('model.predictions.positive', description='Count of positive churn predictions')
total_predictions = meter.create_counter('model.predictions.total', description='Total number of model predictions')

# business outcome metrics
campaign_interaction_counter = meter.create_counter('business.campaign_interactions.total', description='Total campaign interactions')
campaign_conversion_counter = meter.create_counter('business.campaign_conversion.total', description='Total campaign conversions')
revenue_retained_histogram = meter.create_histogram('business.revenue.retained', unit='USD', description='Revenue retained after intervention')
churn_lift_histogram = meter.create_histogram('business.churn_lift', unit='1', description='Observed churn lift over baseline')


@app.middleware('http')
async def telemetry_middleware(request: Request, call_next):
    """Collect telemetry for every incoming HTTP request."""
    start_time = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        labels = {
            'http.method': request.method,
            'http.path': request.url.path,
            'http.status_code': str(status_code),
        }
        request_counter.add(1, labels)
        request_latency_histogram.record(duration_ms, labels)
        if status_code >= 500:
            error_counter.add(1, labels)
        logger.info(
            'HTTP request completed',
            extra={
                'http.method': request.method,
                'http.path': request.url.path,
                'http.status_code': status_code,
                'duration_ms': round(duration_ms, 2),
            },
        )


class CustomerFeatures(BaseModel):
    customer_id: Optional[str] = None
    total_orders: Optional[int] = Field(0, ge=0)
    total_amount: Optional[float] = Field(0.0, ge=0.0)
    avg_order_value: Optional[float] = Field(0.0, ge=0.0)
    recency_days: Optional[float] = Field(9999.0, ge=0.0)
    support_ticket_count: Optional[int] = Field(0, ge=0)


class BusinessOutcome(BaseModel):
    customer_id: Optional[str] = None
    campaign_id: Optional[str] = None
    interaction_count: Optional[int] = Field(None, ge=0)
    conversion: bool = False
    revenue_retention: Optional[float] = Field(None, ge=0.0)
    churn_lift: Optional[float] = None
    risk_level: Optional[str] = None


class ModelLoadError(Exception):
    pass


def load_model(path: Path):
    """Load a serialized scikit-learn pipeline from disk."""
    if not path.exists():
        raise FileNotFoundError(f'Model not found at {path}')
    return joblib.load(path)


try:
    model = load_model(MODEL_PATH)
    # determine model version if not explicitly provided
    if MODEL_VERSION is None:
        try:
            MODEL_VERSION = str(int(MODEL_PATH.stat().st_mtime))
        except Exception:
            MODEL_VERSION = 'unknown'
    logger.info('Model loaded successfully', extra={'model_path': str(MODEL_PATH), 'model_version': MODEL_VERSION})
except Exception:
    model = None
    logger.warning('Model not loaded at startup', extra={'model_path': str(MODEL_PATH)})


def predict_proba_from_features(m, df: pd.DataFrame) -> np.ndarray:
    """Compute churn probabilities from a trained model, with safe fallbacks."""
    try:
        return m.predict_proba(df)[:, 1]
    except Exception:
        try:
            scores = m.decision_function(df)
            return 1 / (1 + np.exp(-scores))
        except Exception:
            return np.zeros(len(df))


@app.get('/health')
def health():
    """Health check endpoint returns basic service status."""
    return {'status': 'ok'}


@app.post('/predict')
def predict(payload: CustomerFeatures):
    """Run a single customer churn prediction and emit metrics."""
    logger.info('Single prediction request received', extra={'customer_id': payload.customer_id, 'payload': payload.model_dump()})
    if model is None:
        raise HTTPException(status_code=503, detail='Model not loaded. Run `python train_model.py` to create model.pkl')

    df = pd.DataFrame([
        {
            'total_orders': payload.total_orders,
            'total_amount': payload.total_amount,
            'avg_order_value': payload.avg_order_value,
            'recency_days': payload.recency_days,
            'support_ticket_count': payload.support_ticket_count,
        }
    ])
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

    reasons = []
    if payload.recency_days is not None and payload.recency_days > 180:
        reasons.append('Long time since last purchase')
    if payload.total_orders is not None and payload.total_orders <= 1:
        reasons.append('Low purchase frequency')
    if payload.support_ticket_count and payload.support_ticket_count > 2:
        reasons.append('Multiple support tickets')
    if len(reasons) == 0:
        reasons.append('Model indicates elevated churn risk' if predicted_class == 1 else 'No immediate risk signals')

    # record metrics
    prediction_counter.add(1, {'prediction.type': 'single'})
    total_predictions.add(1, {'prediction.type': 'single'})
    churn_histogram.record(prob, {'prediction.type': 'single'})
    if int(prob >= 0.5):
        positive_predictions.add(1, {'prediction.type': 'single'})
    logger.info(
        'Single prediction response',
        extra={
            'customer_id': payload.customer_id,
            'churn_probability': prob,
            'predicted_class': predicted_class,
            'risk_level': risk,
        },
    )
    return {
        'churn_probability': round(prob, 4),
        'predicted_class': predicted_class,
        'risk_level': risk,
        'risk_explanation': '; '.join(reasons),
    }


@app.post('/business_outcomes')
def business_outcomes(payload: BusinessOutcome):
    """Ingest business outcome events and export associated metrics."""
    labels = {
        'campaign_id': payload.campaign_id or 'unknown',
        'risk_level': payload.risk_level or 'unknown',
    }
    if payload.interaction_count is not None:
        campaign_interaction_counter.add(payload.interaction_count, labels)
    if payload.conversion:
        campaign_conversion_counter.add(1, labels)
    if payload.revenue_retention is not None:
        revenue_retained_histogram.record(payload.revenue_retention, labels)
    if payload.churn_lift is not None:
        churn_lift_histogram.record(payload.churn_lift, labels)

    logger.info(
        'Business outcome event',
        extra={
            'customer_id': payload.customer_id,
            'campaign_id': payload.campaign_id,
            'interaction_count': payload.interaction_count,
            'conversion': payload.conversion,
            'revenue_retention': payload.revenue_retention,
            'churn_lift': payload.churn_lift,
            'risk_level': payload.risk_level,
        },
    )
    return {'status': 'ok'}


@app.post('/batch_predict')
def batch_predict(payload: List[CustomerFeatures]):
    """Run batch prediction for multiple customers and record aggregate metrics."""
    ids = [p.customer_id for p in payload]
    logger.info('Batch prediction request received', extra={'batch_size': len(payload), 'customer_ids': ids})
    if model is None:
        raise HTTPException(status_code=503, detail='Model not loaded. Run `python train_model.py` to create model.pkl')

    rows = [
        [p.total_orders, p.total_amount, p.avg_order_value, p.recency_days, p.support_ticket_count]
        for p in payload
    ]
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
        out.append(
            {
                'customer_id': cid,
                'churn_probability': float(round(float(prob), 4)),
                'predicted_class': pred,
                'risk_level': risk,
            }
        )

        # record per-item metrics
        churn_histogram.record(float(prob), {'prediction.type': 'batch'})
        total_predictions.add(1, {'prediction.type': 'batch'})
        if pred == 1:
            positive_predictions.add(1, {'prediction.type': 'batch'})

    batch_prediction_counter.add(len(payload), {'prediction.type': 'batch'})
    logger.info(
        'Batch prediction response',
        extra={'batch_size': len(payload), 'prediction_count': len(out)},
    )
    return {'predictions': out}


FastAPIInstrumentor.instrument_app(app)
