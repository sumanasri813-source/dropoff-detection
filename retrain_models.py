#!/usr/bin/env python
"""Quick retraining script to generate metrics with accuracy."""

from src.models.train_model import train_model
import pandas as pd

print("=" * 60)
print("RETRAINING MODELS WITH ACCURACY METRIC")
print("=" * 60)

result = train_model()

print("\n✓ Training complete!")
print(f"Best model: {result['best_model']}")
print(f"Best ROC-AUC: {result['best_roc_auc']:.4f}")

df = pd.read_csv('results/model_comparison.csv')
print("\n" + "=" * 60)
print("MODEL COMPARISON METRICS")
print("=" * 60)
print(df.to_string(index=False))
print("=" * 60)
