"""Shared API response helpers."""
from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_DETAIL_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "encryption_key",
    "jwt",
    "password",
    "secret",
    "token",
}


def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Return the standard successful API envelope used by the frontend."""
    payload: Dict[str, Any] = {
        "success": True,
        "data": jsonable_encoder(data),
    }
    if message:
        payload["message"] = message
    return payload


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_DETAIL_KEYS)


def _redact_sensitive_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_VALUE
                if _is_sensitive_key(str(key))
                else _redact_sensitive_details(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive_details(item) for item in value]
    return value


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the standard API error envelope used by the frontend."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(
                _redact_sensitive_details(details or {})
            ),
        },
    }
