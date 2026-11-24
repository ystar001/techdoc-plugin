"""인용·서지 게이트 V8·V13·V45·V68 (v1.11-a — 시리즈 check_v2·prose_gates 이식, F85)."""
import techdoc_core.qc.gates  # noqa: F401 — 게이트 등록
from techdoc_core.qc.engine import run_selftests
from techdoc_core.qc.registry import REGISTRY, sample_model


def _n(gid, model):
    return len(REGISTRY[gid](model).findings)


def _card(body):
    return {"sections": {"s1": {"body": body}}}


# ── V8 인용 REF ↔ 참고문헌 목록 ──

def test_v8_cited_ref_missing_from_list():
    m = sample_model(cards={"1.1": _card("근거다[REF-001]. 또[REF-002].")},
                     references=[{"id": "REF-001"}])
    out = REGISTRY["V8"](m)
    assert len(out.findings) == 1 and "REF-002" in out.findings[0].msg


def test_v8_orphan_listed_ref_counts_each():
    m = sample_model(cards={"1.1": _card("근거다[REF-001].")},
                     references=[{"id": "REF-001"}, {"id": "REF-008"}, {"id": "REF-009"}])
    assert _n("V8", m) == 2


def test_v8_ignores_backtick_fence_and_self_check():
    body = "표기 예 `REF-005`는 인용이 아니다.\n```json\n{\"id\": \"REF-006\"}\n```\n근거[REF-001]."
    card = {**_card(body), "self_check": {"note": "REF-007은 쓰지 않았다"}}
    m = sample_model(cards={"1.1": card}, references=[{"id": "REF-001"}])
    assert _n("V8", m) == 0


def test_v8_counts_mermaid_citation_and_draft():
    body = "```mermaid\ngraph TD; A[근거 REF-003]\n```"
    m = sample_model(cards={"1.1": _card(body)}, references=[{"id": "REF-003"}, {"id": "REF-004"}])
    m.draft.append(__import__("techdoc_core.qc.model", fromlist=["TreeFile"]).TreeFile("p.md", "[REF-004]"))
    assert _n("V8", m) == 0


def test_v8_not_counting_render_tree_reference_list():
    # 렌더 트리 끝 참고문헌 목록을 인용으로 세면 거짓 통과 — 트리는 V8 원천이 아니다
    m = sample_model(cards={"1.1": _card("x")}, tree={"a.md": "- [REF-001] 문헌"},
                     references=[{"id": "REF-001"}])
    assert _n("V8", m) == 1


def test_v8_no_reference_list_is_notarget():
    out = REGISTRY["V8"](sample_model(cards={"1.1": _card("[REF-001]")}))
    assert out.targets_read == 0 and out.findings == []


def test_v8_foreign_prefix_not_counted():
    m = sample_model(cards={"1.1": _card("다른 편 수확편:REF-162. 근거[REF-001].")},
                     references=[{"id": "REF-001"}])
    assert _n("V8", m) == 0


# ── V13 중복 등록·비원전·말미 목록 ──

def test_v13_duplicate_registration():
    refs = [{"id": "REF-001", "url": "https://a.org/x/", "title": "같은 문헌"},
            {"id": "REF-002", "url": "https://a.org/x", "title": "같은 문헌"}]
    assert _n("V13", sample_model(cards={"1.1": _card("x")}, references=refs)) == 1


def test_v13_same_url_different_title_is_ok():
    refs = [{"id": "REF-001", "url": "https://a.org/m", "title": "제1장 보리"},
            {"id": "REF-002", "url": "https://a.org/m", "title": "제2장 밀"}]
    assert _n("V13", sample_model(cards={"1.1": _card("x")}, references=refs)) == 0


def test_v13_nonprimary_and_config_exemption():
    refs = [{"id": "REF-001", "url": "https://en.wikipedia.org/wiki/X", "title": "X"}]
    m = sample_model(cards={"1.1": _card("[REF-001]")}, references=refs)
    assert _n("V13", m) == 1
    m2 = sample_model(cards={"1.1": _card("[REF-001]")}, references=refs,
                      extra={"citation": {"nonprimary_ok": {"REF-001": "1차 문헌 없음"}}})
    assert _n("V13", m2) == 0


