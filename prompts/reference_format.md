# 참고문헌 양식 — APA 7th

말미 참고문헌 목록의 표준 양식. 본문 인용(`[REF-xxx]`)은 `_shared/citation_rules.md`가 정의하고, 본 문서는 **말미 목록**의 저자·연도·제목·출처·DOI 표기와 영문/국문 분리·정렬·venue 정규화를 정의한다. `reference_list.json`의 `authors/year/venue/title/url` 필드가 APA 호환이다.

---

## 1. 영문 / 국문 참고문헌 분리

말미 목록은 영문·국문을 분리하고 각각 정렬한다.

```
# 참고문헌 (References)

## 영문 참고문헌
- {APA entries, 첫 저자 alphabet 정렬}

## 국문 참고문헌
- {APA entries, 첫 저자 가나다 정렬}
```

- 판정: 첫 저자가 한글이면 국문, 아니면 영문.
- 저자가 비어 있으면 `institution`(기관 저자)의 한글 여부로 보조 판정.

## 2. 저자 표기 — `성, 이니셜.`

APA 7th 저자 양식. 성 뒤 콤마, 이니셜 마침표.

| 저자 수 | 양식 |
|---|---|
| 단독 | `Park, J.` |
| 2명 | `Park, J., & Kim, S.` |
| 3~20명 | `Park, J., Kim, S., & Lee, M.` (Oxford 콤마) |
| 21명 이상 | `Park, J., ..., Lee, M.` (처음 19 + 마지막 1) |

- 본문 풀어쓰기 시 3+ 저자는 `Smith et al. (2024)` (한글 본문에서도 `et al.` 그대로).

## 3. 연도·제목·출처·DOI 우선

엔트리 기본형:

```
{authors}. ({year}). {title}. {venue}, {volume}({issue}), {pages}. {DOI 또는 URL}  [REF-NNN]
```

예시:

```
- Park, J., & Kim, S. (2024). Smart agriculture in Korea: A national strategy review. Agricultural Systems, 219, 104012. https://doi.org/10.1016/j.agsy.2024.104012  [REF-004]
- 농촌진흥청 (2024). 노지스마트농업 시범사업 1차년도 성과 분석. https://www.rda.go.kr/...  [REF-012]
```

- **DOI 우선**(`https://doi.org/...`). 없으면 publisher / preprint URL. 한국 자료는 RDA·KMA·NTIS 등 도메인 URL.
- `[REF-NNN]` ID를 엔트리 우측 끝에 부착(역추적용).

## 4. 기관 저자·웹자료

- 기관 보고서는 저자 = 기관명:
  - `USDA. (2024). National agricultural statistics service crop production. https://...  [REF-018]`
  - `농촌진흥청 (2024). 노지스마트농업 표준모델 구축 보고서. https://...  [REF-012]`
- 웹자료는 가능하면 발행 기관·연도를 채우고, 접근일은 끊김 우려 시에만 부기.

## 5. venue 정규화 (출처 표기 통일)

`reference_list.json`의 `venue` 필드는 보수적으로 정규화한다(의미 손실 없는 결정적 변환만).

| 현재 표기 | 정규 표기 | 규칙 |
|---|---|---|
| `Sensors (MDPI)` | `Sensors` | publisher 병기 strip |
| `MDPI Agriculture` | `Agriculture` | publisher prefix strip |
| `Frontiers in Plant Science, 2024` | `Frontiers in Plant Science` | 연도 suffix strip |
| `Agric. Water Mgmt.` | `Agricultural Water Management` | 약식 → 정식명 매핑 |

- publisher 예: MDPI · Springer · Elsevier · Wiley · IEEE · ACM · Frontiers · Nature.
- **보존**(정보 유용): 슬래시·세로바 멀티 출처(`A / B`), archive ID(`PMC*`·`arXiv:*`), 표준 ID(`ISO 11783-1:2017`), 기관 보고서 식별자(`GAO-24-105962`).
- 약어 형태(`J. Agric. Sci.`)는 `venue`에 입력하지 말고 정식명으로 통일한다.
