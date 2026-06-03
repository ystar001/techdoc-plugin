"""project 마커 동작·컨벤션 회귀 (findings F23).

자식 프로젝트가 plugin tests/를 복사·재사용할 때, 프로젝트 특화 테스트가
`@pytest.mark.project`로 표시되어 `pytest -m "not project"`로 skip되는지 검증한다.
"""

import re
from pathlib import Path

import pytest


@pytest.mark.project
def test_marker_example_project_specific():
    """프로젝트 특화 검증 예시 — 신규 프로젝트에서 `-m "not project"`로 skip."""
    assert True


def test_project_marker_is_registered():
    # pyproject.toml에 등록돼 있으면 --strict-markers에서도 경고 없음.
    # 주의: 본 플러그인은 Python 3.10 지원이라 tomllib(3.11+) 대신
    # pyproject.toml을 텍스트로 읽어 markers 항목에 'project' 등록을 확인한다.
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    # [tool.pytest.ini_options]의 markers 배열 안에 "project: ..." 항목이 있어야 함
    assert '"project:' in pyproject or "'project:" in pyproject
    # markers 키 자체도 존재
    assert re.search(r"^\s*markers\s*=", pyproject, re.MULTILINE)
