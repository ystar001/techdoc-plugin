# TechDoc Plugin 설치 가이드

> **v0.1.0** — Claude Code 플러그인 설치

---

## 배포 파일 종류 (2종)

| 파일 | 구조 | 용도 |
|---|---|---|
| **`techdoc-plugin-v0.1.0.zip`** (flat, 권장) | 해제 시 바로 `.claude-plugin/` | `/plugin marketplace add` 표준 |
| `techdoc-plugin-v0.1.0-wrapped.zip` | 해제 시 `techdoc-plugin/` 폴더 생성 | 수동 배치용 |

**대부분의 경우 flat 버전을 사용하세요.**

---

## 방법 1: `/plugin marketplace add` (권장)

### 1단계: ZIP 압축 해제

**Windows (PowerShell)**:
```powershell
mkdir $HOME\.claude\plugins\techdoc-plugin
Expand-Archive techdoc-plugin-v0.1.0.zip -DestinationPath $HOME\.claude\plugins\techdoc-plugin
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/plugins/techdoc-plugin
unzip techdoc-plugin-v0.1.0.zip -d ~/.claude/plugins/techdoc-plugin
```

압축 해제 후 구조:
```
~/.claude/plugins/techdoc-plugin/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── agents/
├── commands/
├── prompts/
├── scripts/
├── techdoc_core/
├── pyproject.toml
└── ...
```

### 2단계: SHA-256 검증 (선택)

```bash
shasum -a 256 -c techdoc-plugin-v0.1.0.zip.sha256
# 또는 Windows PowerShell
Get-FileHash techdoc-plugin-v0.1.0.zip -Algorithm SHA256
```

### 3단계: Claude Code에 등록

```
/plugin marketplace add ~/.claude/plugins/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
/reload-plugins
```

### 4단계: Python 의존성 설치

```bash
cd ~/.claude/plugins/techdoc-plugin
pip install -e .

# PDF/DOCX 필요 시
pip install -e ".[pdf,docx]"
playwright install chromium
```

### 5단계: 환경 진단

```
/techdoc-doctor
```

15개 항목 모두 `[OK]`이면 설치 완료.

---

## 방법 2: wrapped ZIP (수동 배치)

ZIP에 `techdoc-plugin/` 래퍼가 포함되어 있어 아무 곳에 해제하면 자동으로 폴더 생성:

```bash
unzip techdoc-plugin-v0.1.0-wrapped.zip -d ~/.claude/plugins/
# → ~/.claude/plugins/techdoc-plugin/ 자동 생성
```

이후 방법 1의 3~5단계 동일.

---

## 방법 3: 개발자 모드 (임시 실행)

```bash
claude --plugin-dir /path/to/techdoc-plugin
```

세션 종료 시 자동 언로드. 설치 영속 아님.

---

## 방법 4: Git 저장소 (팀 공유)

조직 Git 저장소에 publish한 경우:

```
/plugin marketplace add github.com/<org>/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
```

또는 `.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "techdoc-team": {
      "source": {"source": "github", "repo": "<org>/techdoc-plugin"}
    }
  }
}
```

---

## 설치 후 검증

### 슬래시 커맨드 인식
```
/help
```
목록에 `/techdoc`, `/techdoc-doctor`, `/techdoc-outline` 등 11개가 보이면 OK.

### 환경 진단
```
/techdoc-doctor
```
기대 결과: 15개 항목 `[OK]`.

### 3분 smoke test
```
/techdoc-demo
```

---

## 업데이트

### 새 ZIP 받은 경우
```bash
/plugin uninstall techdoc-plugin
rm -rf ~/.claude/plugins/techdoc-plugin
# 방법 1의 1~5단계 재실행
```

### Git 기반
```
/plugin marketplace update techdoc-marketplace
/plugin install techdoc-plugin@techdoc-marketplace
```

---

## 제거

```
/plugin uninstall techdoc-plugin
/plugin marketplace remove techdoc-marketplace
pip uninstall techdoc-plugin
rm -rf ~/.claude/plugins/techdoc-plugin
```

---

## 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `/plugin` 명령 인식 안 됨 | Claude Code 구버전 | `claude --version` 확인 후 최신 업그레이드 |
| `plugin validation fail` | `plugin.json` 스키마 문제 | 본 v0.1.0은 공식 스키마 준수 — 다시 다운로드 |
| `techdoc_core: [FAIL]` (doctor) | Python 의존성 누락 | `cd <plugin-path> && pip install -e .` |
| `Korean font: [WARN]` | matplotlib 한글 폰트 없음 | Pretendard 또는 NanumGothic 설치 |
| PDF 생성 실패 | playwright 없음 | `pip install -e ".[pdf]" && playwright install chromium` |
| 슬래시 커맨드 안 보임 | 등록 누락 | `/reload-plugins` |

---

## 상세 사용법

설치 완료 후 실제 보고서 생성 흐름은 [USAGE.md](USAGE.md) 참조.

## 추가 정보

- 전체 기능 소개: [README.md](README.md)
- 변경 이력: [CHANGELOG.md](CHANGELOG.md)
- 요구사항 ↔ 구현 매핑: [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md)
