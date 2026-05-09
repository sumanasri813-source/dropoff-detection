"""
Pydantic-based input validation models for API requests.
Provides type safety, validation, and automatic documentation.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class PredictionInputModel(BaseModel):
    """Validated input for single prediction request."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "days_signup_age": 250.0,
            "recency_days": 45.0,
            "frequency_total": 9.0,
            "session_duration_avg": 6.5,
            "feature_count_used": 2.0,
            "device_type": "mobile",
            "os_type": "android",
            "user_segment": "free",
            "region": "north",
        }
    })
    
    # Numeric fields with constraints
    days_signup_age: float = Field(ge=0, le=10000, description="Days since signup")
    recency_days: float = Field(ge=0, le=5000, description="Days since last activity")
    frequency_total: float = Field(ge=0, le=50000, description="Total activity count")
    session_duration_avg: float = Field(ge=0, le=1000, description="Average session duration in minutes")
    feature_count_used: float = Field(ge=0, le=500, description="Number of features used")
    
    # Categorical fields with allowed values
    device_type: Literal["mobile", "desktop", "tablet"] = Field(description="Device type")
    os_type: Literal["windows", "mac", "android", "ios", "linux"] = Field(description="Operating system")
    user_segment: Literal["free", "trial", "premium"] = Field(description="User segment")
    region: Literal["north", "south", "east", "west"] = Field(description="Geographic region")
    
    # Optional external user ID for database linking
    external_user_id: Optional[str] = Field(None, max_length=100, description="External user identifier")
    
    @field_validator("days_signup_age", "recency_days", "frequency_total", "session_duration_avg", "feature_count_used")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Ensure numeric fields are finite numbers."""
        if not isinstance(v, (int, float)) or (isinstance(v, float) and not (-1e308 < v < 1e308)):
            raise ValueError("Value must be a finite number")
        return float(v)


class BatchPredictionInputModel(BaseModel):
    """Validated input for batch predictions."""
    
    predictions: List[PredictionInputModel] = Field(
        ...,
        min_items=1,
        max_items=10000,
        description="List of prediction inputs (max 10,000)"
    )
    return_errors: bool = Field(
        default=True,
        description="Include validation errors in response"
    )


class UserCreateModel(BaseModel):
    """Validated input for user creation."""
    
    external_user_id: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    user_segment: Optional[str] = Field(None, max_length=50)
    device_type: Optional[str] = Field(None, max_length=50)
    os_type: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=50)


class UserUpdateModel(BaseModel):
    """Validated input for user update."""
    
    external_user_id: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    user_segment: Optional[str] = Field(None, max_length=50)
    device_type: Optional[str] = Field(None, max_length=50)
    os_type: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=50)


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    
    status: Literal["healthy", "degraded", "unhealthy"]
    model_loaded: bool
    database_connected: bool
    timestamp: str


class PredictionResponse(BaseModel):
    """Prediction response model."""
    
    dropoff_probability: float = Field(ge=0, le=1, description="Probability of user dropoff")
    predicted_label: int = Field(ge=0, le=1, description="Binary prediction (0=stay, 1=dropoff)")
    risk_level: Literal["low", "medium", "high"]
    threshold_used: float
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: Dict[str, str]
    request_id: Optional[str] = None
    details: Optional[Dict[str, str]] = None


# O(1) model validation - Pydantic validates on instantiation
def validate_input(data: Dict, model_class: type[BaseModel]) -> BaseModel:
    """
    Validate input data against Pydantic model.
    O(1) - constant time validation with cached schemas.
    """
    try:
        return model_class(**data)
    except Exception as e:
        from src.utils.errors import ValidationError
        raise ValidationError(
            f"Input validation failed: {str(e)}",
            details={"validation_error": str(e)}
        )
