from src.data.generate_synthetic_data import generate_synthetic_data
from src.data.preprocessing import run_preprocessing


def main() -> None:
    # Step 1A: Generate synthetic source data if real data is not available.
    df = generate_synthetic_data(n_users=8000, seed=42)
    df.to_csv("data/raw/user_data.csv", index=False)

    # Step 1B: Load + preprocess + persist clean data.
    report = run_preprocessing(
        raw_csv_path="data/raw/user_data.csv",
        processed_csv_path="data/processed/clean_user_data.csv",
        report_path="results/preprocessing_report.txt",
    )

    print("Data step completed successfully.")
    print(report)


if __name__ == "__main__":
    main()
