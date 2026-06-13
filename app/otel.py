import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("churn_service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(console_handler)

otel_enabled = False
request_counter = None
request_latency_histogram = None
prediction_counter = None
risk_level_counter = None


def _get_otlp_endpoint(export_type: str) -> str:
    if env := os.environ.get(f"OTEL_EXPORTER_OTLP_{export_type.upper()}_ENDPOINT"):
        return env
    if root := os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return root
    return "http://localhost:4318"


def _build_labels(**kwargs: Any) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


def setup_otel(app: Any, service_name: str = "churn-scoring-service", service_version: str = "1.0.0") -> None:
    global otel_enabled, request_counter, request_latency_histogram, prediction_counter, risk_level_counter

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning("OpenTelemetry dependencies are not installed: %s", exc)
        return

    try:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
            }
        )

        span_exporter = OTLPSpanExporter(endpoint=_get_otlp_endpoint("traces"))
        span_processor = BatchSpanProcessor(span_exporter)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)

        metric_exporter = OTLPMetricExporter(endpoint=_get_otlp_endpoint("metrics"))
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        try:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
            from opentelemetry.sdk._logs import BatchLogRecordProcessor, LoggerProvider, LoggingHandler, set_logger_provider

            log_exporter = OTLPLogExporter(endpoint=_get_otlp_endpoint("logs"))
            log_provider = LoggerProvider(resource=resource)
            log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
            set_logger_provider(log_provider)
            LoggingInstrumentor().instrument(set_logging_format=True)
        except ImportError:
            logger.warning("OpenTelemetry log exporter is not available; logs will still be emitted locally.")

        request_counter = metrics.get_meter(__name__).create_counter(
            "http_server_requests",
            description="Number of HTTP requests received by the churn service",
        )
        request_latency_histogram = metrics.get_meter(__name__).create_histogram(
            "http_server_request_duration_ms",
            description="HTTP request duration in milliseconds",
        )
        prediction_counter = metrics.get_meter(__name__).create_counter(
            "model_prediction_count",
            description="Number of model predictions generated",
        )
        risk_level_counter = metrics.get_meter(__name__).create_counter(
            "prediction_risk_level_count",
            description="Number of predictions by risk level",
        )

        FastAPIInstrumentor().instrument_app(app)

        otel_enabled = True
        logger.info("OpenTelemetry initialized for traces, metrics, and logs")
    except Exception as exc:
        logger.warning("Failed to initialize OpenTelemetry instrumentation: %s", exc)


def record_request(
    route: str,
    method: str,
    status_code: int,
    duration_ms: float,
    customer_id: Optional[str] = None,
) -> None:
    labels = _build_labels(
        http_route=route,
        http_method=method,
        http_status_code=str(status_code),
        customer_id=customer_id,
    )
    if request_counter:
        request_counter.add(1, labels)
    if request_latency_histogram:
        request_latency_histogram.record(duration_ms, labels)

    logger.info(
        "HTTP request %s %s %s %.2fms customer_id=%s",
        method,
        route,
        status_code,
        duration_ms,
        customer_id or "unknown",
    )


def record_prediction(
    route: str,
    predicted_class: int,
    churn_probability: float,
    risk_level: str,
    customer_id: Optional[str] = None,
) -> None:
    labels = _build_labels(
        route=route,
        predicted_class=str(predicted_class),
        risk_level=risk_level,
        customer_id=customer_id,
    )
    if prediction_counter:
        prediction_counter.add(1, labels)
    if risk_level_counter:
        risk_level_counter.add(1, {"risk_level": risk_level})

    logger.info(
        "prediction route=%s customer_id=%s class=%d probability=%.4f risk_level=%s",
        route,
        customer_id or "unknown",
        predicted_class,
        churn_probability,
        risk_level,
    )


def record_batch_prediction(route: str, total_records: int, positive_records: int) -> None:
    labels = _build_labels(route=route)
    if prediction_counter:
        prediction_counter.add(total_records, labels)
    logger.info(
        "batch prediction route=%s total_records=%d positive_records=%d",
        route,
        total_records,
        positive_records,
    )
