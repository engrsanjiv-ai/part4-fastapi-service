# D2C Customer Churn Capstone — Data Dictionary

**Snapshot date:** `2025-09-30`
**Target window:** 60 days after the snapshot date (i.e., `2025-10-01` to `2025-11-29`)
**Primary key across all files:** `customer_id`

---

## ⚠️ Leakage Rule (Critical)

Use **only** data available on or before `2025-09-30` as model features.
`orders.csv` contains rows dated after the snapshot; those rows exist **only** to explain how churn labels were created. Do **not** include them as features.

---

## File Overview

| File | Rows | Description |
|---|---|---|
| `customers.csv` | 2,400 | Static customer profile and acquisition attributes |
| `orders.csv` | ~10,009 | Full order-level transaction history (pre- and post-snapshot) |
| `support_tickets.csv` | ~1,921 | Customer-service interactions |
| `web_events_snapshot.csv` | 2,400 | 30-day web/app activity as of snapshot date |
| `churn_labels.csv` | 2,400 | Target variable and train/val/test split assignment |
| `rfm_modeling_snapshot.csv` | 2,400 | Pre-built, feature-engineered modeling table |
| `intervention_history.csv` | 2,400 | Most recent campaign/intervention per customer |

---

## 1. `customers.csv`

One row per customer. All columns reflect the state at or before the snapshot date.

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `customer_id` | string | No | Unique customer identifier | `CUST00001` – `CUST02400` |
| `signup_date` | date (`YYYY-MM-DD`) | No | Date the customer created their account | `2024-01-01` – `2025-09-15` |
| `city_tier` | string (categorical) | No | Classification of the customer's city by market size | `Tier 1`, `Tier 2`, `Tier 3` |
| `age_group` | string (categorical) | No | Age bracket of the customer | `18-24`, `25-34`, `35-44`, `45+` |
| `acquisition_channel` | string (categorical) | No | Marketing channel through which the customer was acquired | `Google Search`, `Instagram`, `Influencer`, `Referral`, `Marketplace`, `Organic` |
| `loyalty_tier` | string (categorical) | **Yes** (~1,386 nulls) | Loyalty programme tier assigned at signup or upgrade; null means not enrolled | `Silver`, `Gold`, `Platinum` |
| `preferred_category` | string (categorical) | No | Product category the customer selected as a preference at signup | `Skin Care`, `Hair Care`, `Makeup`, `Fragrance`, `Wellness`, `Baby Care` |
| `skin_type` | string (categorical) | **Yes** (~401 nulls) | Self-reported skin type; null means not provided | `Normal`, `Dry`, `Oily`, `Combination`, `Sensitive` |
| `marketing_consent` | string (categorical) | No | Whether the customer has opted in to marketing communications | `Yes`, `No` |

---

## 2. `orders.csv`

One row per order line. Contains both **pre-snapshot** orders (usable as features) and **post-snapshot** orders (for label construction only — do **not** use as features).

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `order_id` | string | No | Unique order identifier; records ending in `_DUP` are intentional duplicate-like entries for data-quality tasks | `ORD000001` – `ORD009997`; some `*_DUP` suffixes |
| `customer_id` | string | No | Links to `customers.csv` | `CUST00001` – `CUST02400` |
| `order_date` | date (`YYYY-MM-DD`) | No | Date the order was placed; dates after `2025-09-30` are post-snapshot and **must not be used as features** | `2024-01-09` – `2025-11-29` |
| `category` | string (categorical) | No | Product category ordered | `Skin Care`, `Hair Care`, `Makeup`, `Fragrance`, `Wellness`, `Baby Care` |
| `quantity` | integer | No | Number of units in the order | 1 – 4 |
| `gross_amount` | float (INR) | No | Total order value before any discount; intentional outliers present for data-quality work | 149.0 – 24,789.38 |
| `discount_pct` | float | No | Discount applied as a decimal fraction (e.g., `0.20` = 20% off) | 0.0 – 0.7 |
| `delivery_days` | integer | No | Number of calendar days from order placement to delivery | 1 – 11 |
| `returned` | integer (binary) | No | Whether the order was returned (`1` = returned, `0` = not returned) | `0`, `1` |
| `rating` | integer | **Yes** (~80 nulls) | Customer satisfaction rating for the order; null means the customer did not leave a rating | 1 – 5 |

