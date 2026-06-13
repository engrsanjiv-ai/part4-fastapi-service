from pathlib import Path
import argparse
import json
import pandas as pd
import numpy as np
import joblib

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
)


FEATURE_COLUMNS = [
    "total_orders",
    "total_amount",
    "avg_order_value",
    "recency_days",
    "support_ticket_count",
]


def find_label_column(df):
    for col in df.columns:
        if "churn" in col.lower() or "label" in col.lower():
            return col
    return df.columns[-1]


def build_features(base_path: Path):
    """
    Simplified feature builder.
    Reuse your existing build_features() implementation if preferred.
    """
    orders_path = base_path / "orders.csv"
    support_path = base_path / "support_tickets.csv"

    features = pd.DataFrame()

    if orders_path.exists():
        orders = pd.read_csv(orders_path)

        customer_col = next(
            (
                c
                for c in orders.columns
                if "customer" in c.lower() and "id" in c.lower()
            ),
            orders.columns[0],
        )

        amount_col = next(
            (
                c
                for c in orders.columns
                if any(x in c.lower() for x in ["amount", "price", "total"])
            ),
            None,
        )

        grp = orders.groupby(customer_col)

        features = grp.size().rename("total_orders").to_frame()

        if amount_col:
            features["total_amount"] = grp[amount_col].sum()
            features["avg_order_value"] = grp[amount_col].mean()
        else:
            features["total_amount"] = 0
            features["avg_order_value"] = 0

    if support_path.exists():
        support = pd.read_csv(support_path)

        customer_col = next(
            (
                c
                for c in support.columns
                if "customer" in c.lower() and "id" in c.lower()
            ),
            support.columns[0],
        )

        counts = (
            support.groupby(customer_col)
            .size()
            .rename("support_ticket_count")
            .to_frame()
        )

        features = features.join(counts, how="outer")

    for col in FEATURE_COLUMNS:
        if col not in features.columns:
            features[col] = 0

    if "recency_days" not in features.columns:
        features["recency_days"] = 9999

    return features.fillna(0)


def save_metrics(metrics: dict, path: Path):
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)


def train_model(data_dir: Path, output_model: Path):
    labels_path = data_dir / "churn_labels.csv"

    if not labels_path.exists():
        raise FileNotFoundError("churn_labels.csv not found")

    labels = pd.read_csv(labels_path)

    label_col = find_label_column(labels)

    customer_col = next(
        (
            c
            for c in labels.columns
            if "customer" in c.lower() and "id" in c.lower()
        ),
        labels.columns[0],
    )

    features = build_features(data_dir)

    features = (
        features.reset_index()
        .rename(columns={"index": customer_col})
    )

    df = labels.merge(features, on=customer_col, how="left")

    df = df.fillna(0)

    X = df[FEATURE_COLUMNS]
    y = df[label_col]

    if len(df) < 20:
        raise ValueError(
            f"Insufficient training records ({len(df)}). Need at least 20."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "f1_score": f1_score(
            y_test,
            predictions,
            zero_division=0,
        ),
    }

    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(X_test)[:, 1]

        try:
            metrics["roc_auc"] = roc_auc_score(y_test, probs)
        except Exception:
            metrics["roc_auc"] = None

    print("\n=== MODEL METRICS ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    print("\n=== CLASSIFICATION REPORT ===")
    print(classification_report(y_test, predictions))

    joblib.dump(pipeline, output_model)

    metrics_file = output_model.with_suffix(".metrics.json")
    save_metrics(metrics, metrics_file)

    print(f"\nModel saved to: {output_model}")
    print(f"Metrics saved to: {metrics_file}")


def create_fallback_model(output_model: Path):
    print("Creating fallback model...")

    dummy = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="constant", fill_value=0),
            ),
            (
                "clf",
                DummyClassifier(strategy="most_frequent"),
            ),
        ]
    )

    dummy.fit([[0, 0, 0, 0, 0]], [0])

    joblib.dump(dummy, output_model)

    print(f"Fallback model saved to {output_model}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--out",
        default="model.pkl",
        help="Output model path",
    )

    args = parser.parse_args()

    try:
        train_model(
            data_dir=Path("data"),
            output_model=Path(args.out),
        )

    except Exception as exc:
        print(f"Training failed: {exc}")
        create_fallback_model(Path(args.out))


if __name__ == "__main__":
    main()