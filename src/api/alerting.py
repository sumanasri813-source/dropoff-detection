"""
Automated Alerting System

This module continuously monitors the prediction outputs and triggers alerts
(e.g., to Slack or Email) when a user's drop-off probability exceeds the critical threshold.
"""

import time
import json
import logging
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [ALERTING] - %(message)s")

API_URL = "http://127.0.0.1:5000"
API_KEY = "dev-local-key"
CRITICAL_THRESHOLD = 0.75
CHECK_INTERVAL_SECONDS = 60

import os

# Mock webhook URL for demonstration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "https://api.example.com/webhook")
RISK_ALERTS_PATH = "mlops/monitoring/alerts/risk_alerts.jsonl"

def persist_risk_alert(user_id, probability, factors):
    """Saves the alert to a local file for dashboard integration."""
    os.makedirs(os.path.dirname(RISK_ALERTS_PATH), exist_ok=True)
    alert = {
        "timestamp": datetime.now().isoformat(),
        "type": "risk_alert",
        "severity": "critical" if probability >= 0.85 else "warning",
        "user_id": user_id,
        "probability": float(probability),
        "factors": factors,
        "message": f"High risk detected for user {user_id}"
    }
    with open(RISK_ALERTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


def send_slack_alert(user_id, probability, factors):
    """Mocks sending a Slack alert to the retention team."""
    msg = (
        f"🚨 *HIGH CHURN RISK DETECTED*\n"
        f"User ID: `{user_id}`\n"
        f"Drop-off Probability: *{probability:.1%}*\n"
        f"Key Factors: {', '.join(factors)}\n"
        f"Action: Consider immediate retention intervention."
    )
    
    payload = {"text": msg}
    
    logging.info(f"Triggering Alert for User {user_id} (Prob: {probability:.2f})")
    
    # Persist for dashboard view
    persist_risk_alert(user_id, probability, factors)
    
    # In production, this would be an actual POST request:
    # requests.post(SLACK_WEBHOOK_URL, json=payload)
    print("\n" + "="*50)
    print("🔔 SIMULATED SLACK NOTIFICATION:")
    print("="*50)
    print(msg)
    print("="*50 + "\n")


def monitor_predictions():
    """Polls the API for recent high-risk predictions and alerts if needed."""
    logging.info("Starting real-time alerting monitor...")
    
    seen_predictions = set()
    
    while True:
        try:
            headers = {"X-API-Key": API_KEY}
            response = requests.get(f"{API_URL}/predictions?limit=10", headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                predictions = data.get("predictions", [])
                
                for pred in predictions:
                    pred_id = pred.get("id")
                    prob = pred.get("dropoff_probability", 0)
                    
                    if pred_id not in seen_predictions and prob >= CRITICAL_THRESHOLD:
                        # Extract some mock factors from payload if available
                        payload = pred.get("payload_json", "{}")
                        try:
                            payload_data = json.loads(payload)
                            factors = []
                            if payload_data.get("recency_days", 0) > 30:
                                factors.append("High Recency (Inactive)")
                            if payload_data.get("session_duration_avg", 10) < 5:
                                factors.append("Low Session Duration")
                        except:
                            factors = ["Behavioral Decline"]
                            
                        send_slack_alert(pred_id, prob, factors)
                        seen_predictions.add(pred_id)
            else:
                logging.warning(f"Failed to fetch predictions. Status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error: {e}")
            
        # Wait before next poll
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    monitor_predictions()
