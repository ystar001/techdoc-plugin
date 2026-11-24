"""기존 품질 도구의 측정 코드 — qc 게이트(PLG·VC)와 CLI 래퍼가 같이 쓴다 (v1.11-c Task 3, 설계 D3.5).

- `format_metrics`: `scripts/format_gate.py`의 서식 지표 (PLG-FG-*)
- `doc_metrics`: `scripts/check_quality.py`의 Phase A 지표·self-model 분량 (PLG-CQ-*)
- `card_checks`: `scripts/verify_cards.py`의 카드 완결성 A~E (VC-*)
- `abbr`: `scripts/extract_glossary.py`의 약어·풀이 페어 추출

판정 로직은 옮기기 전과 같다. 기존 CLI는 이 모듈을 불러 같은 결과 계약을 낸다.
"""
