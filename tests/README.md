# tests/ — 테스트 컨벤션 (재사용성)

자식 프로젝트가 본 plugin의 `tests/`를 복사·재사용할 수 있도록, 테스트를 두 부류로 구분한다. (findings F23)

## 1. 재사용 테스트 (기본)

`tests/fixtures`·`conftest.py` fixtures 기반으로 **프로젝트 데이터에 비의존**하는 테스트.
자식 프로젝트가 그대로 복사·실행할 수 있다. 별도 마커를 붙이지 않는다.

## 2. 프로젝트 특화 테스트

특정 산출물(페이지 수·`reference_list` 내용)·도메인 약어처럼 **한 프로젝트의 데이터에 결합**되는
검증은 `@pytest.mark.project`로 표시한다.

```python
import pytest


@pytest.mark.project
def test_some_project_specific_thing():
    ...
```

이 마커는 `pyproject.toml`의 `[tool.pytest.ini_options]` `markers`에 등록되어 있어
`pytest --strict-markers`에서도 경고가 발생하지 않는다.

## 3. 실행 방법

| 목적 | 명령 |
|---|---|
| 전체 (재사용 + 프로젝트 특화) | `pytest` |
| 코어만 (재사용 테스트만, 신규 프로젝트 기본) | `pytest -m "not project"` |
| 프로젝트 특화만 | `pytest -m "project"` |

신규 프로젝트는 plugin 테스트를 복사한 직후 `pytest -m "not project"`로 코어 회귀만 돌리면
프로젝트 데이터가 아직 없어도 green을 유지할 수 있다.

## 예시

`tests/test_marker_convention.py::test_marker_example_project_specific` —
`@pytest.mark.project` 사용 예시(신규 프로젝트에서 `-m "not project"`로 skip).
