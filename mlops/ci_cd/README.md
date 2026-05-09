# CI/CD Setup

This folder contains MLOps CI/CD templates.

## Files
- quality_gates/thresholds.yaml: evaluation and service thresholds

## Active workflow
- .github/workflows/mlops-ci-cd.yml

## Pipeline Stages
1. test: compile checks and smoke data pipeline
2. train: feature engineering and model training
3. evaluate: model evaluation and quality gates
4. deploy: build deployment bundle (main branch only)
