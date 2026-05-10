"""
Security Hardening Middleware

Adds essential HTTP security headers to every API response.
Protects against XSS, clickjacking, MIME sniffing, and other common attacks.
"""

from __future__ import annotations

from flask import Flask
from src.utils.logger import get_logger

logger = get_logger("security")


def init_security_headers(app: Flask) -> None:
    """
    Register security headers middleware.
    
    Headers applied:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Enables browser XSS filter
    - Strict-Transport-Security: Enforces HTTPS
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser feature access
    """
    
    @app.after_request
    def add_security_headers(response):
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking (allow same origin for Swagger UI)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # Enable browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Force HTTPS (1 year max-age)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # Content Security Policy - restrict resource loading
        # Relaxed for Swagger UI to work properly
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        
        # Limit referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Restrict access to browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        
        # Remove server identification header
        response.headers.pop("Server", None)
        
        return response
    
    logger.info("security_headers_initialized")
