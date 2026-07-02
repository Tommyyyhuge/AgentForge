import json

import pytest
from fastapi import HTTPException

from agent_forge.api.responses import error_response, success_response
from agent_forge.core.error_handler import AppException, ErrorCode
from main import app_exception_handler, http_exception_handler


def _json_response_body(response):
    return json.loads(response.body.decode("utf-8"))


def test_success_response_uses_standard_envelope():
    response = success_response({"id": "task-1"}, message="Created")

    assert response == {
        "success": True,
        "data": {"id": "task-1"},
        "message": "Created",
    }


def test_error_response_uses_standard_envelope():
    response = error_response(
        code="TASK_NOT_FOUND",
        message="Task was not found.",
        details={"task_id": "task-1"},
    )

    assert response == {
        "success": False,
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "Task was not found.",
            "details": {"task_id": "task-1"},
        },
    }


def test_error_response_redacts_sensitive_detail_fields():
    response = error_response(
        code="PROVIDER_AUTH_FAILED",
        message="Provider authentication failed.",
        details={
            "provider": "deepseek",
            "api_key": "sk-secret",
            "nested": {
                "authorization": "Bearer secret-token",
                "model": "deepseek-chat",
            },
        },
    )

    assert response["error"]["details"] == {
        "provider": "deepseek",
        "api_key": "[REDACTED]",
        "nested": {
            "authorization": "[REDACTED]",
            "model": "deepseek-chat",
        },
    }


@pytest.mark.asyncio
async def test_app_exception_handler_returns_standard_error_envelope():
    response = await app_exception_handler(
        None,
        AppException(
            code=ErrorCode.TASK_NOT_FOUND,
            message="Task was not found.",
            details={"task_id": "task-1"},
            status_code=404,
        ),
    )

    assert response.status_code == 404
    assert _json_response_body(response) == {
        "success": False,
        "error": {
            "code": "40000",
            "message": "Task was not found.",
            "details": {"task_id": "task-1"},
        },
    }


@pytest.mark.asyncio
async def test_http_exception_handler_returns_standard_error_envelope():
    response = await http_exception_handler(
        None,
        HTTPException(status_code=404, detail="Task was not found."),
    )

    assert response.status_code == 404
    assert _json_response_body(response) == {
        "success": False,
        "error": {
            "code": "HTTP_404",
            "message": "Task was not found.",
            "details": {},
        },
    }
