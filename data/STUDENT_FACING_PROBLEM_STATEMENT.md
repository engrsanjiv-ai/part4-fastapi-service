# Capstone Project: D2C Customer Churn Intelligence & Retention API

## Business Context

A D2C personal-care brand wants to reduce customer churn without blindly giving discounts to everyone. The product, marketing, and customer-support teams need a data-backed system that can:

1. understand customer behavior,
2. identify churn-risk patterns,
3. recommend which customers should be prioritized for retention, and
4. expose a simple API that can be used by an internal CRM tool.

You are given customer, order, support-ticket, web/app activity, campaign, and churn-label data. Your work must be submitted as **four separate GitHub repositories/links**, one for each part below. Each part must be independently understandable and runnable.

---

## Dataset

Use the provided dataset package. The snapshot date and target definition are given in the data dictionary.

Important: For model features, use only data available on or before the snapshot date. Data after the snapshot date must not be used as model input.

---

## Submission Format

Submit exactly four public GitHub links:

1. Part 1 GitHub link
2. Part 2 GitHub link
3. Part 3 GitHub link
4. Part 4 GitHub link

Each repository must contain:

- `README.md` explaining how to run the work
- required notebook/script files
- `requirements.txt` or clear setup instructions
- outputs/reports requested in that part
- no private credentials, tokens, or local-only file paths

---

# Part 1 — Data Audit, EDA & Business Understanding [20 Marks]

## Objective

Understand the business problem and audit the raw data before building any model.

## Tasks

1. Load and inspect all raw datasets: customers, orders, support tickets, web/app events, labels, and intervention history.
2. Create a clear data-quality report covering missing values, duplicate-like records, outliers, invalid values, and join issues.
3. Perform exploratory analysis on customer behavior, order patterns, support-ticket issues, web/app activity, and churn distribution.
4. Identify at least **five churn-risk hypotheses** from your analysis. Each hypothesis must be supported by a chart/table and a short explanation.
5. Write a short business memo explaining what the company should investigate before launching any retention campaign.

## Required Outputs

- `eda_audit.ipynb`
- `data_quality_report.md`
- `business_memo.md`
- at least 6 meaningful charts/tables

## Marks Breakdown

| Component | Marks |
|---|---:|
| Correct loading, joining, and schema understanding | 4 |
| Data-quality audit and treatment recommendations | 5 |
| Meaningful EDA and visual analysis | 6 |
| Churn-risk hypotheses grounded in evidence | 3 |
| Business memo clarity and prioritization | 2 |

---

# Part 2 — RFM Segmentation & Retention Strategy [20 Marks]

## Objective

Create customer segments and recommend targeted retention actions. This part should be possible even without building a machine-learning model.

## Tasks

1. Build RFM features using the order data: recency, frequency, and monetary value.
2. Create at least 5 customer segments such as champions, loyal customers, at-risk customers, discount-sensitive customers, and dormant customers. You may define your own segment names, but you must justify the logic.
3. Combine RFM with at least two additional signals such as support complaints, return rate, app/web activity, campaign engagement, or category diversity.
4. Recommend a retention action for each segment.
5. Choose a limited campaign budget and explain which segment/customer group should be prioritized first.
6. Include a manual review section with at least **10 specific customer IDs** where the decision is not obvious, and explain what you would do for them.

## Required Outputs

- `rfm_segmentation.ipynb`
- `segments.csv` with `customer_id`, `segment_name`, and important segment features
- `retention_strategy.md`
- `manual_review_cases.md`

## Marks Breakdown

| Component | Marks |
|---|---:|
| Correct RFM feature creation | 5 |
| Segment design and justification | 5 |
| Use of non-RFM behavioral/support signals | 3 |
| Retention strategy and budget prioritization | 4 |
| Manual review cases and reasoning quality | 3 |

---

# Part 3 — Churn Prediction Model & Model Card [35 Marks]

## Objective

Build a churn-prediction model that can identify customers likely to churn in the next 60 days.

## Tasks

1. Use the provided modeling snapshot or create your own feature table from raw data.
2. Clearly separate train, validation, and test data using the provided split or a justified alternative.
3. Train at least two models:
   - one simple baseline model
   - one stronger model such as Random Forest, Gradient Boosting, XGBoost, LightGBM, or another justified classifier
4. Evaluate the model using metrics suitable for churn classification. Accuracy alone is not sufficient.
5. Select a decision threshold and justify it from a business perspective.
6. Perform error analysis using false positives and false negatives. Include at least **10 specific customer examples** with your interpretation.
7. Explain the top features driving predictions.
8. Write a model card covering intended use, data, performance, limitations, ethical risks, and monitoring needs.

## Minimum Expected Performance

Your final model should attempt to beat the baseline on validation data. There is no full-mark guarantee for only crossing a metric threshold; marks depend on correctness, reasoning, and defensibility.

## Required Outputs

- `churn_model.ipynb`
- `model.pkl` or equivalent saved model artifact
- `metrics.json`
- `error_analysis.md`
- `model_card.md`

## Marks Breakdown

| Component | Marks |
|---|---:|
| Correct feature preparation and leakage prevention | 7 |
| Baseline and stronger model implementation | 6 |
| Evaluation using suitable metrics | 6 |
| Threshold selection and business justification | 4 |
| Error analysis with specific customer examples | 5 |
| Feature importance/interpretability | 3 |
| Model card quality and ethical framing | 4 |

---

# Part 4 — FastAPI Churn Scoring Service & Reproducible ML Workflow [25 Marks]

## Objective

Turn the churn model into a simple internal service that another team could use.

## Tasks

1. Create a FastAPI app with at least the following endpoints:
   - `GET /health`
   - `POST /predict` for one customer feature payload
   - `POST /batch_predict` for multiple customer payloads
2. Load the saved model and return churn probability, predicted class, and a short risk explanation.
3. Add input validation using Pydantic models.
4. Add at least 3 test cases for the API.
5. Add a reproducibility setup using `requirements.txt`; Docker is optional but will receive credit if working.
6. Add a short monitoring plan explaining what should be tracked after deployment: data drift, prediction distribution, business outcomes, API errors, and retraining triggers.
7. Include a short note on responsible use: how the API output should and should not be used by the retention team.

## Required Outputs

- `app/main.py` or equivalent FastAPI app
- saved model file or script to train and save the model
- `tests/` folder or test script
- `README.md` with run instructions and sample request/response
- `monitoring_plan.md`

## Marks Breakdown

| Component | Marks |
|---|---:|
| Working API structure and endpoints | 6 |
| Model loading and valid prediction response | 5 |
| Input validation and error handling | 4 |
| API tests | 3 |
| Reproducibility setup / Docker readiness | 3 |
| Monitoring and responsible-use plan | 4 |

---

## Overall Evaluation Rules

- Your work must be your own and grounded in the dataset outputs.
- You may use AI tools for support, but copied generic explanations without dataset-backed evidence will receive low marks.
- Use charts, metrics, customer IDs, and examples from your own run wherever reasoning is required.
- Do not use future/post-snapshot data as model input. Using leaked target-window information in model features may lead to major deduction.
- Repositories must be public and runnable. Broken links, empty repositories, missing files, or private repositories may receive zero for that part.
