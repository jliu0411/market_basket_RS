# Electronic Retailer Market Basket Recommendation System

**SJSU CMPE 256 Hackathon — slides 6–11**

A working checkout demonstration using the **real 1,000-order Retail dataset** supplied with the assignment. React renders a searchable 40-product catalog, an interactive cart, and live recommendations. FastAPI provides the product API and **Apriori** association-rule engine.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer and npm

## Run it in VS Code

Open the `market-basket-recommender` folder in VS Code and open **two terminals**.

### Terminal 1: backend

**Windows PowerShell**

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

If PowerShell prohibits activating the virtual environment, use ` .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` then ` .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000 ; interactive API documentation: http://127.0.0.1:8000/docs

### Terminal 2: frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Select products to see recommendations update. API URL defaults to `http://127.0.0.1:8000`; override via `frontend/.env` with `VITE_API_URL=...`.

## Dataset

`data/transactions.csv` is included; it is extracted from the uploaded Retail ZIP, **not fabricated**. It contains the columns `transaction_id,item_1,item_2,item_3,item_4,item_5`, one row per historical transaction, with SKU embedded in each product's label.

## Algorithm

`backend/app/recommender.py` implements Apriori in standard Python (no mlxtend dependency). It counts frequent singleton items, joins/prunes candidates to find frequent 2- and 3-itemsets, and generates rules of the form `{A, B} -> {C}`. A rule is retained if it passes minimum support, confidence and lift thresholds. Results are sorted by descending confidence, lift and support.

- **Support**: `count(A ∪ C) / number_of_transactions`
- **Confidence**: `count(A ∪ C) / count(A)`
- **Lift**: `confidence / (count(C) / number_of_transactions)`

Defaults: `MIN_SUPPORT=0.005`, `MIN_CONFIDENCE=0.08`, `MIN_LIFT=1.0`, `MAX_ITEMSET_SIZE=3`. These can be overridden with environment variables on the backend. No paid APIs are required.

### Important: unseen baskets

Recommendations use rules whose antecedents are contained in the cart, excluding products already selected. Rules matching more cart items rank first, followed by confidence, lift, and support. Each suggested product appears once with the metrics and matched SKUs of its strongest ranked rule. Carts larger than the maximum antecedent size can still receive recommendations from matching subsets.

The project intentionally does **not** claim every basket can be matched. A production system could use explicit backoff policies, larger training datasets or a separate recommender if that requirement changes.

## API

| Request | Description |
| --- | --- |
| `GET /health` | Backend health check |
| `GET /products?search=Bosch` | Product catalog filtered by name or SKU |
| `GET /model-info` | Model parameters and counts |
| `POST /recommend` | Rank association-rule recommendations for cart |

Request:

```json
{"cart":["D7050"],"limit":5}
```

Response contains `recommendations` with `sku`, `name`, `confidence`, `support`, `lift`, `matched_skus` and `transaction_count`. Unrecognized SKUs return HTTP 422; empty or unmatched carts return an empty list.

## Testing and rule export

From `backend/` (with venv active):

```bash
python -m pytest -v
python scripts/train.py
```

The second command exports `data/association_rules.csv` and prints the model statistics. Training is performed in memory when FastAPI first receives a request; no separately saved model is needed. The exported file is for analysis.

## Suggested demo

1. Start with an empty cart.
2. Add a single product, e.g. `Bosch D7050 Detector`.
3. Look at ranked recommendations and their metrics.
4. Add a suggested product and watch the engine recompute rules using the *entire* cart.
5. Try an unmatched combination and show the explicit no-recommendation state.
6. Open `/docs` and `/model-info` to show the microservice and explain support, confidence, and lift.

## Evaluation / deployment notes

This is a runnable hackathon prototype, not a claim of production-grade accuracy. For formal validation, use a transaction-level train/test split, withhold one product from each test basket, and report Precision@K/Recall@K and no-match coverage. Use separate train data to learn association rules, then score against the held-out transactions to avoid leakage. Track API latency, empty-result rate, and changing SKU frequencies; retrain periodically as new transactions arrive. Deploy frontend to Netlify and API to a Python-compatible service with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, with an explicit backend working directory and `CORS_ORIGINS` set to the deployed frontend URL.

## Windows one-click launch (recommended)

Install **Python 3** and **Node.js LTS** once (they must be on PATH). In the extracted project directory, double-click **`start.bat`**. It creates `backend/.venv` if necessary, installs Python packages, installs npm packages if necessary, starts the API and React app, and opens the browser at http://localhost:5173. The first run needs internet access and can take several minutes. Keep the resulting server windows open while using the app.

Double-click **`stop.bat`** to stop both services. If you close the server windows manually, run `stop.bat` to remove the stored PID file before launching again. Alternatively, from PowerShell run `./start.ps1` and `./stop.ps1` (your execution policy may require the batch wrappers). The launcher uses ports **8000** and **5173**, so free them if another application is using either port.
