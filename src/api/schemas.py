"""
Pydantic schemas for API request/response validation.
Provides type safety, data validation, and clear API documentation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PredictionRequest(BaseModel):
    """Schema for single user prediction request with input validation."""

    days_signup_age: int = Field(
        ge=30, le=730, description="Days since user signup (30-730)"
    )
    recency_days: int = Field(
        ge=0, le=120, description="Days since last activity (0-120)"
    )
    frequency_total: int = Field(
        ge=0, le=200, description="Total interaction frequency (0-200)"
    )
    session_duration_avg: float = Field(
        ge=1.0, le=60.0, description="Average session duration in minutes (1-60)"
    )
    feature_count_used: int = Field(
        ge=1, le=15, description="Number of features used (1-15)"
    )
    device_type: Literal["mobile", "desktop", "tablet"] = Field(
        description="Device type used"
    )
    os_type: Literal["windows", "mac", "android", "ios", "linux"] = Field(
        description="Operating system type"
    )
    user_segment: Literal["free", "trial", "premium"] = Field(
        description="User subscription segment"
    )
    region: Literal["north", "south", "east", "west"] = Field(
        description="Geographic region"
    )
    user_id: Optional[int] = Field(None, ge=1, description="Optional user ID")

    @field_validator("session_duration_avg")
    @classmethod
    def validate_session_duration(cls, v):
        """Ensure session duration is positive."""
        if v <= 0:
            raise ValueError("session_duration_avg must be positive")
        return round(v, 2)

    class Config:
        """Pydantic config for schema."""

        json_schema_extra = {
            "example": {
                "days_signup_age": 180,
                "recency_days": 15,
                "frequency_total": 45,
                "session_duration_avg": 12.5,
                "feature_count_used": 8,
                "device_type": "desktop",
                "os_type": "windows",
                "user_segment": "premium",
                "region": "north",
                "user_id": 123,
            }
        }


class BatchPredictionRequest(BaseModel):
    """Schema for batch prediction request."""

    predictions: List[PredictionRequest] = Field(
        ..., min_items=1, max_items=1000, description="List of predictions (1-1000)"
    )
    return_probabilities: bool = Field(
        True, description="Return raw probabilities in response"
    )

    class Config:
        """Pydantic config for schema."""

        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "days_signup_age": 180,
                        "recency_days": 15,
                        "frequency_total": 45,
                        "session_duration_avg": 12.5,
                        "feature_count_used": 8,
                        "device_type": "desktop",
                        "os_type": "windows",
                        "user_segment": "premium",
                        "region": "north",
                    }
                ],
                "return_probabilities": True,
            }
        }


class PredictionResponse(BaseModel):
    """Schema for prediction response."""

    prediction: int = Field(description="Predicted label (0=retain, 1=dropoff)")
    probability: float = Field(
        description="Probability of dropoff (0.0-1.0)"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk level classification"
    )
    confidence: float = Field(description="Model confidence score")
    request_id: str = Field(description="Unique request identifier")

    class Config:
        """Pydantic config for schema."""

        json_schema_extra = {
            "example": {
                "prediction": 0,
                "probability": 0.25,
                "risk_level": "low",
                "confidence": 0.92,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="System health status"
    )
    model_status: Literal["loaded", "not_loaded", "error"] = Field(
        description="Model loading status"
    )
    database_status: Literal["connected", "disconnected", "error"] = Field(
        description="Database connection status"
    )
    timestamp: str = Field(description="ISO 8601 timestamp")
    api_version: str = Field(description="API version")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str = Field(description="Error message")
    error_code: str = Field(description="Error code")
    request_id: str = Field(description="Unique request identifier")
    details: Optional[dict] = Field(None, description="Additional error details")

    class Config:
        """Pydantic config for schema."""

        json_schema_extra = {
            "example": {
                "error": "Invalid input data",
                "error_code": "VALIDATION_ERROR",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {"field": "recency_days", "message": "Must be 0-120"},
            }
        }
