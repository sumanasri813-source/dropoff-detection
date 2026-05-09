from src.data.generate_synthetic_data import main as generate_data_main
from src.evaluation.evaluate_model import main as evaluate_main
from src.features.build_features import main as build_features_main
from src.models.train_model import main as train_main
from src.utils.config_loader import get_runtime_environment, load_config


if __name__ == "__main__":
    env_name = get_runtime_environment()
    cfg = load_config("config.yaml")

    print(f"Runtime environment: {env_name}")
    print(f"Environment config loaded: {cfg.get('runtime', {}).get('environment_config_loaded', False)}")

    print("Step 1/4: Generating synthetic data...")
    generate_data_main()

    print("\nStep 2/4: Building features...")
    build_features_main()

    print("\nStep 3/4: Training model...")
    train_main()

    print("\nStep 4/4: Evaluating model...")
    evaluate_main()

    print("\nPipeline finished successfully.")
