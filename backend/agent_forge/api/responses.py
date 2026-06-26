"""Shared API response helpers."""
from typing import Any, Dict, Optional

from fastapi.encoders import jsonable_encoder


def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Return the standard successful API envelope used by the frontend."""
    payload: Dict[str, Any] = {
        "success": True,
        "data": jsonable_encoder(data),
    }
    if message:
        payload["message"] = message
    return payload
