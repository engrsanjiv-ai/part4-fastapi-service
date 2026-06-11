from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}


def test_predict_minimal():
    payload = {
        'customer_id': 'C123',
        'total_orders': 1,
        'total_amount': 50.0,
        'avg_order_value': 50.0,
        'recency_days': 400,
        'support_ticket_count': 0
    }
    r = client.post('/predict', json=payload)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        j = r.json()
        assert 'churn_probability' in j
        assert 'predicted_class' in j


def test_batch_predict():
    payload = [
        {
            'customer_id': 'C1',
            'total_orders': 0,
            'total_amount': 0.0,
            'avg_order_value': 0.0,
            'recency_days': 9999,
            'support_ticket_count': 0
        },
        {
            'customer_id': 'C2',
            'total_orders': 5,
            'total_amount': 250.0,
            'avg_order_value': 50.0,
            'recency_days': 10,
            'support_ticket_count': 0
        }
    ]
    r = client.post('/batch_predict', json=payload)
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        j = r.json()
        assert 'predictions' in j
        assert len(j['predictions']) == 2
