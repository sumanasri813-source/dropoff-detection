CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY,
    external_user_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    user_segment VARCHAR(50),
    device_type VARCHAR(50),
    os_type VARCHAR(50),
    region VARCHAR(50),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_records (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    request_id VARCHAR(64),
    dropoff_probability DOUBLE PRECISION NOT NULL,
    predicted_label INTEGER NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    threshold_used DOUBLE PRECISION NOT NULL,
    payload_json TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_profiles(id)
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_external_user_id
ON user_profiles (external_user_id);

CREATE INDEX IF NOT EXISTS idx_prediction_records_user_id
ON prediction_records (user_id);

CREATE INDEX IF NOT EXISTS idx_prediction_records_request_id
ON prediction_records (request_id);

CREATE INDEX IF NOT EXISTS idx_prediction_records_created_at
ON prediction_records (created_at);
