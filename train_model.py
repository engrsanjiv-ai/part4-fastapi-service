"""Train a simple churn model and save as a pipeline to disk.

This script is intentionally minimal and robust: it will attempt to build a few
aggregated features from `data/orders.csv` and `data/support_tickets.csv` and
match them to `data/churn_labels.csv`. If those files are not available, the
script trains a tiny synthetic model so the API can run for demonstration.

Usage:
    python train_model.py --out model.pkl
"""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib


def find_label_column(df: pd.DataFrame):
    """Choose the label column by searching for churn or label keywords."""
    for col in df.columns:
        if 'churn' in col.lower() or 'label' in col.lower():
            return col
    # fallback to last column
    return df.columns[-1]


def build_features(base_path: Path):
    """Build training features from orders and support ticket CSVs."""
    orders_path = base_path / 'orders.csv'
    support_path = base_path / 'support_tickets.csv'
    labels_path = base_path / 'churn_labels.csv'

    features = pd.DataFrame()

    if orders_path.exists():
        orders = pd.read_csv(orders_path, parse_dates=True)
        # try to find customer id and order date/amount columns
        cid = None
        for c in orders.columns:
            if 'customer' in c.lower() and 'id' in c.lower():
                cid = c
                break
        if cid is None:
            # try first column
            cid = orders.columns[0]

        # amount heuristics
        amt_col = None
        for c in orders.columns:
            if any(k in c.lower() for k in ['amount', 'total', 'price', 'grand']):
                amt_col = c
                break

        date_col = None
        for c in orders.columns:
            if 'date' in c.lower() or 'created' in c.lower() or 'timestamp' in c.lower():
                date_col = c
                break

        grp = orders.groupby(cid)
        features = grp.size().rename('total_orders').to_frame()
        if amt_col is not None:
            features['total_amount'] = grp[amt_col].sum()
            features['avg_order_value'] = grp[amt_col].mean()
        else:
            features['total_amount'] = 0.0
            features['avg_order_value'] = 0.0

        if date_col is not None:
            orders[date_col] = pd.to_datetime(orders[date_col], errors='coerce')
            last = grp[date_col].max().rename('last_order_date')
            features = features.join(last)
        else:
            features['last_order_date'] = pd.NaT

    if support_path.exists():
        sup = pd.read_csv(support_path)
        sup_cid = None
        for c in sup.columns:
            if 'customer' in c.lower() and 'id' in c.lower():
                sup_cid = c
                break
        if sup_cid is None:
            sup_cid = sup.columns[0]
        sup_count = sup.groupby(sup_cid).size().rename('support_ticket_count').to_frame()
        features = features.join(sup_count, how='outer')

    # default missing columns
    for c in ['total_orders', 'total_amount', 'avg_order_value', 'support_ticket_count']:
        if c not in features.columns:
            features[c] = 0

    # compute recency if churn snapshot exists
    if labels_path.exists():
        labels = pd.read_csv(labels_path, parse_dates=True)
        # find id columns
        label_cid = None
        for c in labels.columns:
            if 'customer' in c.lower() and 'id' in c.lower():
                label_cid = c
                break
        if label_cid is None:
            label_cid = labels.columns[0]

        # detect snapshot date
        snap_col = None
        for c in labels.columns:
            if 'snapshot' in c.lower() or 'date' in c.lower():
                snap_col = c
                break

        if snap_col is not None:
            labels[snap_col] = pd.to_datetime(labels[snap_col], errors='coerce')
            # join snapshot info
            # derive recency: snapshot_date - last_order_date
            features = features.reset_index().rename(columns={'index': label_cid})
            lbl = labels[[label_cid, snap_col]].drop_duplicates(subset=[label_cid])
            features = features.merge(lbl, on=label_cid, how='left')
            if 'last_order_date' in features.columns:
                features['recency_days'] = (features[snap_col] - pd.to_datetime(features['last_order_date'])).dt.days
            else:
                features['recency_days'] = np.nan
            features = features.set_index(label_cid)
        else:
            # fallback recency from last_order_date to max date in orders
            if 'last_order_date' in features.columns and not features['last_order_date'].isna().all():
                maxd = features['last_order_date'].max()
                features['recency_days'] = (maxd - features['last_order_date']).dt.days
            else:
                features['recency_days'] = 9999

    else:
        # no labels file — use last order date if available
        if 'last_order_date' in features.columns and not features['last_order_date'].isna().all():
            maxd = features['last_order_date'].max()
            features['recency_days'] = (maxd - features['last_order_date']).dt.days
        else:
            features['recency_days'] = 9999

    # keep relevant columns
    features = features[['total_orders', 'total_amount', 'avg_order_value', 'recency_days', 'support_ticket_count']]
    features = features.fillna(0)
    return features


def main(out_path: Path):
    """Train a churn model and save it to the provided output path."""
    base = Path('data')
    labels_path = base / 'churn_labels.csv'
    if labels_path.exists():
        labels = pd.read_csv(labels_path)
        label_col = find_label_column(labels)
        # find customer id column
        cid = None
        for c in labels.columns:
            if 'customer' in c.lower() and 'id' in c.lower():
                cid = c
                break
        if cid is None:
            cid = labels.columns[0]

        feats = build_features(base)
        # align on customer id
        feats = feats.reset_index().rename(columns={'index': cid})
        df = labels.merge(feats, on=cid, how='left').fillna(0)
        if df.shape[0] < 10:
            print('Not enough labeled rows, training small synthetic model.')
            raise FileNotFoundError('insufficient labeled data')

        X = df[['total_orders', 'total_amount', 'avg_order_value', 'recency_days', 'support_ticket_count']]
        y = df[label_col]
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value=0)),
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        pipeline.fit(X, y)
        joblib.dump(pipeline, out_path)
        print(f'Model trained and saved to {out_path}')
    else:
        # fallback: train tiny synthetic model
        print('churn_labels.csv not found — training synthetic demo model')
        rng = np.random.RandomState(0)
        X = rng.normal(size=(100, 5))
        y = rng.binomial(1, 0.2, size=100)
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(max_iter=500))
        ])
        pipeline.fit(X, y)
        joblib.dump(pipeline, out_path)
        print(f'Synthetic model saved to {out_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='model.pkl')
    args = parser.parse_args()
    try:
        main(Path(args.out))
    except Exception as e:
        # fallback: save small model so API can run
        import joblib
        from sklearn.dummy import DummyClassifier
        print('Primary train failed:', e)
        print('Saving fallback dummy model...')
        dummy = Pipeline([('imputer', SimpleImputer(strategy='constant', fill_value=0)),
                          ('clf', DummyClassifier(strategy='most_frequent'))])
        dummy.fit([[0, 0, 0, 0, 0]], [0])
        joblib.dump(dummy, Path(args.out))
        print('Fallback model saved.')
