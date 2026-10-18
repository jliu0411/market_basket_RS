"""FastAPI endpoints for the checkout recommendation demo."""
import os
from pathlib import Path
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .recommender import BasketRecommender

DEFAULT_CSV = Path(__file__).resolve().parents[2] / 'data' / 'transactions.csv'

@lru_cache(maxsize=1)
def get_model():
    return BasketRecommender(
        os.getenv('TRANSACTIONS_CSV', str(DEFAULT_CSV)),
        min_support=float(os.getenv('MIN_SUPPORT', '0.005')),
        min_confidence=float(os.getenv('MIN_CONFIDENCE', '0.08')),
        min_lift=float(os.getenv('MIN_LIFT', '1.0')),
        max_itemset_size=int(os.getenv('MAX_ITEMSET_SIZE', '3')),
    )

app = FastAPI(title='Electronic Retail Market Basket Recommender', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','),
                   allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['*'])

class RecommendationRequest(BaseModel):
    cart: list[str] = Field(default_factory=list, max_length=40)
    limit: int = Field(default=5, ge=1, le=20)

@app.get('/health')
def health():
    return {'status': 'ok', 'model_loaded': bool(get_model().transactions)}

@app.get('/products')
def products(search: str = Query(default='', max_length=100)):
    model = get_model()
    return {'products': [{'sku': p.sku, 'name': p.name} for p in sorted(model.products.values(), key=lambda p: p.name.lower())
                         if search.lower() in p.name.lower() or search.lower() in p.sku.lower()], 'total': len(model.products)}

@app.get('/model-info')
def model_info():
    return get_model().metadata()

@app.post('/recommend')
def recommend(payload: RecommendationRequest):
    model = get_model()
    unknown = sorted(set(payload.cart) - set(model.products))
    if unknown:
        raise HTTPException(status_code=422, detail={'unknown_skus': unknown})
    results = model.recommend(payload.cart, payload.limit)
    return {'cart': sorted(set(payload.cart)), 'recommendations': results,
            'message': ('Add a product to receive recommendations.' if not payload.cart else
                        'No sufficiently strong rule matches items in this cart.' if not results else
                        f'{len(results)} recommendation(s) found.')}
