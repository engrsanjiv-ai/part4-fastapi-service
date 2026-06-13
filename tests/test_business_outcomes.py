from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_business_outcomes_conversion():
    payload = {
        'customer_id': 'C123',
        'campaign_id': 'CMP1',
        'interaction_count': 3,
        'conversion': True,
        'revenue_retention': 120.0,
        'churn_lift': 0.08,
        'risk_level': 'high'
    }
    r = client.post('/business_outcomes', json=payload)
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}


def test_business_outcomes_no_conversion():
    payload = {
        'customer_id': 'C124',
        'campaign_id': 'CMP2',
        'interaction_count': 1,
        'conversion': False,
        'revenue_retention': 0.0,
        'churn_lift': -0.02,
        'risk_level': 'medium'
    }
    r = client.post('/business_outcomes', json=payload)
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}
