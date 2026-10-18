"""Pure-Python Apriori and association-rule recommender (no external ML dependency).

Supports up to 3-item antecedents and matches rules against subsets of the cart.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
import csv
import math
import re
from pathlib import Path

SKU_PATTERN = re.compile(r"\(SKU:\s*(.*?)\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Product:
    sku: str
    name: str


@dataclass(frozen=True)
class Rule:
    antecedent: tuple[str, ...]
    consequent: str
    support: float
    confidence: float
    lift: float
    count: int


class BasketRecommender:
    def __init__(self, csv_path: str | Path, min_support: float = 0.005,
                 min_confidence: float = 0.08, min_lift: float = 1.0,
                 max_itemset_size: int = 3):
        if not (0 < min_support <= 1 and 0 <= min_confidence <= 1 and min_lift >= 0):
            raise ValueError('Invalid support, confidence, or lift setting')
        if not (2 <= max_itemset_size <= 4):
            raise ValueError('max_itemset_size must be between 2 and 4')
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_itemset_size = max_itemset_size
        self.transactions: list[frozenset[str]] = []
        self.products: dict[str, Product] = {}
        with open(csv_path, newline='', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or 'transaction_id' not in reader.fieldnames:
                raise ValueError('Missing transaction_id column')
            item_cols = [col for col in reader.fieldnames if col.startswith('item_')]
            if not item_cols:
                raise ValueError('Missing item_1, item_2, ... columns')
            by_transaction: dict[str, set[str]] = {}
            for row in reader:
                transaction_id = (row.get('transaction_id') or '').strip()
                if not transaction_id:
                    continue
                basket = by_transaction.setdefault(transaction_id, set())
                for col in item_cols:
                    text = (row.get(col) or '').strip()
                    if not text:
                        continue
                    m = SKU_PATTERN.search(text)
                    if not m:
                        raise ValueError(f'Product missing SKU annotation: {text}')
                    sku = m.group(1).strip()
                    name = text[:m.start()].strip()
                    if sku in self.products and self.products[sku].name != name:
                        raise ValueError(f'Conflicting product names for SKU {sku}')
                    self.products[sku] = Product(sku, name)
                    basket.add(sku)
            self.transactions = [frozenset(items) for items in by_transaction.values() if items]
        if not self.transactions:
            raise ValueError('No usable transactions in dataset')
        self.counts = self._apriori()
        self.rules = self._generate_rules()

    def _apriori(self) -> dict[frozenset[str], int]:
        n = len(self.transactions)
        threshold = max(1, math.ceil(self.min_support * n - 1e-10))
        frequencies = Counter(sku for basket in self.transactions for sku in basket)
        previous = {frozenset([sku]): count for sku, count in frequencies.items() if count >= threshold}
        frequent = dict(previous)
        for size in range(2, self.max_itemset_size + 1):
            previous_keys = set(previous)
            candidates = set()
            for a, b in combinations(sorted(previous_keys, key=lambda x: tuple(sorted(x))), 2):
                union = a | b
                if len(union) == size and all(frozenset(part) in previous_keys for part in combinations(sorted(union), size - 1)):
                    candidates.add(union)
            if not candidates:
                break
            # Count membership directly; efficient for this 40-SKU dataset.
            counted = {candidate: sum(candidate <= basket for basket in self.transactions) for candidate in candidates}
            previous = {key: count for key, count in counted.items() if count >= threshold}
            if not previous:
                break
            frequent.update(previous)
        return frequent

    def _generate_rules(self) -> list[Rule]:
        n = len(self.transactions)
        rules = []
        for group, count in self.counts.items():
            if len(group) < 2:
                continue
            # Consequent is exactly one SKU, so frontend can recommend one product.
            for consequent in group:
                antecedent = group - {consequent}
                antecedent_count = self.counts.get(antecedent, 0)
                consequent_count = self.counts.get(frozenset([consequent]), 0)
                if not antecedent_count or not consequent_count:
                    continue
                support = count / n
                confidence = count / antecedent_count
                lift = confidence / (consequent_count / n)
                if confidence >= self.min_confidence and lift >= self.min_lift:
                    rules.append(Rule(tuple(sorted(antecedent)), consequent, support, confidence, lift, count))
        return sorted(rules, key=lambda r: (-r.confidence, -r.lift, -r.support, r.consequent))

    def recommend(self, cart: list[str], limit: int = 5) -> list[dict]:
        normalized = frozenset(cart)
        if not normalized or any(sku not in self.products for sku in normalized):
            return []
        # Every cart item can contribute; prefer evidence from larger combinations.
        applicable = [r for r in self.rules if frozenset(r.antecedent) <= normalized and r.consequent not in normalized]
        rank = lambda r: (-len(r.antecedent), -r.confidence, -r.lift, -r.support, r.consequent)
        best: dict[str, Rule] = {}
        for rule in sorted(applicable, key=rank):
            if rule.consequent not in best:
                best[rule.consequent] = rule
        ranked = sorted(best.values(), key=rank)
        return [{**asdict(self.products[r.consequent]), 'support': round(r.support, 4),
                 'confidence': round(r.confidence, 4), 'lift': round(r.lift, 4),
                 'matched_skus': list(r.antecedent), 'transaction_count': r.count}
                for r in ranked[:limit]]

    def metadata(self) -> dict:
        return {'transaction_count': len(self.transactions), 'product_count': len(self.products),
                'frequent_itemset_count': len(self.counts), 'rule_count': len(self.rules),
                'algorithm': 'Apriori (frequent itemsets + association rules)',
                'min_support': self.min_support, 'min_confidence': self.min_confidence,
                'min_lift': self.min_lift, 'max_itemset_size': self.max_itemset_size,
                'matching_policy': 'Cart subset matching, prioritizing larger antecedents'}
