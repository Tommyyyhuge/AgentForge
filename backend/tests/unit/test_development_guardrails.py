from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read_repo_file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def makefile_target_body(target: str) -> list[str]:
    lines = read_repo_file("Makefile").splitlines()
    start = lines.index(f"{target}:") + 1
    body: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith("\t") and line.endswith(":"):
            break
        if line.startswith("\t"):
            body.append(line.strip())
    return body


def test_claude_points_to_agents_without_duplicating_rules():
    claude = read_repo_file("CLAUDE.md")

    assert "`AGENTS.md` 是本仓库的权威开发规范" in claude
    assert len(claude.splitlines()) <= 20


def test_make_check_matches_documented_quality_gates():
    body = makefile_target_body("check")

    assert "make format" not in body
    assert "cd backend && python -m pytest" in body
    assert "cd backend && python -m mypy agent_forge --ignore-missing-imports" in body
    assert "cd backend && python -m flake8 agent_forge" in body
    assert "cd frontend && npm run lint" in body
    assert "cd frontend && npm run test" in body
    assert "cd frontend && npm run build" in body
