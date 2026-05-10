"""
CORS (Cross-Origin Resource Sharing) Configuration

Controls which external domains can make API requests.
Essential for security when the Streamlit frontend and Flask API 
are hosted on different domains.
"""

from __future__ import annotations

import os
from typing import List

from flask import Flask, request, make_response
from src.utils.logger import get_logger

logger = get_logger("cors")


def get_allowed_origins() -> List[str]:
    """
    Load allowed CORS origins from environment or defaults.
    
    Set CORS_ORIGINS env var as comma-separated list:
      CORS_ORIGINS=https://my-app.streamlit.app,https://mysite.com
    """
    env_origins = os.getenv("CORS_ORIGINS", "").strip()
    
    if env_origins:
        origins = [o.strip() for o in env_origins.split(",") if o.strip()]
    else:
        # Default: allow Streamlit Cloud and localhost for development
        origins = [
            "https://sumanasri813-source-dropoff-detection.streamlit.app",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:3000",
        ]
    
    return origins


def init_cors(app: Flask) -> None:
    """
    Register CORS middleware on the Flask app.
    
    This handles:
    - Preflight OPTIONS requests automatically
    - Access-Control headers on every response
    - Origin validation against whitelist
    """
    allowed_origins = get_allowed_origins()
    
    @app.after_request
    def apply_cors_headers(response):
        origin = request.headers.get("Origin", "")
        
        # Check if origin is in our whitelist
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        # Standard CORS headers
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-API-Key, X-Request-ID"
        )
        response.headers["Access-Control-Max-Age"] = "600"  # Cache preflight for 10 minutes
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    @app.before_request
    def handle_preflight():
        """Automatically respond to OPTIONS preflight requests."""
        if request.method == "OPTIONS":
            response = make_response()
            origin = request.headers.get("Origin", "")
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-API-Key, X-Request-ID"
            )
            response.headers["Access-Control-Max-Age"] = "600"
            response.status_code = 204
            return response
    
    logger.info("cors_initialized", allowed_origins=allowed_origins)
