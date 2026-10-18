from pathlib import Path
import csv
from fastapi.testclient import TestClient
from app.main import app, get_model
from app.recommender import BasketRecommender

client = TestClient(app)

def test_actual_dataset():
    m = get_model()
    assert len(m.transactions) == 1000
    assert len(m.products) == 40
    assert m.metadata()['rule_count'] > 0
    assert 'D7050' in m.products

def test_api_catalog():
    response = client.get('/products')
    assert response.status_code == 200
    assert response.json()['total'] == 40

def test_empty_cart():
    r = client.post('/recommend', json={'cart': []})
    assert r.status_code == 200 and r.json()['recommendations'] == []

def test_unknown_sku():
    r = client.post('/recommend', json={'cart': ['FAKE-SKU']})
    assert r.status_code == 422

def test_real_single_cart_excludes_existing():
    model = get_model()
    r = client.post('/recommend', json={'cart': ['D7050']})
    assert r.status_code == 200
    assert all(p['sku'] != 'D7050' for p in r.json()['recommendations'])
    assert all(0 <= p['confidence'] <= 1 and p['lift'] >= 1 for p in r.json()['recommendations'])

def test_cart_subset_rules_and_ranking(tmp_path):
    file = tmp_path / 'tiny.csv'
    with file.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['transaction_id', 'item_1', 'item_2', 'item_3'])
        for i, skus in enumerate([['A', 'B', 'C'], ['A', 'B', 'C'], ['A', 'B'], ['C', 'D']], 1):
            w.writerow([i] + [f'Product {sku} (SKU: {sku})' for sku in skus])
    m = BasketRecommender(file, min_support=.1, min_confidence=.1, min_lift=0)
    results = m.recommend(['A', 'B'])
    assert next(r for r in results if r['sku'] == 'C')['matched_skus'] == ['A', 'B']
    results = m.recommend(['A', 'D'])
    assert {r['sku'] for r in results} == {'B', 'C'}
    assert results == m.recommend(['D', 'A'])
    assert len(results) == len({r['sku'] for r in results})
    assert m.recommend(['A', 'D'], limit=1) == results[:1]
    # The third cart item contributes even when the cart exceeds antecedent size.
    results = m.recommend(['A', 'B', 'D'])
    assert [r['sku'] for r in results] == ['C']
    assert results[0]['matched_skus'] == ['A', 'B']
    assert m.recommend(['A', 'B', 'C', 'D']) == []

def test_health_and_metadata():
    assert client.get('/health').json()['status'] == 'ok'
    assert client.get('/model-info').json()['algorithm'].startswith('Apriori')
