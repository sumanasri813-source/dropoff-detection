# FINAL DEMO - START HERE

## Quick Start (30 seconds)

### Option 1: One-click in VS Code (RECOMMENDED)
1. **Open Command Palette**: `Ctrl+Shift+P`
2. Type: `Tasks: Run Task`
3. Select: `Run final demo process`
4. Wait for completion. API should be ready in about 15 seconds.

### Option 2: PowerShell Terminal
```powershell
powershell -ExecutionPolicy Bypass -File run_final_process.ps1
```

---

## What the Demo Does

- Database migration (initializes SQLite schema)
- Contract tests (24 security and functionality tests)
- API startup (Flask app with API-key protection)
- Health check (confirms service readiness)

**Total Time**: ~15 seconds  
**Expected Result**: Health endpoint returns `status: "healthy"` with model loaded, database connected, worker running

---

## Expected Output

```json
{
  "status": "ok",
  "model_loaded": true,
  "database": {
    "connected": true
  },
  "health": {
    "status": "healthy"
  },
  "worker": {
    "running": true
  }
}
```

---

## Testing the API After Demo Starts

The API runs in the background. Test it with:

```bash
# Get all users
curl -H "X-API-Key: dev-local-key" http://localhost:5000/users

# Make a prediction
curl -X POST http://localhost:5000/predict \
  -H "X-API-Key: dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "login_count": 10, "session_duration": 45}'

# Check monitoring data
curl -H "X-API-Key: dev-local-key" http://localhost:5000/monitor
```

---

## Full Documentation

For detailed setup, architecture, and checklist, see [README.md](README.md#mca-final-5-minute-runbook)

---

Ready to evaluate: run the VS Code task `Run final demo process`.
