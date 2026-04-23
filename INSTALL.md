# TechDoc Plugin 설치 가이드

> **v0.1.0** — 로컬 배포 아카이브 기반 설치

3가지 설치 방식 중 선택하세요. 대부분의 경우 **방법 1**이 가장 간단합니다.

---

## 방법 1: ZIP 아카이브 수동 설치 (권장)

배포 ZIP 파일 (`techdoc-plugin-v0.1.0.zip`)을 받았다면:

### 1단계: 압축 해제

**Windows (PowerShell)**:
```powershell
Expand-Archive techdoc-plugin-v0.1.0.zip -DestinationPath $HOME\.claude\plugins\
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/plugins
unzip techdoc-plugin-v0.1.0.zip -d ~/.claude/plugins/
```

압축 해제 후 경로: `~/.claude/plugins/techdoc-plugin/`

### 2단계: SHA-256 체크섬 검증 (선택)

```bash
# macOS / Linux
shasum -a 256 -c techdoc-plugin-v0.1.0.zip.sha256

# Windows (PowerShell)
Get-FileHash techdoc-plugin-v0.1.0.zip -Algorithm SHA256
# 결과를 .sha256 파일 값과 비교
```

### 3단계: Claude Code에 등록

Claude Code 실행 중에:

```
/plugin marketplace add ~/.claude/plugins/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
/reload-plugins
```

### 4단계: Python 의존성 설치

```bash
cd ~/.claude/plugins/techdoc-plugin
pip install -e .

# PDF/DOCX 필요 시:
pip install -e ".[pdf,docx]"
playwright install chromium
```

### 5단계: 환경 진단

```
/techdoc-doctor
```

15개 항목이 모두 `[OK]`면 완료. `[FAIL]` 있으면 수정 제안 따라 실행.

---

## 방법 2: 로컬 디렉토리 직접 참조 (개발·테스트용)

이미 plugin 소스를 클론·압축해제했다면 경로만 등록:

```
/plugin marketplace add /path/to/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
```

이후 Python 설치·환경 진단은 방법 1의 4~5단계와 동일.

### 개발자 모드 (임시 실행)

```bash
claude --plugin-dir /path/to/techdoc-plugin
```

세션 종료 시 자동 언로드. 설치 영속 아님. 빠른 테스트용.

---

## 방법 3: Git 저장소 (팀 공유)

조직 내부 Git 저장소에 publish한 경우:

```
/plugin marketplace add github.com/<org>/techdoc-plugin
/plugin install techdoc-plugin@techdoc-marketplace
```

**또는** `.claude/settings.json`에 팀용 마켓플레이스 자동 등록:

```json
{
  "extraKnownMarketplaces": {
    "techdoc-team": {
      "source": {
        "source": "github",
        "repo": "<org>/techdoc-plugin"
      }
    }
  }
}
```

이 파일을 레포에 커밋하면 팀원이 프로젝트 클론 후 즉시 인식.

---

## 설치 후 검증 (모든 방법 공통)

### 1. 슬래시 커맨드 인식

```
/help
```

`/techdoc`, `/techdoc-doctor`, `/techdoc-outline` 등이 목록에 나오면 정상.

### 2. 환경 진단

```
/techdoc-doctor
```

**기대 결과**: 15개 항목 모두 `[OK]`.

### 3. 미니 테스트

```
/techdoc-demo
```

3분 이내에 fixtures 기반 미니 보고서 생성 (HTML + MD).

---

## 업데이트

### 새 버전 ZIP을 받은 경우

```bash
# 기존 plugin 제거
/plugin uninstall techdoc-plugin

# 디렉토리 삭제
rm -rf ~/.claude/plugins/techdoc-plugin

# 새 버전 압축 해제 후 방법 1의 1~5단계 재실행
```

### Git 기반인 경우

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

### `/plugin` 커맨드가 인식되지 않음
Claude Code 버전이 구버전일 수 있음. `claude --version` 확인 후 최신 버전으로 업그레이드.

### `/techdoc-doctor`가 `techdoc_core: [FAIL]` 보고
Python 의존성 설치 누락. 방법 1의 **4단계** 재실행:
```bash
cd ~/.claude/plugins/techdoc-plugin && pip install -e .
```

### 한글 폰트 경고
```
Korean font  [WARN]  no Korean font
```
matplotlib 차트의 한글 표시를 위해 Pretendard 또는 NanumGothic 설치:
- **Windows**: 시스템 기본 Malgun Gothic 자동 인식 (이 경고가 나오면 matplotlib 재설치)
- **macOS**: `brew install font-nanum-gothic`
- **Linux**: `sudo apt install fonts-nanum`

### playwright 관련 오류
PDF 생성 시만 필요. HTML + MD 출력은 playwright 없이도 동작:
```
/techdoc "제목" --toc ... --formats html,md
```

PDF가 꼭 필요하면:
```bash
pip install -e ".[pdf]"
playwright install chromium  # ~300MB 다운로드
```

### WebSearch 제한
Claude Code 세션의 `WebSearch` 도구 사용. API 키 불필요 (세션 자격증명). 구독 플랜의 도구 쿼터 한도 내에서 동작.

### 플러그인 버전 확인
```
/plugin list
```

또는 직접:
```bash
python -c "import techdoc_core; print(techdoc_core.__version__)"
```

---

## 체크섬·서명

모든 배포 ZIP에 `.sha256` 체크섬 파일이 함께 제공됩니다:

```
techdoc-plugin-v0.1.0.zip
techdoc-plugin-v0.1.0.zip.sha256
techdoc-plugin-v0.1.0.metadata.json
```

`metadata.json`에는 파일 수·크기·압축률·SHA-256이 포함됩니다. 배포 자동화 시 metadata를 읽어 버전 판정 가능.

---

## 지원

- 설치 문제: `/techdoc-doctor` 출력 첨부
- 버그: GitHub Issues (해당 저장소) 또는 조직 내부 채널
- 문서: [README.md](README.md), [CHANGELOG.md](CHANGELOG.md), [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md)
