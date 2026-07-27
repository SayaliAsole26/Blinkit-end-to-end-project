"""Phase 2 clean module tests."""

from datetime import datetime, timezone

from models.records import SentenceSegment
from pipeline.clean import CleanModule, strip_html


def _segment(text: str) -> SentenceSegment:
    return SentenceSegment(
        segment_id="seg_1",
        record_id="rec_1",
        text=text,
        sentence_index=0,
        platform="forum",
        rating=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://forum.example.com/post/1",
    )


def test_html_stripped() -> None:
    raw = "<p>Blinkit is <b>great</b> for groceries</p>"
    assert strip_html(raw) == "Blinkit is great for groceries"


def test_category_mapping() -> None:
    mod = CleanModule()
    seg = _segment("I wish Blinkit had better pet food assortment.")
    clean = mod.clean_segment(seg)
    assert "pet_supplies" in clean.category_mentions


def test_logistics_tag() -> None:
    mod = CleanModule()
    seg = _segment("Delivery was late and rider was rude. Refund delay too.")
    clean = mod.clean_segment(seg)
    assert clean.is_logistics_only is True


def test_competitor_pre_tag() -> None:
    mod = CleanModule()
    seg = _segment("I compare Blinkit with Zepto for electronics.")
    clean = mod.clean_segment(seg)
    assert "Zepto" in clean.competitor_mentions_raw


def test_embed_text_enrichment() -> None:
    mod = CleanModule()
    seg = _segment("Never order personal care from Blinkit, use Nykaa.")
    clean = mod.clean_segment(seg)
    assert clean.embed_text.startswith("Represent feedback about cross-category shopping")
    assert "[categories:" in clean.embed_text
    assert "Nykaa" in clean.embed_text


def test_hinglish_included_when_mixed() -> None:
    mod = CleanModule()
    seg = _segment("Blinkit se groceries fast aati hain but pet food nahi milta")
    clean = mod.clean_segment(seg)
    assert clean.language == "hinglish"
    assert clean.embed_skipped is False
    assert clean.embed_text


def test_devanagari_mostly_excluded_from_embed() -> None:
    mod = CleanModule()
    hindi = (
        "ब्लिंकिट से केवल किराना सामान मंगाते हैं "
        "पालतू भोजन यहाँ उपलब्ध नहीं है"
    )
    seg = _segment(hindi)
    clean = mod.clean_segment(seg)
    assert clean.embed_skipped is True
    assert clean.embed_skip_reason == "devanagari_ratio_exceeded"


def test_search_gap_tag() -> None:
    mod = CleanModule()
    seg = _segment("Wish they had baby diapers in stock.")
    clean = mod.clean_segment(seg)
    assert "search_gap" in clean.content_tags
