# 타깃 사이트 카탈로그 (researcher subagent 필수 참조)

기술연구 품질 강화 (v1.3 — 대학·기업·연구기관 77%)를 위해 `site:` 연산자 쿼리 시 이 카탈로그 우선 사용.

## 대학 (학술 카테고리, 목표 비율 35%)

### 해외
```
site:mit.edu            # MIT (CSAIL, Media Lab 등)
site:stanford.edu       # Stanford
site:berkeley.edu       # UC Berkeley
site:cmu.edu            # Carnegie Mellon
site:eth.ch             # ETH Zurich
site:ox.ac.uk           # Oxford
site:cam.ac.uk          # Cambridge
site:princeton.edu
site:cornell.edu
site:columbia.edu
site:utoronto.ca
site:ntu.edu.sg
site:u-tokyo.ac.jp
site:kyoto-u.ac.jp
```

### 학술 DB
```
site:arxiv.org                 # Preprint
site:ieeexplore.ieee.org       # IEEE 논문·표준
site:dl.acm.org                # ACM
site:link.springer.com         # Springer Nature
site:sciencedirect.com         # Elsevier
site:nature.com                # Nature 계열
site:mdpi.com                  # MDPI Open Access
site:semanticscholar.org
site:openreview.net
```

### 국내 대학
```
site:snu.ac.kr          # 서울대
site:kaist.ac.kr        # KAIST
site:postech.ac.kr      # POSTECH
site:yonsei.ac.kr       # 연세대
site:korea.ac.kr        # 고려대
site:unist.ac.kr        # UNIST
site:gist.ac.kr         # GIST
site:dgist.ac.kr        # DGIST
site:hanyang.ac.kr
site:skku.edu
```

### 국내 학술 DB
```
site:riss.kr                    # 한국교육학술정보원
site:dbpia.co.kr                # DBpia
site:kiss.kstudy.com            # KISS
site:kci.go.kr                  # 한국학술지인용색인
```

## 기업 R&D (목표 비율 24%)

### 해외 (테크 자이언트)
```
site:research.google            # Google Research
site:ai.meta.com                # Meta AI
site:research.ibm.com           # IBM Research
site:microsoft.com/research     # MSR
site:openai.com/research
site:deepmind.google
site:nvidia.com/research
site:research.apple.com
site:aws.amazon.com/blogs/ai    # AWS AI
```

### 특허
```
site:patents.google.com         # Google Patents
site:kipris.or.kr               # 국내 특허
site:patentscope.wipo.int       # WIPO
```

### 국내 기업 R&D
```
site:research.samsung.com       # 삼성 리서치
site:lgresearch.ai              # LG AI Research
site:sk.com/research
site:research.hyundai.com
```

## 전문연구기관 (목표 비율 18%)

### 국내 출연연
```
site:etri.re.kr                 # ETRI (전자통신)
site:kist.re.kr                 # KIST
site:kitech.re.kr               # 한국생산기술연구원
site:krri.re.kr                 # 한국철도기술연구원
site:rda.go.kr                  # 농촌진흥청
site:kict.re.kr                 # 한국건설기술연구원
site:kaeri.re.kr                # 원자력연구원
site:kasi.re.kr                 # 천문연구원
site:kriso.re.kr                # 선박해양플랜트연구소
site:kbsi.re.kr                 # 기초과학지원연구원
```

### 해외 연구기관
```
site:fraunhofer.de              # Fraunhofer (독일)
site:csiro.au                   # CSIRO (호주)
site:riken.jp                   # RIKEN (일본)
site:cea.fr                     # CEA (프랑스)
site:nist.gov                   # NIST (미국)
site:nasa.gov
site:cern.ch
site:tno.nl                     # TNO (네덜란드)
site:vtt.fi                     # VTT (핀란드)
```

## 정부·국제기구 (축소 유지)

### 국제기구
```
site:fao.org                    # 농업·식량
site:oecd.org                   # 경제협력
site:worldbank.org              # 세계은행
site:who.int                    # WHO
site:unesco.org
site:iea.org                    # 국제에너지기구
```

### 국내 정부
```
site:data.go.kr                 # 공공데이터
site:motie.go.kr                # 산업통상자원부
site:msit.go.kr                 # 과학기술정보통신부
site:mafra.go.kr                # 농림축산식품부
```

## 쿼리 구성 원칙

### 라운드별 사이트 분배
- **Round 2 (대학)**: arxiv, IEEE, ACM, mit.edu, stanford.edu 등 (5회)
- **Round 3 (기업R&D)**: research.google, ai.meta.com, research.samsung.com 등 (4회)
- **Round 4 (연구기관)**: etri.re.kr, fraunhofer.de, csiro.au 등 (3회)

### 사이트별 쿼리 다양화
한 사이트에 2번 이상 쿼리 시 키워드 변형:
- `{기술} site:arxiv.org`
- `{기술} {하위키워드} site:arxiv.org`
- `{기술} 2024 site:arxiv.org`

### 한영 균형
- 국내 주제: 한국어 4~5 + 영어 3~4
- 글로벌 주제: 한국어 3 + 영어 6~7
