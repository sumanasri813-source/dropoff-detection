# Week 1 (Day 1-5) File-by-File Checklist

This checklist maps the Day 1-5 roadmap directly to your current repository files.

## Day 1 - Contract Freeze and Documentation

- [ ] Create public OpenAPI spec: `docs/contracts/openapi-gateway-v1.yaml`
- [ ] Create public JSON Schema: `docs/contracts/public-gateway-contract.schema.json`
- [ ] Create internal JSON Schema: `docs/contracts/internal-model-service-contract.schema.json`
- [ ] Confirm feature parity with inference keys in `src/api/prediction_service.py`
- [ ] Add contract usage notes to `README.md`

Acceptance checks:
- [ ] Public request contains `request_id`, `user`, `session`, `features`
- [ ] Internal request contains `feature_payload` aligned to `FEATURE_KEYS`
- [ ] Error payload format is standardized

## Day 2 - Python Model Service Boundary Cleanup

- [ ] Update `src/api/app.py` to expose internal endpoint namespace (example: `/internal/v1/predict`)
- [ ] Keep model loading/inference behavior in `src/api/prediction_service.py`
- [ ] Ensure threshold and risk levels still load from `results/evaluation_metrics.json` and `config.yaml`
- [ ] Keep health and monitoring endpoints in `src/api/app.py` intact

Acceptance checks:
- [ ] Existing `/predict` remains backward compatible (if needed)
- [ ] New internal route reuses same prediction logic
- [ ] Request IDs are returned for success and error responses

## Day 3 - Contract and Validation Tests

- [ ] Add contract test file: `tests/contract/test_predict_contract.py`
- [ ] Add valid request fixture: `tests/contract/fixtures/public_predict_valid.json`
- [ ] Add invalid request fixture: `tests/contract/fixtures/public_predict_invalid.json`
- [ ] Add response contract fixture: `tests/contract/fixtures/public_predict_response.json`
- [ ] Keep existing contract tests green in `tests/contract/test_alert_rules.py`

Acceptance checks:
- [ ] Missing fields fail with expected error code
- [ ] Wrong enum/type fails with clear validation message
- [ ] Success response includes model metadata and latency fields

## Day 4 - Integration and Behavior Verification

- [ ] Add integration test file: `tests/integration/test_prediction_flow.py`
- [ ] Reuse test setup style from `tests/integration/test_monitoring_worker.py`
- [ ] Validate threshold behavior using `results/evaluation_metrics.json`
- [ ] Add test for batch behavior against `src/api/app.py` batch route

Acceptance checks:
- [ ] End-to-end prediction works for a known payload
- [ ] Batch route returns partial success (`207`) when mixed valid/invalid records are sent
- [ ] Prediction response risk label matches configured thresholds

## Day 5 - Observability and Config Hardening

- [ ] Confirm request metrics/logs in `src/utils/metrics.py` and `src/utils/logger.py`
- [ ] Confirm alert rules are evaluated in `src/utils/alerts.py`
- [ ] Validate background monitor behavior in `src/utils/monitoring_worker.py`
- [ ] Verify API deployment configuration in `config.yaml`
- [ ] Align environment values in `mlops/configs/environments/dev.yaml`

Acceptance checks:
- [ ] Every request logs `request_id`, path, status, latency
- [ ] Metrics persist endpoint behaves as expected
- [ ] Alert records are written when thresholds are exceeded

## Suggested Daily Verification Commands

Use your current environment and run these each day after changes:

```powershell
python -m pytest tests/contract -q
python -m pytest tests/integration -q
python run_pipeline.py
```

## End-of-Week Done Criteria

- [ ] Contracts are versioned and documented
- [ ] Internal model service boundary is stable
- [ ] Contract + integration tests pass
- [ ] Monitoring/logging/alerts validated
- [ ] README updated with new API contract references
