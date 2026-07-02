from datetime import datetime, timezone

from agent_forge.api.routes.tasks import _orm_step_to_response
from agent_forge.database.models import StepORM


def test_step_response_includes_stable_step_number():
    step = StepORM(
        id="step-3",
        task_id="task-1",
        agent_id="agent-reviewer",
        agent_role="reviewer",
        step_number=3,
        step_type="final",
        content="Review final output",
        timestamp=datetime(2026, 6, 26, 1, 3, tzinfo=timezone.utc),
    )

    response = _orm_step_to_response(step)

    assert response.model_dump()["step_number"] == 3
