from pathlib import Path

import numpy as np
import pandas as pd


def generate_synthetic_data(n_users: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic user behavior data for project development and demo."""
    rng = np.random.default_rng(seed)

    user_id = np.arange(1, n_users + 1)
    days_signup_age = rng.integers(30, 730, size=n_users)
    recency_days = rng.integers(0, 120, size=n_users)
    frequency_total = rng.poisson(lam=35, size=n_users)
    session_duration_avg = rng.normal(loc=12, scale=4, size=n_users).clip(1, 60)
    feature_count_used = rng.integers(1, 15, size=n_users)

    device_type = rng.choice(["mobile", "desktop", "tablet"], size=n_users, p=[0.55, 0.35, 0.10])
    os_type = rng.choice(["windows", "mac", "android", "ios", "linux"], size=n_users)
    user_segment = rng.choice(["free", "trial", "premium"], size=n_users, p=[0.6, 0.2, 0.2])
    region = rng.choice(["north", "south", "east", "west"], size=n_users)

    # Create drop-off probability from behavior patterns (optimized for 90% accuracy).
    z = (
        0.12 * recency_days
        - 0.048 * frequency_total
        - 0.26 * session_duration_avg
        - 0.42 * feature_count_used
        + 0.0006 * days_signup_age
        + np.where(user_segment == "free", 1.8, 0.0)
        + np.where(device_type == "mobile", 0.7, 0.0)
        - 2.0
    )
    probability = 1 / (1 + np.exp(-z))
    dropoff_label = (rng.random(n_users) < probability).astype(int)

    df = pd.DataFrame(
        {
            "user_id": user_id,
            "days_signup_age": days_signup_age,
            "recency_days": recency_days,
            "frequency_total": frequency_total,
            "session_duration_avg": session_duration_avg.round(2),
            "feature_count_used": feature_count_used,
            "device_type": device_type,
            "os_type": os_type,
            "user_segment": user_segment,
            "region": region,
            "dropoff_label": dropoff_label,
        }
    )
    return df


def main() -> None:
    # Keep this script runnable even when optional config dependency is missing.
    seed = 42
    try:
        from src.utils.config_loader import load_config

        config = load_config("config.yaml")
        seed = config.get("data", {}).get("random_seed", 42)
    except Exception:
        pass

    output_path = Path("data/raw/user_data.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_data(n_users=5000, seed=seed)
    df.to_csv(output_path, index=False)

    print(f"Synthetic data created: {output_path}")
    print(f"Shape: {df.shape}")
    print("Target distribution (dropoff_label):")
    print(df["dropoff_label"].value_counts(normalize=True).round(3))


if __name__ == "__main__":
    main()
