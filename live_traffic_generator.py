"""Generate continuous prediction traffic for real-time dashboard views."""

from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Any, Dict

import requests


def make_payload() -> Dict[str, Any]:
    """Create a valid randomized payload for /predict endpoint."""
    return {
        "days_signup_age": random.randint(30, 730),
        "recency_days": random.randint(0, 120),
        "frequency_total": random.randint(1, 160),
        "session_duration_avg": round(random.uniform(1.5, 32.0), 2),
        "feature_count_used": random.randint(1, 12),
        "device_type": random.choice(["Desktop", "Mobile", "Tablet"]),
        "os_type": random.choice(["Windows", "Android", "iOS", "Linux", "MacOS"]),
        "user_segment": random.choice(["Free", "Trial", "Premium", "Returning"]),
        "region": random.choice(["North", "South", "East", "West"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate live prediction traffic")
    parser.add_argument("--api-url", default="http://127.0.0.1:5000", help="Base API URL")
    parser.add_argument("--api-key", default="", help="X-API-Key value when auth is enabled")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between prediction calls")
    parser.add_argument("--burst", type=int, default=1, help="Number of requests per cycle")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json", "User-Agent": "DropoffLiveTraffic/1.0"})
    if args.api_key.strip():
        session.headers.update({"X-API-Key": args.api_key.strip()})

    url = f"{args.api_url.rstrip('/')}/predict"
    sent = 0
    errors = 0
    print(f"[live-traffic] Sending traffic to: {url}")
    print(f"[live-traffic] interval={args.interval}s burst={max(1, args.burst)}")

    try:
        while True:
            for _ in range(max(1, args.burst)):
                payload = make_payload()
                try:
                    response = session.post(url, json=payload, timeout=6)
                    if response.status_code == 200:
                        sent += 1
                    else:
                        errors += 1
                        body = response.text[:220].replace("\n", " ")
                        print(f"[live-traffic] non-200={response.status_code} body={body}")
                except requests.RequestException as exc:
                    errors += 1
                    print(f"[live-traffic] request failed: {exc}")

            print(f"[live-traffic] sent={sent} errors={errors}")
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        print("[live-traffic] stopped by user")

    return 0


if __name__ == "__main__":
    sys.exit(main())
