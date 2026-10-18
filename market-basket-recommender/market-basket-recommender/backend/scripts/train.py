"""Train/inspect association rules and export readable output for the report."""
import csv
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.main import get_model

model = get_model()
print(json.dumps(model.metadata(), indent=2))
output = ROOT / 'data' / 'association_rules.csv'
with output.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['antecedent_skus', 'consequent_sku', 'support', 'confidence', 'lift', 'transaction_count'])
    for r in model.rules:
        writer.writerow([';'.join(r.antecedent), r.consequent, f'{r.support:.5f}', f'{r.confidence:.5f}', f'{r.lift:.4f}', r.count])
print(f'Exported {len(model.rules)} rules to {output}')
