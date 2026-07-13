"""update_plugin stdout UTF-8 가드 테스트 (v1.9.0 워크스트림 G — F53).

update_plugin.py는 한글·em-dash를 다수 print하나 stdout 인코딩 가드가 없어
cp949 등 비-UTF-8 콘솔에서 UnicodeEncodeError로 업데이트 중 크래시했다.
"""
import io
import sys

from scripts import update_plugin


def test_ensure_utf8_stdout_rewraps_non_utf8(monkeypatch):
    """F53 — 비-UTF-8 stdout을 UTF-8로 재바인딩, 한글·em-dash 출력이 안 터진다."""
    buf = io.BytesIO()
    fake = io.TextIOWrapper(buf, encoding="ascii")  # 한글 인코딩 불가 (cp949 대역)
    monkeypatch.setattr(sys, "stdout", fake)

    update_plugin._ensure_utf8_stdout()

    assert sys.stdout.encoding.lower() == "utf-8"
    sys.stdout.write("한글 제목 — 최신 버전")  # ascii였다면 UnicodeEncodeError
    sys.stdout.flush()


def test_ensure_utf8_stdout_noop_when_already_utf8(monkeypatch):
    """이미 UTF-8이면 재바인딩하지 않는다(동일 객체 유지)."""
    buf = io.BytesIO()
    fake = io.TextIOWrapper(buf, encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", fake)

    update_plugin._ensure_utf8_stdout()

    assert sys.stdout is fake
