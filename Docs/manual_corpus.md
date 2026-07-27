# Manual Corpus Format

When live API access is unavailable (rate limits, missing credentials), import feedback via CSV files in `data/samples/` or custom paths.

## Unified Format (all platforms)

Place a file at `data/samples/manual.csv` or pass a custom path via connector init.

| Column | Required | Description |
|--------|----------|-------------|
| `platform` | Yes | `play_store`, `app_store`, `reddit`, `twitter`, `forum` |
| `raw_text` | Yes | Verbatim review/post text — never modified at ingest |
| `created_at` | Yes | ISO 8601 datetime, e.g. `2024-03-15T10:30:00+00:00` |
| `url` | Yes | Stable source URL |
| `rating` | No | Integer 1–5; leave empty for Reddit/forums |
| `language` | No | `en`, `hinglish`, etc. |
| `metadata` | No | JSON string with extra fields |

### Example row

```csv
platform,raw_text,rating,created_at,url,language,metadata
reddit,"Does Blinkit have pet food?",,2024-01-10T08:00:00+00:00,https://reddit.com/r/india/comments/abc123,"en","{""subreddit"":""india""}"
```

## Platform-Specific CSV Formats

### Play Store (`data/samples/play_store.csv`)

| Column | Aliases |
|--------|---------|
| `review_text` | `text`, `content` |
| `score` | `rating` |
| `at` | `created_at`, `date` |
| `review_url` | `url` |
| `user_name` | `author` |

### App Store (`data/samples/app_store.csv`)

| Column | Aliases |
|--------|---------|
| `content` | `review_text` |
| `rating` | `score` |
| `updated` | `created_at`, `date` |
| `link` | `url` |

### Reddit (`data/samples/reddit.csv`)

| Column | Notes |
|--------|-------|
| `body` | Post or comment text |
| `created_at` | ISO datetime or Unix timestamp in `created_utc` |
| `permalink` | `/r/subreddit/...` or full URL |
| `subreddit` | Optional |
| `rating` | Always omitted — inferred as `None` |

## Generate Sample Corpus (1100+ records)

```bash
python scripts/generate_sample_corpus.py
python -m pipeline ingest --source all
```

## Live Reddit (optional)

Set in `.env`:

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=blinkit-insight-engine/0.1.0
```

Install optional dependency: `pip install praw`

If PRAW fails or credentials are missing, ingestion falls back to `data/samples/reddit.csv`.

## Idempotency

`record_id = SHA-256(platform + url + created_at)`. Re-running ingest with the same run ID skips duplicate `record_id` values within that run.
