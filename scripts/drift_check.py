"""KS-based drift check that emits metrics via OTLP.

This script compares a baseline CSV to a recent CSV and pushes simple metrics
to an OTLP collector: `drift.ks_stat` and `drift.mean_shift` with an attribute
`feature=<feature_name>`.

Example:
  python scripts/drift_check.py --baseline data/baseline_features.csv --recent data/recent_features.csv \
    --otlp http://localhost:4318 --wait 6
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
from scipy import stats

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'data' / 'baseline_features.csv'
RECENT = ROOT / 'data' / 'recent_features.csv'
OUT_DIR = ROOT / 'metrics'
OUT_DIR.mkdir(exist_ok=True)


def ks_check(series1, series2):
    try:
        stat, p = stats.ks_2samp(series1.dropna(), series2.dropna())
        return float(stat), float(p)
    except Exception:
        return None, None


def setup_meter(otlp_endpoint: str, insecure: bool = True, interval_ms: int = 2000):
    exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=insecure)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=interval_ms)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', default=str(BASELINE))
    parser.add_argument('--recent', default=str(RECENT))
    parser.add_argument('--out', default=str(OUT_DIR / 'drift_metrics.json'))
    parser.add_argument('--otlp', default=None, help='OTLP endpoint, e.g. http://collector:4318')
    parser.add_argument('--wait', type=int, default=5, help='Seconds to wait for exporter to push metrics')
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    recent_path = Path(args.recent)

    if not baseline_path.exists() or not recent_path.exists():
        print('Missing baseline or recent data; create CSVs at data/baseline_features.csv and data/recent_features.csv')
        return

    b = pd.read_csv(baseline_path)
    r = pd.read_csv(recent_path)

    features = ['total_orders', 'total_amount', 'avg_order_value', 'recency_days', 'support_ticket_count']
    results = {}
    for f in features:
        if f in b.columns and f in r.columns:
            stat, p = ks_check(b[f], r[f])
            results[f] = {
                'ks_stat': stat,
                'p_value': p,
                'baseline_mean': float(b[f].mean()),
                'recent_mean': float(r[f].mean()),
            }

    # Write local JSON copy
    with open(args.out, 'w') as fh:
        json.dump(results, fh, indent=2)

    # If OTLP endpoint provided, push metrics
    if args.otlp:
        provider = setup_meter(args.otlp)
        meter = metrics.get_meter('churn-drift-check', version='1.0.0')
        ks_hist = meter.create_histogram('drift.ks_stat', description='KS statistic for feature drift')
        mean_hist = meter.create_histogram('drift.mean_shift', description='Absolute mean shift for feature')

        for feat, vals in results.items():
            if vals['ks_stat'] is not None:
                ks_hist.record(vals['ks_stat'], {'feature': feat})
                mean_shift = abs(vals['recent_mean'] - vals['baseline_mean'])
                mean_hist.record(mean_shift, {'feature': feat})

        # wait to allow PeriodicExportingMetricReader to push metrics
        print(f'Pushed metrics to {args.otlp}; waiting {args.wait}s for export...')
        time.sleep(args.wait)
        try:
            provider.shutdown()
        except Exception:
            pass

    print('Drift check written to', args.out)


if __name__ == '__main__':
    main()
