# FINAL SUBMISSION GUIDE

This guide is designed for quick project evaluation.

## 1. Run The Project (Step-by-Step)

### Option A (Recommended): One-click run in VS Code
1. Open Command Palette (`Ctrl+Shift+P`)
2. Select `Tasks: Run Task`
3. Choose `Run final demo process`

### Option B: Terminal run
From project root:

```powershell
powershell -ExecutionPolicy Bypass -File run_final_process.ps1
```

## 2. Expected Output

After running, you should see:
- Database migration completed
- Contract tests completed (all pass)
- API started in background
- Health endpoint response printed

Key success signals in output:
- `API is ready.`
- `Demo process complete.`
- Health JSON contains:
  - `"status": "ok"`
  - `"model_loaded": true`
  - `"database": {"connected": true}`
  - `"worker": {"running": true}`

## 3. How To Test The API

Use these commands in a new terminal.

### 3.1 Health check

```powershell
curl -H "X-API-Key: dev-local-key" http://127.0.0.1:5000/health
```

Expected: HTTP 200 with `status: ok` and `model_loaded: true`

### 3.2 Single prediction

```powershell
curl -X POST http://127.0.0.1:5000/predict -H "Content-Type: application/json" -H "X-API-Key: dev-local-key" -d "{\"days_signup_age\":10,\"recency_days\":2,\"frequency_total\":20,\"session_duration_avg\":12.5,\"feature_count_used\":4,\"device_type\":\"mobile\",\"os_type\":\"android\",\"user_segment\":\"free\",\"region\":\"north\"}"
```

Expected: HTTP 200 with fields like:
- `dropoff_probability`
- `predicted_label`
- `risk_level`
- `threshold_used`

### 3.3 Batch prediction

```powershell
curl -X POST http://127.0.0.1:5000/predict-batch -H "Content-Type: application/json" -H "X-API-Key: dev-local-key" -d "{\"records\":[{\"days_signup_age\":10,\"recency_days\":2,\"frequency_total\":20,\"session_duration_avg\":12.5,\"feature_count_used\":4,\"device_type\":\"mobile\",\"os_type\":\"android\",\"user_segment\":\"free\",\"region\":\"north\"}]}"
```

Expected: HTTP 200 with batch summary and predictions list

## 4. How To Verify The Model Works

Use this quick checklist:

1. Health endpoint confirms model is loaded
- `model_loaded` is `true`

2. Prediction endpoint returns valid inference output
- probability + label + risk level are present

3. Evaluation artifacts exist in project
- `results/evaluation_metrics.json`
- `results/evaluation_summary.txt`
- `results/threshold_analysis.csv`

4. Trained model artifact exists
- `models/final_model.pkl`

If all four checks pass, the model pipeline and serving path are working correctly.

## 5. Quick Troubleshooting

If API does not start:
- Re-run with dependency install:

```powershell
powershell -ExecutionPolicy Bypass -File run_final_process.ps1
```

If auth errors occur:
- Ensure `X-API-Key: dev-local-key` header is included in API calls.

If port is busy:
- Re-run the same script; it cleans up prior PID and restarts API.