_TAIL_LIST_CFG = {"citation": {"card_ref_list_pattern": r"인용 참고문헌 \((\d+)건\)\.\*\*(.{0,1200})"}}


def test_v13_card_tail_list_mismatch_when_configured():
    body = "근거[REF-001]. 또[REF-002].\n\n**인용 참고문헌 (2건).** REF-001 · REF-003"
    m = sample_model(cards={"1.1": _card(body)}, references=[], extra=_TAIL_LIST_CFG)
    assert _n("V13", m) == 2


def test_v13_card_tail_list_not_builtin():
    # 카드 말미 인용 목록 문구는 시리즈 작성 관례 — 플러그인 기본으로 내장하지 않는다
    body = "근거[REF-001]. 또[REF-002].\n\n**인용 참고문헌 (2건).** REF-001 · REF-003"
    assert _n("V13", sample_model(cards={"1.1": _card(body)}, references=[])) == 0


# ── V45 [REF-n](…) 가짜 링크 ──

def test_v45_fake_link():
    m = sample_model(tree={"a.md": "근거다[REF-003](표 13.3-2)."})
    assert _n("V45", m) == 1


def test_v45_real_link_and_fence_ok():
    text = "주소 [REF-003](https://x.org) 는 괜찮다.\n```\n[REF-004](예시)\n```\n"
    assert _n("V45", sample_model(tree={"a.md": text})) == 0


def test_v45_uses_draft_when_present():
    m = sample_model(tree={"a.md": "[REF-001](덧말)"})
    m.draft.append(__import__("techdoc_core.qc.model", fromlist=["TreeFile"]).TreeFile("d.md", "깨끗"))
    assert _n("V45", m) == 0


# ── V68 참고문헌 목록 ──

_REFMD = "## 영문\n- Smith, J. (2020). Title. [REF-001]\n"


def test_v68_placeholder_author():
    md = "## 영문\n- et al. (2020). Title. [REF-001]\n"
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md})) == 1


def test_v68_team_author_is_caught():
    md = "## 영문\n- AI Research Team. (2023). Report. [REF-002]\n"
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md})) == 1


def test_v68_internal_file_builtin_and_from_config():
    md = "## 영문\n- Smith, J. (2020). See MASTERPLAN.md. [REF-001]\n"
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md})) == 0
    cfg = {"citation": {"internal_files": ["MASTERPLAN.md"]}}
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md}, extra=cfg)) == 1
    md2 = "## 영문\n- Smith, J. (2020). x_card.json. [REF-001]\n"
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md2})) == 1


def test_v68_group_and_sort_order():
    md = ("## 국문\n- Smith, J. (2020). T. [REF-001]\n"
          "## 영문\n- Zeta, A. (2020). T. [REF-002]\n- Alpha, B. (2021). T. [REF-003]\n")
    assert _n("V68", sample_model(reference_md={"참고문헌.md": md})) == 2


def test_v68_empty_authors_in_reference_list():
    refs = [{"id": "REF-001", "title": "t", "authors": []},
            {"id": "REF-002", "title": "t", "authors": ["여러 저자"]},
            {"id": "REF-003", "title": "t", "authors": ["Kim, H."]}]
    assert _n("V68", sample_model(references=refs)) == 2


def test_v68_clean_list_passes():
    assert _n("V68", sample_model(reference_md={"참고문헌.md": _REFMD},
                                  references=[{"id": "REF-001", "authors": ["Smith, J."]}])) == 0


def test_v68_nothing_is_notarget():
    out = REGISTRY["V68"](sample_model(tree={"a.md": "x"}))
    assert out.targets_read == 0


def test_selftests_pass():
    funcs = {k: REGISTRY[k] for k in ("V8", "V13", "V45", "V68")}
    assert run_selftests(funcs) == []
    assert all(getattr(funcs[k], "samples", []) for k in funcs)
