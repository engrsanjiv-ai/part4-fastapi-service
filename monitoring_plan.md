# Monitoring Plan — Churn Scoring Service

## 1. Data Drift
- Monitor feature distributions for the actual model inputs used by `train_model.py` and `app/main.py`:
  - `total_orders`
  - `total_amount`
  - `avg_order_value`
  - `recency_days`
  - `support_ticket_count`
- Source data files:
  - `data/orders.csv`
  - `data/support_tickets.csv`
  - `data/churn_labels.csv`
- For each feature, compare current production distribution to the training baseline using summary statistics and a population KS statistic.
- Alert if KS > 0.2 or if any feature mean shifts by more than 20% from baseline.

## 2. Prediction Distribution
- Track the distribution of `churn_probability` produced by the model.
- Monitor the daily rate of positive churn predictions (`predicted_class == 1`).
- Alert if the positive prediction rate is more than 2x or less than 0.5x the historical expected rate.

## 3. Business Outcomes
- Track downstream retention and revenue metrics for customers flagged as medium/high risk.
- Key metrics:
  - campaign conversion rate for flagged customers
  - revenue retention lift versus a control group
  - churn reduction over time
- Review weekly and compare with the baseline outcome period.

## 4. API Health
- Monitor the FastAPI service in `app/main.py` via `/health`, `/predict`, and `/batch_predict`.
- Track:
  - request success rate
  - p95 latency
  - 5xx error rate
- Alert if:
  - 5xx > 1%
  - p95 latency > 500ms
  - health endpoint returns non-`ok`

## 5. Retraining / Triggers
- Retrain the model when one or more of the following conditions occur:
  - label distribution shifts by >10% vs training baseline
  - end-to-end performance drops by >0.05 (AUC or PR-AUC)
  - feature drift alerts persist for more than two consecutive weeks
- Note: if `data/churn_labels.csv` is missing, `train_model.py` falls back to a synthetic demo model rather than a production model.

## 6. Logging
- Log request inputs, `churn_probability`, `predicted_class`, risk level, model version, timestamp, and request latency.
- Persist logs to a durable storage system with daily partitioning.
- Ensure logs include enough context for audit and troubleshooting:
  - customer identifier when available
  - payload feature values
  - response values
  - model load status

## Related files
- API implementation: `app/main.py`
- Training script: `train_model.py`
- API tests: `tests/test_api.py`
- Data dictionary: `data/DATA_DICTIONARY.md`

## Responsible-use note
- This churn score is advisory only.
- Require human review before taking automated or irreversible actions, especially for VIP customers.
- Do not use the score as the sole gate for account closure, credit denial, or similar high-impact decisions.