---

## 3. `support_tickets.csv`

One row per support interaction. A single customer can have multiple tickets.

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `ticket_id` | string | No | Unique ticket identifier | `TKT000001` – `TKT001921` |
| `customer_id` | string | No | Links to `customers.csv` | `CUST00001` – `CUST02398` |
| `ticket_date` | date (`YYYY-MM-DD`) | No | Date the ticket was raised | `2024-01-13` – `2025-09-30` |
| `issue_type` | string (categorical) | No | Nature of the customer's complaint or query | `damaged_item`, `late_delivery`, `refund_delay`, `wrong_item`, `product_reaction`, `payment_issue`, `general_query` |
| `support_channel` | string (categorical) | No | Channel through which the ticket was submitted | `chat`, `call`, `email` |
| `resolution_hours` | float | No | Time from ticket creation to resolution, in hours | 1.0 – 74.6 |
| `sentiment_score` | float | No | Model-generated sentiment score derived from the ticket text; negative = dissatisfied, positive = satisfied | –1.0 to +1.0 |
| `reopened` | integer (binary) | No | Whether the ticket was reopened after initial closure (`1` = reopened) | `0`, `1` |

---

## 4. `web_events_snapshot.csv`

One row per customer. All metrics are computed over the **30 days ending on the snapshot date** (`2025-09-01` to `2025-09-30`).

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `customer_id` | string | No | Links to `customers.csv` | `CUST00001` – `CUST02400` |
| `snapshot_date` | date | No | Always `2025-09-30`; the reference date for all counts in this file | `2025-09-30` |
| `sessions_30d` | integer | No | Number of web/app sessions in the last 30 days | ≥ 0 |
| `product_views_30d` | integer | No | Number of product detail pages viewed in the last 30 days | ≥ 0 |
| `cart_adds_30d` | integer | No | Number of times an item was added to the cart in the last 30 days | ≥ 0 |
| `wishlist_adds_30d` | integer | No | Number of times an item was added to the wishlist in the last 30 days | ≥ 0 |
| `abandoned_carts_30d` | integer | No | Number of cart sessions that ended without purchase in the last 30 days | ≥ 0 |
| `email_opens_30d` | integer | No | Number of marketing emails opened in the last 30 days | ≥ 0 |
| `campaign_clicks_30d` | integer | No | Number of clicks on marketing campaign links in the last 30 days | ≥ 0 |
| `last_visit_days_ago` | integer | No | Number of days since the customer's most recent website/app visit, measured from the snapshot date | ≥ 0 |

---

## 5. `churn_labels.csv`

One row per customer. The authoritative source for model targets and data splits.

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `customer_id` | string | No | Links to `customers.csv` | `CUST00001` – `CUST02400` |
| `snapshot_date` | date | No | Always `2025-09-30` | `2025-09-30` |
| `churn_next_60d` | integer (binary) | No | **Target variable.** `1` = customer made no purchase in the 60-day window after snapshot (`2025-10-01` to `2025-11-29`). `0` = customer made at least one purchase in that window. | `0`, `1` |
| `split` | string (categorical) | No | Pre-assigned train/validation/test split; use this for consistent evaluation across submissions | `train`, `validation`, `test` |

---

## 6. `rfm_modeling_snapshot.csv`

One row per customer. A pre-built, feature-engineered table combining all sources as of the snapshot date. Intended for Parts 3 and 4, so students can start modelling without completing EDA first. All features are safe to use as model inputs (no leakage).

