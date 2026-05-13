---
description: Step 2 - researcher subagent × 3 병렬로 5라운드 본문 자료 조사. 대학·기업·연구기관 77% 가중, 섹션 범위 분할 (A/B/C)
allowed-tools: Bash, Read, Write, Agent
argument-hint: "--outline FILE [--type 기술보고서|연구보고서|사업계획서|정책보고서|교육자료] [--depth quick|standard|deep] [--ref file:...|url:...|site:...] [-o OUTPUT]"
---

# /techdoc-research — 자료 조사 (5라운드)

3개 researcher subagent를 **병렬**로 호출해 섹션 범위를 나눠 조사합니다.

## 입력 분석
`$ARGUMENTS`에서 추출:
- `--outline FILE` (필수, draft_outline.json 경로)
- `--type <문서유형>` (기본: 기술보고서)
- `--depth quick|standard|deep` (기본: standard)
- `--ref file:path | url:URL | site:URL` (옵션, 사용자 참고자료)
- `-o DIR` (기본: `./output`)

## 섹션 범위 분할 규칙

outline의 섹션 개수 N에 따라 분할:
- N ≤ 3: researcher 1개만 호출 (분할 의미 없음)
- 4 ≤ N ≤ 6: 2개 (A, B)
- N ≥ 7: 3개 (A: 1~4, B: 5~7, C: 8~N)

섹션 ID 리스트를 각 researcher에 정확히 전달 (중복·누락 금지).

## 실행 순서

### 1. Outline 로드 + 문서 유형 확인
```bash
python -c "
import json
d = json.load(open('$OUTLINE_FILE', encoding='utf-8'))
print(f'sections={len(d[\"sections\"])}, type={d.get(\"document_type\", \"기술보고서\")}')
"
```

### 2. 사용자 참고자료 검증 (선택)
`--ref file:path.pdf` 제공 시 `scripts/doctor.py`처럼 사전 검증:
- 경로 화이트리스트 (CWD 외부 거부 `TECHDOC-E070`)
- 50MB 상한 (`TECHDOC-E071`)
- `..` 경로 시퀀스 거부

### 2.5. Write 권한 사전 점검 (F6, v1.1.1+)

researcher subagent 호출 전에 `output/` 디렉토리에 실제 쓸 수 있는지 확인:

```bash
python -m scripts.preflight "$OUTPUT_DIR"
```

비정상 종료(exit 1)면 **researcher를 호출하지 말고 즉시 중단** 후 사용자에게 안내:

```
[/techdoc-research 중단] Write 권한 사전 점검 실패.

원인: <preflight 출력>
조치:
  1. 현재 디렉토리 권한 확인: ls -ld "$OUTPUT_DIR"
  2. Windows: 디렉토리 속성 → 보안 탭에서 현재 사용자에게 쓰기 권한 부여
  3. POSIX: chmod +w "$OUTPUT_DIR"
  4. settings.json의 permissions.allow에 Write 추가됐는지 확인

권한 확보 후 같은 명령으로 재실행하세요.
```

이 단계는 F6 사고(researcher가 권한 거부 후 메인 세션이 generator로 우회하여 `KeyRef_overlap_*` 중복 산출)를 사전 차단합니다.

### 3. Researcher × 3 병렬 호출 (한 메시지에 모두 포함)

**중요**: 한 메시지 안에 Agent tool을 3번 호출해야 실제 병렬 실행됨. 순차로 하면 시간 3배 소요.

각 호출 프롬프트 예시:
```
[researcher-A]
섹션 그룹: A
담당 섹션: [{id: "1.1", title: "...", subtopics: [...], analysis_tags: [...]}, ... 섹션 1~4]
문서 유형: 기술보고서
출력: ./output/research_round_A.json
모드: body
```

각 subagent는 5라운드 × 섹션당 21회 검색 수행.

### 4. 병합
3개 `research_round_{A,B,C}.json` 완료 후:
```bash
python -m scripts.merge_research -i "$OUTPUT_DIR" -o "$OUTPUT_DIR/merged_research.json"
```

### 5. Reference List 생성
```bash
python -m scripts.build_reflist \
  --keyref "$OUTPUT_DIR/KeyRef" \
  --type "$DOC_TYPE" \
  -o "$OUTPUT_DIR"
```

## Depth 옵션별 차등

| depth | researcher별 검색 횟수 | 섹션당 REF 목표 | 소요 시간 |
|---|---|---|---|
| quick | 11회 (라운드 1~2만) | 10 | 3~5분 |
| standard | 21회 (5라운드 전체) | 18~22 | 5~8분 |
| deep | 30회 (라운드 추가 + 재확장) | 25~30 | 10~15분 |

subagent 프롬프트에 `depth` 값 전달.

## 카테고리 커버리지 보고

merge 결과에서 카테고리 비율 표시:
```
총 REF: 87건 (목표 85건)
- 학술 (대학): 31건 (35.6%, 목표 30)
- 기업 R&D: 19건 (21.8%, 목표 20)
- 전문연구기관: 14건 (16.1%, 목표 15)
- 기타: 23건
- 해외 비율: 52% (목표 50%+)
- 합계 77% aspirational: ✓ 달성 (대학+기업R&D+연구기관 = 73.5%)
```

77% 미달이어도 FAIL 아님 (aspirational).

## 실행 시간·제약

- Agent × 3 병렬 시 **5~8분** (standard depth)
- 컨텍스트 보호: 상세 검색 결과는 디스크에 저장, 메인 세션엔 요약만
- 중단 시 `/techdoc-research --outline ... --resume` 으로 부분 재개 가능 (TODO: 향후 구현)

## 출력 요약

```
[techdoc-research 완료] (6분 42초)
- Researcher A (섹션 1~4): REF 34건
- Researcher B (섹션 5~7): REF 28건
- Researcher C (섹션 8~10): REF 25건
- 병합 후: 87건 (중복 dedup 5건 제거)
- 카테고리: 학술 31, 기업R&D 19, 연구기관 14, 기타 23
- 해외 비율: 52%, 영문 쿼리 50건 (55%)

파일:
  $OUTPUT_DIR/research_round_A.json, _B.json, _C.json
  $OUTPUT_DIR/merged_research.json
  $OUTPUT_DIR/reference_list.json
  $OUTPUT_DIR/KeyRef/001~087_*.md

다음 단계: /techdoc-write --outline ... --refs "$OUTPUT_DIR/reference_list.json"
```
