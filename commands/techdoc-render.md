---
description: Step 12 - document_final.json → HTML + PDF + DOCX + MD 렌더링 (카드·별첨 포함)
allowed-tools: Bash, Read
argument-hint: "--input FILE [--refs FILE] [--type DESIGN] [--formats html,pdf,docx,md] [-o OUTPUT] | --tree --cards-dir DIR [--routing-config FILE] [--with-series-index] | --webbook --cards-dir DIR [--routing-config FILE] [--title TEXT]"
---

# /techdoc-render — 4종 출력 생성

`scripts/render.py` 오케스트레이터가 수행. HTML을 마스터로 PDF·DOCX·MD 병렬 생성. 카드·별첨 자동 포함.

## 입력 분석
- `--input FILE` (필수, document_final.json 또는 document_draft.json)
- `--refs FILE` (옵션, 참고문헌·각주 생성용)
- `--type DESIGN` (옵션, 자동 판별 안 할 때 명시)
- `--formats LIST` (기본: `html,pdf,docx,md`)
- `-o DIR` (기본: `./output`)

### 트리 디렉토리 출력 (--tree, F15·F17)
- `--tree` — 단일파일 대신 config 기반 트리 디렉토리 출력 (`--input` 대신 `--cards-dir` 사용)
- `--cards-dir DIR` — 입력 카드 JSON 디렉토리 (`*_card.json`)
- `--routing-config FILE` — 카드 ID → Part 라우팅 config (기본 `DEFAULT_ROUTING`; 프로젝트별 교체로 도메인 Part·카테고리·시리즈 라벨 지정)
- `--with-series-index` — 시리즈 폴더 INDEX 강제 (기본: F17 — 단일 카드 시리즈는 INDEX 생략)

출력: `Part-*/` 디렉토리 + (2+ 카드) 시리즈 하위폴더 + 부분별 INDEX + 최상위 표지·TOC INDEX. split 카드(L1/L2/L3)는 부모당 1파일 병합.

### 웹북 출력 (--webbook, F52)
- `--webbook` — 카드 디렉토리를 file:// 정적 **다중 페이지 HTML 웹북**으로 출력 (`--input` 대신 `--cards-dir` 사용)
- `--cards-dir DIR` — 입력 카드 JSON 디렉토리 (`*_card.json`)
- `--routing-config FILE` — Part 라우팅 config (트리와 동일)
- `--title TEXT` — 표지 제목 (기본 "기술보고서")

출력: `index.html`(표지+전체 목차) + `Part-*/<card_id>.html`(Part별 카드/병합 페이지) + `assets/webbook.css`. 수식 `$$…$$`·`$…$` 보호 후 MathJax 렌더(F38), fenced ```mermaid → `<pre class="mermaid">` `<br/>` 보존(F48), 2단 중첩 리스트(F26). 단일파일 render와 독립(opt-in).

## 실행

```bash
python -m scripts.render \
  --input "$INPUT" \
  ${REFS:+--refs "$REFS"} \
  ${DESIGN:+--type "$DESIGN"} \
  --formats "$FORMATS" \
  -o "$OUTPUT_DIR"
```

## 출력

파일명 규칙: `<제목_정리>_<YYYYMMDDhhmm>.<ext>`

예시:
- `스마트농업기술보고서_202604231430.html` (마스터, 카드+별첨 포함)
- `스마트농업기술보고서_202604231430.pdf`
- `스마트농업기술보고서_202604231430.docx`
- `스마트농업기술보고서_202604231430.md`

## 의존성 선택적

- **playwright 없음** → PDF 스킵, 경고만
- **python-docx 없음** → DOCX 스킵, 경고만
- HTML + MD는 항상 생성 (core 의존성만 필요)

## 별첨·수식 렌더링

- 별첨 내 MathJax LaTeX → HTML에 CDN 로더 자동 주입
- Mermaid 다이어그램 → HTML에 CDN 로더 자동 주입
- PDF 변환 시 playwright가 페이지 로드하며 수식·다이어그램 확정 렌더

## 실행 시간

- HTML: 즉시 (< 5초)
- MD: 즉시 (< 3초)
- PDF: 30초~2분 (페이지 수에 비례, MathJax·Mermaid 포함 시 증가)
- DOCX: 10~30초

## 출력 요약

```
[techdoc-render 완료] (1분 42초)
- HTML: 스마트농업기술보고서_202604231430.html (1.2 MB, 추정 287페이지)
- PDF:  스마트농업기술보고서_202604231430.pdf  (4.8 MB)
- DOCX: 스마트농업기술보고서_202604231430.docx (2.1 MB)
- MD:   스마트농업기술보고서_202604231430.md   (340 KB)

카드: 72개 (기술 38, 프로젝트 22, 제품 12)
별첨: 5개 (기술 3 + 프로젝트 2, 합 142p)
차트: 18개 (본문 10 + 별첨 8)

파일 위치: $OUTPUT_DIR/
```