| Column | Type | Description | Notes |
|---|---|---|---|
| `customer_id` | string | Unique customer identifier | — |
| `snapshot_date` | date | Always `2025-09-30` | — |
| `city_tier` | string | From `customers.csv` | — |
| `age_group` | string | From `customers.csv` | — |
| `acquisition_channel` | string | From `customers.csv` | — |
| `loyalty_tier` | string | From `customers.csv`; nulls present | — |
| `preferred_category` | string | From `customers.csv` | — |
| `marketing_consent` | string | From `customers.csv` | — |
| `recency_days` | integer | Days since the customer's last pre-snapshot order | Lower = more recent |
| `frequency_180d` | integer | Number of orders placed in the 180 days before snapshot | — |
| `monetary_180d` | float | Total gross spend (INR) in the 180 days before snapshot | — |
| `return_rate_180d` | float | Proportion of orders returned in the 180-day window | 0.0 – 1.0 |
| `avg_discount_pct_180d` | float | Average discount fraction across orders in the 180-day window | 0.0 – 1.0 |
| `avg_rating_180d` | float | Average order rating in the 180-day window; null if no ratings given | 1.0 – 5.0 |
| `category_diversity_180d` | integer | Number of distinct product categories purchased in the 180-day window | ≥ 1 |
| `ticket_count_90d` | integer | Number of support tickets raised in the 90 days before snapshot | ≥ 0 |
| `negative_ticket_rate_90d` | float | Proportion of tickets in the 90-day window with sentiment score < 0 | 0.0 – 1.0 |
| `avg_resolution_hours_90d` | float | Average ticket resolution time (hours) in the 90-day window; 0 if no tickets | ≥ 0.0 |
| `days_since_signup` | integer | Number of days from `signup_date` to snapshot date | — |
| `sessions_30d` | integer | From `web_events_snapshot.csv` | — |
| `product_views_30d` | integer | From `web_events_snapshot.csv` | — |
| `cart_adds_30d` | integer | From `web_events_snapshot.csv` | — |
| `wishlist_adds_30d` | integer | From `web_events_snapshot.csv` | — |
| `abandoned_carts_30d` | integer | From `web_events_snapshot.csv` | — |
| `email_opens_30d` | integer | From `web_events_snapshot.csv` | — |
| `campaign_clicks_30d` | integer | From `web_events_snapshot.csv` | — |
| `last_visit_days_ago` | integer | From `web_events_snapshot.csv` | — |
| `churn_next_60d` | integer (binary) | Target variable; same as in `churn_labels.csv` | **Do not use as a feature** |
| `split` | string | Train/val/test assignment; same as in `churn_labels.csv` | — |

---

## 7. `intervention_history.csv`

One row per customer. Records the most recent retention campaign delivered to each customer before the snapshot date.

| Column | Type | Nullable | Description | Values / Range |
|---|---|---|---|---|
| `customer_id` | string | No | Links to `customers.csv` | `CUST00001` – `CUST02400` |
| `snapshot_date` | date | No | Always `2025-09-30` | `2025-09-30` |
| `last_campaign_received` | string (categorical) | No | Type of the most recent retention campaign sent to this customer; `none` means no campaign has been sent | `welcome_offer`, `free_shipping`, `bundle_discount`, `new_launch`, `none` |
| `last_campaign_cost` | integer (INR) | No | Cost of the last campaign sent to this customer; `0` if `last_campaign_received` is `none` | 0 – 40 |
| `manual_priority_bucket` | string (categorical) | No | Manually assigned retention priority label set by the CRM team prior to the snapshot; useful as a baseline or signal in Part 2 | `high`, `medium`, `low` |

---

## Known Data Quality Issues (Intentional)

These are designed-in problems for Part 1 of the project. Do not treat them as errors in the dataset package.

| Issue | File | Column(s) | Detail |
|---|---|---|---|
| Duplicate-like records | `orders.csv` | `order_id` | Some order IDs end in `_DUP`. These simulate real-world deduplication challenges. |
| Missing values | `customers.csv` | `loyalty_tier`, `skin_type` | Not all customers have loyalty enrolment or skin-type data. |
| Missing ratings | `orders.csv` | `rating` | ~80 orders have no rating. Handle before computing averages. |
| Outlier order values | `orders.csv` | `gross_amount` | A small number of records have unusually high values (up to ₹24,789). Investigate and decide on treatment. |
| Post-snapshot orders | `orders.csv` | `order_date` | Rows with `order_date > 2025-09-30` must **not** be used as model features. |

---

## Join Guide

```
customers        ──── customer_id ────▶ orders
customers        ──── customer_id ────▶ support_tickets
customers        ──── customer_id ────▶ web_events_snapshot
customers        ──── customer_id ────▶ churn_labels
customers        ──── customer_id ────▶ rfm_modeling_snapshot
customers        ──── customer_id ────▶ intervention_history
```

All joins are **left joins from `customers`** (2,400 customers are the universe). Not every customer has support tickets; that is expected, not a data error.
