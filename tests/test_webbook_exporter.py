"""WebbookExporter 테스트 (v1.9.0 워크스트림 A — F52 A2).

카드 JSON 디렉토리 → file:// 정적 다중 페이지 HTML 웹북 (index + Part 페이지 + assets).
"""
import json
import sys

from techdoc_core.renderers.webbook import WebbookExporter


def _write_card(d, cid, title, body, formal_section=False):
    card = {"card_id": cid, "title": title, "sections": {"s1": {"body": body}}}
    if formal_section:
        card["formal_section"] = True
    (d / f"{cid}_card.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")


def test_export_produces_index_and_pages(tmp_path):
    """A2 — index.html + Part 페이지 생성, index가 페이지로 링크."""
    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "1.1", "기술 개요", "이것은 1.1 본문 내용이다.")
    _write_card(cards, "2.1", "프로젝트 개요", "이것은 2.1 본문 내용이다.")
    out = tmp_path / "webbook"

    stats = WebbookExporter().export(cards, out, title="테스트 보고서")

    assert (out / "index.html").exists()
    index_html = (out / "index.html").read_text(encoding="utf-8")
    assert "테스트 보고서" in index_html
    # 두 카드 페이지가 존재하고 index에서 링크된다
    pages = list(out.rglob("*.html"))
    assert len(pages) >= 3  # index + 2 페이지
    assert stats["pages"] == 2
    # 페이지 본문이 렌더된다
    all_page_text = "\n".join(p.read_text(encoding="utf-8") for p in pages if p.name != "index.html")
    assert "1.1 본문 내용" in all_page_text and "2.1 본문 내용" in all_page_text


def test_export_merges_split_cards(tmp_path):
    """A2 — split 카드(2.1.L1/L2)는 parent(2.1) 1페이지로 병합."""
    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "3.1.L1", "분할 상", "상 파트 본문.")
    _write_card(cards, "3.1.L2", "분할 하", "하 파트 본문.")
    out = tmp_path / "webbook"

    stats = WebbookExporter().export(cards, out)

    assert stats["pages"] == 1  # 병합
    pages = [p for p in out.rglob("*.html") if p.name != "index.html"]
    merged = pages[0].read_text(encoding="utf-8")
    assert "상 파트 본문" in merged and "하 파트 본문" in merged


def test_export_writes_css_asset(tmp_path):
    """A2 — assets/webbook.css 생성."""
    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "1.1", "제목", "본문.")
    out = tmp_path / "webbook"

    WebbookExporter().export(cards, out)

    assert (out / "assets" / "webbook.css").exists()


def test_variant_general_excludes_formal_cards(tmp_path):
    """F36·F43 — variant='general'은 formal_section 카드를 제외, 'full'은 전부 포함."""
    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "1.1", "일반 개요", "일반 본문.")
    _write_card(cards, "1.2", "SW 정형 사양", "정형 본문.", formal_section=True)

    full = WebbookExporter().export(cards, tmp_path / "full", variant="full")
    general = WebbookExporter().export(cards, tmp_path / "general", variant="general")

    assert full["pages"] == 2
    assert general["pages"] == 1  # formal 카드 제외


def test_cover_shows_version_and_edition_badge(tmp_path):
    """F43 — 표지에 문서 버전·판본 배지 표시."""
    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "1.1", "제목", "본문.")
    out = tmp_path / "wb"

    WebbookExporter().export(cards, out, version="v3.0", edition="전문가판")

    index = (out / "index.html").read_text(encoding="utf-8")
    assert "v3.0" in index and "전문가판" in index


def test_export_md_dir_round_trip(tmp_path):
    """F51 — 편집된 md 디렉토리(--tree 중간물)에서 웹북 재렌더."""
    md_dir = tmp_path / "md"
    (md_dir / "Part-본문").mkdir(parents=True)
    (md_dir / "Part-본문" / "1.1.md").write_text(
        "# 1.1 편집한 제목\n\n사용자가 편집한 본문 [REF-0001].\n\n- 첫째 항목\n- 둘째 항목",
        encoding="utf-8",
    )
    out = tmp_path / "wb"

    stats = WebbookExporter().export_md_dir(md_dir, out, title="편집본")

    assert (out / "index.html").exists()
    assert (out / "Part-본문" / "1.1.html").exists()
    page = (out / "Part-본문" / "1.1.html").read_text(encoding="utf-8")
    assert "사용자가 편집한 본문" in page and "<li>첫째 항목</li>" in page
    assert stats["pages"] == 1


def test_render_cli_webbook_from_md(tmp_path, monkeypatch):
    """F51 — `render --webbook --from-md <md_dir>`."""
    from scripts.render import main

    md_dir = tmp_path / "md"
    (md_dir / "Part-A").mkdir(parents=True)
    (md_dir / "Part-A" / "2.1.md").write_text("# 2.1 제목\n\n본문.", encoding="utf-8")
    out = tmp_path / "wb"
    monkeypatch.setattr(
        sys, "argv",
        ["render", "--webbook", "--from-md", str(md_dir), "-o", str(out)],
    )
    assert main() == 0
    assert (out / "index.html").exists()


def test_render_cli_webbook(tmp_path, monkeypatch):
    """A3 — `render --webbook --cards-dir …`가 웹북을 생성."""
    from scripts.render import main

    cards = tmp_path / "cards"
    cards.mkdir()
    _write_card(cards, "1.1", "제목", "본문 내용.")
    out = tmp_path / "wb"
    monkeypatch.setattr(
        sys, "argv",
        ["render", "--webbook", "--cards-dir", str(cards), "-o", str(out)],
    )
    assert main() == 0
    assert (out / "index.html").exists()
