"""Paraphrase snippets must differ from raw source text."""

from pipeline.synthesize import paraphrase_snippet


def test_paraphrase_not_verbatim() -> None:
    samples = [
        "Blinkit doesn't have the shampoo brand I need.",
        "Always order dog food from Amazon instead of Blinkit.",
        "Zepto has better baby care selection.",
    ]
    for raw in samples:
        para = paraphrase_snippet(raw)
        assert para.strip().lower() != raw.strip().lower()
