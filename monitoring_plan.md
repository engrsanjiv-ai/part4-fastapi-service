Monitoring Plan — Churn Scoring Service

1. Data Drift
- Monitor feature distribution (mean, std, percentiles) for key features: `recency_days`, `total_orders`, `total_amount`, `support_ticket_count` weekly.
- Alert if population KS statistic > 0.2 vs training baseline for any feature.

2. Prediction Distribution
- Track churn_probability histogram and rate of predicted positives daily. Alert if predicted positive rate deviates > 2x expected.

3. Business Outcomes
- Track retention campaign lift: conversion and revenue lift for customers flagged as high-risk. Evaluate weekly.

4. API Health
- Track request success rate, latency (p95), and error rates. Alert on >1% 5xx or p95 latency > 500ms.

5. Retraining / Triggers
- Retrain when: (a) label distribution shifts by >10% vs baseline, (b) performance (AUC/PR-AUC) drops by >0.05, or (c) feature drift alerts repeatedly over 2 weeks.

6. Logging
- Store inputs, model probabilities, model version, timestamp, request id, and request latency for all requests to enable audits and error analysis.
- Persist logs to a durable store (S3, blob storage, or a logging DB) with partitioning by date.

Related files
- API implementation: `app/main.py`
- Training script: `train_model.py`
- Tests: `tests/test_api.py`

Responsible-use note
- Predictions are advisory. Require human review for VIP customers and any automated discounting. Do not use churn score as the sole gate for irreversible actions (e.g., account termination).

