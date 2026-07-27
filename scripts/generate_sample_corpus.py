#!/usr/bin/env python3
"""
Generate sample corpus for ALL problem-statement data sources:
Play Store, App Store, Reddit, Twitter/X, Forums/Quora.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"

PLAY_TEMPLATES = [
    "Blinkit is great for groceries but I never think to order {category} here.",
    "Why doesn't Blinkit have {product}? I always buy from Amazon instead.",
    "Fast delivery for milk and bread but {category} selection is very limited.",
    "I wish Blinkit had more brands in {category}. Zepto seems better for that.",
    "Didn't know Blinkit sells {category} until my friend mentioned it.",
    "Blinkit pe {category} nahi milta, Amazon se order karta hoon.",
    "Good app but missing {product}. Nykaa has better personal care range.",
]

REDDIT_TEMPLATES = [
    "Does anyone order {category} on Blinkit? Can't find {product} there.",
    "Blinkit vs Zepto — which has better {category}?",
    "I use Blinkit only for emergency groceries. For {category} I go to Amazon.",
]

TWITTER_TEMPLATES = [
    "Blinkit missing {product} again. Why no {category} section? @Blinkit",
    "Only use Blinkit for milk. Everything else from Amazon. #{category}",
    "Zepto > Blinkit for {category}. Change my mind.",
]

FORUM_TEMPLATES = [
    "Is Blinkit good for {category}? Looking for {product} but can't find it.",
    "Where do you buy {product} — Blinkit or Nykaa?",
    "Blinkit assortment for {category} is weak compared to BigBasket.",
]

CATEGORIES = [
    ("pet supplies", "dog food"),
    ("baby care", "diapers"),
    ("personal care", "shampoo"),
    ("electronics", "earphones"),
    ("stationery", "notebooks"),
    ("health pharmacy", "vitamins"),
    ("groceries", "milk"),
    ("home essentials", "detergent"),
]

RATINGS = [1, 2, 3, 4, 5]
WEIGHTS = [0.08, 0.12, 0.15, 0.35, 0.30]

PLATFORM_QUOTAS = {
    "play_store": 400,
    "app_store": 350,
    "reddit": 220,
    "twitter": 120,
    "forum": 110,
}

# Natural suffixes keep raw_text unique (exact dedup) while preserving template skeletons.
_NATURAL_SUFFIXES = [
    "",
    " Delivery was fine though.",
    " Might switch to Zepto next time.",
    " Been using Blinkit for two years.",
    " Same thought last month.",
    " Noticed this after the app update.",
    " My friends feel the same.",
    " Especially in Bangalore.",
    " Happens every reorder cycle.",
    " Wish the homepage showed this category.",
    " BigBasket still wins here for me.",
    " Instamart has better variety lately.",
    " Nykaa feels safer for this purchase.",
    " Amazon is my fallback always.",
    " Would buy if assortment improved.",
    " Needs better in-app discovery.",
    " Never saw an promo for this category.",
    " Category tab feels hidden.",
    " Search never surfaces these products.",
    " Price seems higher than competitors.",
]


def _unique_text(base: str, seq: int, seen: set[str]) -> str:
    """Ensure verbatim raw_text is unique without breaking template-family signal."""
    for offset in range(len(_NATURAL_SUFFIXES) + 5):
        suffix = _NATURAL_SUFFIXES[(seq + offset) % len(_NATURAL_SUFFIXES)]
        candidate = f"{base}{suffix}".strip()
        if candidate not in seen:
            seen.add(candidate)
            return candidate
    fallback = f"{base} Ref {seq}."
    seen.add(fallback)
    return fallback


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def _pick_category() -> tuple[str, str]:
    return random.choice(CATEGORIES)


def generate_play_store(n: int, seen: set[str], seq_start: int = 0) -> tuple[list[dict], int]:
    rows = []
    seq = seq_start
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i in range(n):
        cat, product = _pick_category()
        base = random.choice(PLAY_TEMPLATES).format(category=cat, product=product)
        text = _unique_text(base, seq, seen)
        seq += 1
        created = _random_date(start, end)
        rows.append(
            {
                "review_text": text,
                "score": random.choices(RATINGS, weights=WEIGHTS)[0],
                "at": created.isoformat(),
                "review_url": f"https://play.google.com/store/apps/details/review/{100000 + i}",
                "user_name": f"user_{i % 200}",
            }
        )
    return rows, seq


def generate_app_store(n: int, seen: set[str], seq_start: int = 0) -> tuple[list[dict], int]:
    rows = []
    seq = seq_start
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i in range(n):
        cat, product = _pick_category()
        base = random.choice(PLAY_TEMPLATES).format(category=cat, product=product)
        text = _unique_text(base, seq, seen)
        seq += 1
        created = _random_date(start, end)
        rows.append(
            {
                "content": text,
                "rating": random.choices(RATINGS, weights=WEIGHTS)[0],
                "updated": created.isoformat(),
                "link": f"https://apps.apple.com/app/blinkit/review/{200000 + i}",
                "title": f"Review {i}",
            }
        )
    return rows, seq


def generate_reddit(n: int, seen: set[str], seq_start: int = 0) -> tuple[list[dict], int]:
    rows = []
    seq = seq_start
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, tzinfo=timezone.utc)
    subs = ["india", "bangalore", "StartupsIndia", "IndianFood", "pets"]
    for i in range(n):
        cat, product = _pick_category()
        base = random.choice(REDDIT_TEMPLATES).format(category=cat, product=product)
        text = _unique_text(base, seq, seen)
        seq += 1
        created = _random_date(start, end)
        sub = random.choice(subs)
        rows.append(
            {
                "body": text,
                "created_at": created.isoformat(),
                "permalink": f"/r/{sub}/comments/abc{i}/blinkit_{cat.replace(' ', '_')}/",
                "subreddit": sub,
                "kind": random.choice(["submission", "comment"]),
            }
        )
    return rows, seq


def generate_twitter(n: int, seen: set[str], seq_start: int = 0) -> tuple[list[dict], int]:
    rows = []
    seq = seq_start
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i in range(n):
        cat, product = _pick_category()
        base = random.choice(TWITTER_TEMPLATES).format(
            category=cat.replace(" ", ""), product=product
        )
        text = _unique_text(base, seq, seen)
        seq += 1
        created = _random_date(start, end)
        rows.append(
            {
                "platform": "twitter",
                "raw_text": text,
                "created_at": created.isoformat(),
                "url": f"https://twitter.com/user/status/{3000000000 + i}",
                "metadata": '{"source":"twitter_csv"}',
            }
        )
    return rows, seq


def generate_forum(n: int, seen: set[str], seq_start: int = 0) -> tuple[list[dict], int]:
    rows = []
    seq = seq_start
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 6, 1, tzinfo=timezone.utc)
    sites = ["quora.com", "team-bhp.com"]
    for i in range(n):
        cat, product = _pick_category()
        base = random.choice(FORUM_TEMPLATES).format(category=cat, product=product)
        text = _unique_text(base, seq, seen)
        seq += 1
        created = _random_date(start, end)
        site = random.choice(sites)
        rows.append(
            {
                "platform": "forum",
                "raw_text": text,
                "created_at": created.isoformat(),
                "url": f"https://{site}/question/blinkit-{i}",
                "metadata": f'{{"forum_site":"{site.split(".")[0]}"}}',
            }
        )
    return rows, seq


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    random.seed(42)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    seq = 0

    play, seq = generate_play_store(PLATFORM_QUOTAS["play_store"], seen, seq)
    app, seq = generate_app_store(PLATFORM_QUOTAS["app_store"], seen, seq)
    reddit, seq = generate_reddit(PLATFORM_QUOTAS["reddit"], seen, seq)
    twitter, seq = generate_twitter(PLATFORM_QUOTAS["twitter"], seen, seq)
    forum, seq = generate_forum(PLATFORM_QUOTAS["forum"], seen, seq)

    write_csv(
        SAMPLES_DIR / "play_store.csv",
        play,
        ["review_text", "score", "at", "review_url", "user_name"],
    )
    write_csv(
        SAMPLES_DIR / "app_store.csv",
        app,
        ["content", "rating", "updated", "link", "title"],
    )
    write_csv(
        SAMPLES_DIR / "reddit.csv",
        reddit,
        ["body", "created_at", "permalink", "subreddit", "kind"],
    )
    write_csv(
        SAMPLES_DIR / "twitter.csv",
        twitter,
        ["platform", "raw_text", "created_at", "url", "metadata"],
    )
    write_csv(
        SAMPLES_DIR / "forum.csv",
        forum,
        ["platform", "raw_text", "created_at", "url", "metadata"],
    )

    total = sum(PLATFORM_QUOTAS.values())
    print(f"Generated {total} sample records in {SAMPLES_DIR} ({len(seen)} unique texts)")
    for platform, count in PLATFORM_QUOTAS.items():
        print(f"  {platform}: {count}")


if __name__ == "__main__":
    main()
