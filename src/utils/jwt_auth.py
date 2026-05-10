"""
JWT Authentication Module

Provides JSON Web Token (JWT) based authentication for the API.
Supports token generation, validation, and refresh mechanisms.
"""

from __future__ import annotations

import os
import time
import hmac
import hashlib
import base64
import json
from typing import Any, Dict, Optional, Tuple
from functools import wraps

from flask import jsonify, request, g

from src.utils.logger import get_logger

logger = get_logger("jwt_auth")

# ── Configuration ─────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "dropoff-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = int(os.getenv("JWT_EXPIRY_SECONDS", "3600"))  # 1 hour default
JWT_REFRESH_EXPIRY_SECONDS = int(os.getenv("JWT_REFRESH_EXPIRY_SECONDS", "86400"))  # 24 hours

# Demo users (in production, use a proper database)
DEMO_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "name": "Admin User",
    },
    "analyst": {
        "password_hash": hashlib.sha256("analyst123".encode()).hexdigest(),
        "role": "analyst",
        "name": "Data Analyst",
    },
    "viewer": {
        "password_hash": hashlib.sha256("viewer123".encode()).hexdigest(),
        "role": "viewer",
        "name": "Dashboard Viewer",
    },
}

# Role-based access control permissions
ROLE_PERMISSIONS = {
    "admin": ["predict", "predict_batch", "users", "monitor", "health", "model_info", "admin"],
    "analyst": ["predict", "predict_batch", "monitor", "health", "model_info"],
    "viewer": ["health", "model_info"],
}


def _base64url_encode(data: bytes) -> str:
    """URL-safe Base64 encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    """URL-safe Base64 decoding with padding restoration."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt_token(user_id: str, role: str, expiry_seconds: int = JWT_EXPIRY_SECONDS) -> str:
    """
    Generate a signed JWT token.
    
    Args:
        user_id: Username or user identifier
        role: User role (admin, analyst, viewer)
        expiry_seconds: Token validity duration in seconds
    
    Returns:
        Signed JWT token string
    """
    now = int(time.time())
    
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expiry_seconds,
        "iss": "dropoff-detection-api",
    }
    
    # Encode header and payload
    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))
    
    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(JWT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)
    
    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    logger.info("jwt_token_created", user_id=user_id, role=role, expires_in=expiry_seconds)
    return token


def verify_jwt_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Tuple of (is_valid, payload_dict or None)
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False, None
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = _base64url_decode(signature_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("jwt_invalid_signature")
            return False, None
        
        # Decode payload
        payload = json.loads(_base64url_decode(payload_b64))
        
        # Check expiry
        if payload.get("exp", 0) < time.time():
            logger.warning("jwt_token_expired", user_id=payload.get("sub"))
            return False, None
        
        return True, payload
    
    except Exception as exc:
        logger.error("jwt_verification_failed", error=str(exc))
        return False, None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user against the demo user store.
    
    Args:
        username: User login name
        password: Plain text password
    
    Returns:
        User dict with tokens if authenticated, None otherwise
    """
    user = DEMO_USERS.get(username)
    if not user:
        logger.warning("auth_user_not_found", username=username)
        return None
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(user["password_hash"], password_hash):
        logger.warning("auth_invalid_password", username=username)
        return None
    
    # Generate access and refresh tokens
    access_token = create_jwt_token(username, user["role"])
    refresh_token = create_jwt_token(username, user["role"], JWT_REFRESH_EXPIRY_SECONDS)
    
    logger.info("auth_success", username=username, role=user["role"])
    
    return {
        "user_id": username,
        "name": user["name"],
        "role": user["role"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": JWT_EXPIRY_SECONDS,
    }


def require_jwt(allowed_roles: Optional[list] = None):
    """
    Decorator to protect routes with JWT authentication.
    
    Args:
        allowed_roles: List of roles permitted to access this route.
                       None means any authenticated user.
    
    Usage:
        @app.route("/admin")
        @require_jwt(allowed_roles=["admin"])
        def admin_panel():
            ...
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                return jsonify({
                    "error": "Missing or invalid Authorization header. Use: Bearer <token>",
                    "code": "AUTH_MISSING",
                }), 401
            
            token = auth_header[7:].strip()
            is_valid, payload = verify_jwt_token(token)
            
            if not is_valid:
                return jsonify({
                    "error": "Invalid or expired JWT token.",
                    "code": "AUTH_INVALID",
                }), 401
            
            # Check role-based access
            user_role = payload.get("role", "")
            if allowed_roles and user_role not in allowed_roles:
                return jsonify({
                    "error": f"Insufficient permissions. Required roles: {allowed_roles}",
                    "code": "AUTH_FORBIDDEN",
                }), 403
            
            # Attach user context to request
            g.jwt_user = payload.get("sub", "")
            g.jwt_role = user_role
            
            return view_fn(*args, **kwargs)
        
        return wrapped
    return decorator
