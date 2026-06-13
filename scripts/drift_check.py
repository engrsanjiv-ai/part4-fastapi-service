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
RAW_ORDERS = ROOT / 'data' / 'orders.csv'
RAW_SUPPORT = ROOT / 'data' / 'support_tickets.csv'
LABELS_CSV = ROOT / 'data' / 'churn_labels.csv'
OUT_DIR = ROOT / 'metrics'
OUT_DIR.mkdir(exist_ok=True)


def build_feature_frame(customer_ids=None):
    orders = pd.read_csv(RAW_ORDERS, parse_dates=['order_date'])
    support = pd.read_csv(RAW_SUPPORT, parse_dates=['ticket_date'])

    snapshot_date = orders['order_date'].max()
    order_features = (
        orders.groupby('customer_id')
        .agg(
            total_orders=('order_id', 'count'),
            total_amount=('gross_amount', 'sum'),
            avg_order_value=('gross_amount', 'mean'),
            last_order_date=('order_date', 'max'),
        )
    )
    support_counts = support.groupby('customer_id').size().rename('support_ticket_count').to_frame()

    features = order_features.join(support_counts, how='outer').fillna(0)
    features['recency_days'] = (
        snapshot_date - pd.to_datetime(features['last_order_date'], errors='coerce')
    ).dt.days.fillna(9999).astype(int)
    features = features[['total_orders', 'total_amount', 'avg_order_value', 'recency_days', 'support_ticket_count']]

    if customer_ids is not None:
        features = features.loc[features.index.isin(customer_ids)]

    return features.reset_index()


def generate_drift_feature_csvs(baseline_path: Path, recent_path: Path) -> bool:
    if not RAW_ORDERS.exists() or not RAW_SUPPORT.exists() or not LABELS_CSV.exists():
        return False

    labels = pd.read_csv(LABELS_CSV)
    if 'customer_id' not in labels.columns or 'split' not in labels.columns:
        return False

    baseline_ids = labels.loc[labels['split'] == 'train', 'customer_id'].dropna().unique()
    recent_ids = labels.loc[labels['split'].isin(['validation', 'test']), 'customer_id'].dropna().unique()

    if len(baseline_ids) == 0 or len(recent_ids) == 0:
        return False

    baseline_features = build_feature_frame(baseline_ids)
    recent_features = build_feature_frame(recent_ids)

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_features.to_csv(baseline_path, index=False)
    recent_features.to_csv(recent_path, index=False)
    print(f'Generated drift feature files: {baseline_path} and {recent_path}')
    return True


def ks_check(series1, series2):
    """Compute the Kolmogorov-Smirnov statistic and p-value for two distributions."""
    try:
        stat, p = stats.ks_2samp(series1.dropna(), series2.dropna())
        return float(stat), float(p)
    except Exception:
        return None, None


def setup_meter(otlp_endpoint: str, insecure: bool = True, interval_ms: int = 2000):
    """Create and register an OTLP meter provider for drift metrics."""
    exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=insecure)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=interval_ms)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


def main():
    """Run the drift comparison and optionally export metrics via OTLP."""
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
        if generate_drift_feature_csvs(baseline_path, recent_path):
            print('Baseline and recent CSV files were missing and have been generated from raw data.')
        else:
            print('Missing baseline or recent data; create CSVs at data/baseline_features.csv and data/recent_features.csv')
            print('To auto-generate them, ensure data/orders.csv, data/support_tickets.csv, and data/churn_labels.csv exist.')
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
