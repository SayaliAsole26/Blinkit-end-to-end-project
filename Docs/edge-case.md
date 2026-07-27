# Edge Cases & Corner Cases

> **References:** [implementation-plan.md](./implementation-plan.md) · [architecture.md](./architecture.md) · [Problemstatement.md](./Problemstatement.md)  
> **Project:** Blinkit Review Analyzer Dashboard

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [Master Edge-Case Matrix](#2-master-edge-case-matrix)
3. [Detailed Edge-Case Catalog](#3-detailed-edge-case-catalog)
4. [Phase-Wise Edge Cases](#4-phase-wise-edge-cases)
5. [Pipeline-Stage Edge Cases](#5-pipeline-stage-edge-cases)
6. [Data-Quality & Content Edge Cases](#6-data-quality--content-edge-cases)
7. [ML / LLM Edge Cases](#7-ml--llm-edge-cases)
8. [Validation Edge Cases](#8-validation-edge-cases)
9. [Dashboard & API Edge Cases](#9-dashboard--api-edge-cases)
10. [Operational & Infrastructure Edge Cases](#10-operational--infrastructure-edge-cases)
11. [Risk Register (Edge-Case Related)](#11-risk-register-edge-case-related)
12. [Test Coverage Matrix](#12-test-coverage-matrix)
13. [Explicitly Out of Scope](#13-explicitly-out-of-scope)

---

## 1. Guiding Principles

All edge-case handling in this project follows these rules:

| Principle | Rule |
|-----------|------|
| **Never discard raw text** | Filter, tag, or exclude from downstream stages — but preserve in immutable raw store |
| **Tag, don't delete** | Ambiguous or confounding content gets metadata flags, not removal |
| **Log everything excluded** | Every exclusion must appear in an audit log with reason and count |
| **Causal over polar** | Edge cases must not fall back to plain sentiment; assign cognitive barrier or tag |
| **Demonstrable handling** | Edge-case metrics (excluded %, flagged runs) must appear in dashboard or run summary |
| **Copyright safety** | User text is never shown verbatim in dashboard outputs |

---

## 2. Master Edge-Case Matrix

| # | Edge Case | Detection | Pipeline Action | Storage / Dashboard | Phase |
|---|-----------|-----------|-----------------|---------------------|-------|
| EC-01 | Delivery/logistics confounding discovery | Keyword tagger in Clean | `is_logistics_only=True`; exclude from discovery clusters | Logistics slice in overview; excluded from cross-shop insights | 2 |
| EC-02 | Sarcasm / mixed sentiment | Groq low-confidence flag | Label with barrier; add `confidence_note` | Default `medium` confidence | 3 |
| EC-03 | Low-volume high-signal niche themes | HDBSCAN `min_cluster_size=3` | Do not filter by frequency alone | `low` confidence + `niche` tag | 3 |
| EC-04 | Cross-platform comparison contamination | Competitor alias map | Extract as `competitor_entity`; separate from Blinkit friction | Competitor benchmarking view | 2, 5 |
| EC-05 | Hinglish / code-mixed text | Script-ratio heuristic | Process if understandable; set `language=hinglish` | Log excluded % in overview | 1, 2 |
| EC-06 | Review-bombing / spam spikes | Temporal density anomaly | Flag ingestion run; do not auto-delete | Warning banner on overview | 2 |
| EC-07 | Missing metadata (Reddit, forums) | `rating=None` at ingest | Text-only barrier inference via Groq | Omit rating filters for affected platforms | 1 |
| EC-08 | API rate limits | HTTP 429 / quota errors | Retry + backoff; fall back to manual CSV | Document in `ingestion_run.metadata` | 1 |
| EC-09 | Copyright / verbatim reproduction | Diff check vs raw text | Paraphrase in synthesis | `example_snippets` = paraphrased only (max 3) | 4 |
| EC-10 | Stale insights (fixed UX issues) | `latest_evidence_date` > 12 months | `is_stale=True`; deprioritize in ranking | Stale badge in UI | 4, 5 |
| EC-11 | Duplicate records across runs | SHA-256 `record_id` collision | Skip or log duplicate; idempotent ingest | Dedup count in audit log | 1 |
| EC-12 | Star-only reviews (no text) | Empty text after trim | Skip embed/LLM; retain for rating stats | Logged separately; not in insight cards | 2 |
| EC-13 | Conflicting insights (same theme) | Opposing barriers in synthesis | Emit separate insight cards; do not average | Both shown; linked (RQ7 signal) | 4 |
| EC-14 | Groq JSON parse failure | Invalid / partial response | Retry (max 2); log unlabeled cluster | Cluster marked `UNLABELED` in audit | 3 |
| EC-15 | HDBSCAN noise points | Cluster label `-1` | Assign to nearest cluster or `UNCLUSTERED` bucket | Excluded from insight synthesis or low confidence | 3 |
| EC-16 | Long reviews exceeding token budget | Char/token count pre-LLM | Truncate to 5–10 representative snippets | N/A (pre-call truncation) | 3 |
| EC-17 | Dashboard sentiment leak | API returns `sentiment_split` | Block field in API layer | Never render "% negative" | 5 |
| EC-18 | Low inter-run agreement | 10% re-sample disagreement | Downgrade confidence tier | Agreement % in validation panel | 4 |
| EC-19 | HTML-heavy forum content | HTML tags in raw text | Strip via `bleach` in Clean | Clean text in pipeline; raw preserved | 2 |
| EC-21 | Thematic template repetition | Jaccard ≥ 0.85 on token sets | Tag `template_family`; keep in embed/cluster path | Dedup merge at cosine 0.90 pre-Groq | 2, 3 |
| EC-22 | Short Twitter/single-sentence reviews | `len(raw_text) < 280` | Whole-record segment (no split) | 1 segment per record | 2 |
| EC-23 | Search-gap language (~47% of corpus) | Regex on wish/find/missing | Parallel Track B clustering | RQ8 TF-IDF themes | 3 |

---

## 3. Detailed Edge-Case Catalog

### EC-01 — Delivery / Logistics Confounding Discovery Signal

**Problem:** Users complain about late delivery, rude riders, or refund delays. These are negative signals but do **not** explain cross-category discovery friction. Including them in discovery clusters dilutes insight quality.

**Example input:**
> "Blinkit delivery was 45 mins late again. Rider was rude."

**Detection:**
- Keyword classifier in Clean module: `delivery`, `rider`, `late`, `refund delay`, `packaging damaged`, `wrong item delivered`
- Tag: `is_logistics_only=True`, `content_tags=["logistics"]`

**Pipeline action:**
- Segment is embedded (for completeness) but **excluded from discovery/cross-shop HDBSCAN clusters**
- Still counted in corpus size and logistics-specific overview slice

**Dashboard:**
- Shown in logistics KPI slice
- Excluded from cognitive barrier charts for cross-shop insights
- Overview may show "% logistics-only" for transparency

**Tests:** `test_clean.py` — logistics keyword → `is_logistics_only=True`

---

### EC-02 — Sarcasm / Mixed Sentiment

**Problem:** A review may say "Great app — never has what I actually need" (positive tone, negative discovery signal). Plain sentiment classification fails.

**Example input:**
> "Love Blinkit for groceries! Would never think to buy electronics here though lol"

**Detection:**
- Groq classification during cluster labeling
- Optional: flag when barrier and sentiment polarity conflict

**Pipeline action:**
- Assign `user_cognitive_barrier` based on semantic meaning, not polarity
- Set `confidence_tier=medium` by default
- Add optional `confidence_note` in cluster metadata

**Dashboard:**
- Medium confidence badge
- Never show as "X% negative"

**Tests:** Manual QA on sample sarcastic reviews in Phase 3 exit criteria

---

### EC-03 — Low-Volume but High-Signal Niche Themes

**Problem:** Rare but important themes (e.g., pet pharmacy, specialty baby formula) may have only 5–10 mentions. Frequency-only ranking would discard them.

**Example input:**
> 7 Reddit comments over 6 months requesting "prescription pet food" on Blinkit

**Detection:**
- HDBSCAN forms small cluster (`min_cluster_size=3`)
- Cluster survives clustering stage despite low N

**Pipeline action:**
- Do **not** apply minimum frequency filter at cluster stage
- Surface in synthesis with `confidence_tier=low` and `theme_tags=["niche"]`
- Still map to relevant RQ (typically RQ8)

**Dashboard:**
- Visible in Insight Explorer with `low` confidence + `niche` tag
- Not hidden from report due to low count

**Tests:** `test_cluster.py` — cluster of size 5 is retained

---

### EC-04 — Cross-Platform Comparison Contamination (Zepto / Instamart)

**Problem:** Users compare Blinkit to Zepto, Instamart, or Swiggy Instamart. These are **competitor benchmarking signals**, not Blinkit cross-shop friction within Blinkit.

**Example input:**
> "Zepto has better personal care range. I only use Blinkit for milk and bread."

**Detection:**
- Competitor alias map in Clean: `Zepto`, `Instamart`, `Swiggy Instamart`, `Amazon`, `Nykaa`, `Myntra`
- Pre-tag: `competitor_mentions_raw[]`, `content_tags=["competitor_compare"]`

**Pipeline action:**
- Extract triplet: `[Blinkit category] → [competitor] → [advantage]` via merged Groq call
- Separate from Blinkit-native friction in synthesis aggregation
- Feeds RQ1 (habitual lock-in elsewhere) and RQ4

**Dashboard:**
- Competitor Benchmarking view (heatmap: category × competitor × advantage)
- Not mixed into generic "Blinkit friction" barrier chart

**Tests:** `test_clean.py` — Zepto mention pre-tagged; `test_groq_schema.py` — competitor fields populated

---

### EC-05 — Hinglish / Code-Mixed Text

**Problem:** Indian users mix Hindi (Devanagari) and English. BGE-small is English-optimized; fully Hindi segments may embed poorly.

**Example input:**
> "Blinkit pe baby products nahi milte, Amazon se order karta hoon"

**Detection:**
- Script-ratio heuristic in Clean: Devanagari chars / total chars
- Threshold: >70% Devanagari → `language="excluded"`; mixed → `language="hinglish"`

**Pipeline action:**
- **Ingest (Phase 1):** Store as-is; never drop at ingest
- **Clean (Phase 2):** Process Hinglish if Latin-heavy enough for BGE; log excluded count
- Log `% excluded` and `% hinglish` in run summary

**Dashboard:**
- Overview shows language breakdown and excluded %
- Never silently drop — transparency required

**Tests:** `test_clean.py` — Hinglish detection; run summary includes excluded %

---

### EC-06 — Review-Bombing / Spam Spikes

**Problem:** Coordinated negative campaigns (e.g., 200 identical 1-star reviews in 24 hours) skew frequency metrics.

**Example input:**
> 150 Play Store reviews with identical text posted on the same date

**Detection:**
- Filter module: exact duplicate hash (SHA-256 of normalized text)
- Temporal density anomaly: >N reviews with same hash within 24h window
- Bot/template regex patterns

**Pipeline action:**
- Exact duplicates: exclude from pipeline; log in `filter_audit_log`
- Spike detected: flag `ingestion_run.metadata.review_bomb_suspected=True`
- Do **not** auto-delete non-duplicate reviews in the spike window

**Dashboard:**
- Warning banner on Overview when spike flagged
- Filter audit log accessible in validation/metadata panel

**Tests:** `test_filter.py` — duplicate detection; spike flag on synthetic burst

---

### EC-07 — Missing Metadata (Reddit, Forums)

**Problem:** Reddit posts and forum threads have no star rating. Rating-based filters and rating-sentiment correlation are unavailable.

**Example input:**
> Reddit post: "Does anyone order pet food on Blinkit?" (no rating field)

**Detection:**
- At ingestion: `rating=None` for `platform in ["reddit", "forum"]`

**Pipeline action:**
- Store `rating=None` in `UnifiedRecord`
- Groq infers friction from text only (no rating context in prompt)
- Do not impute fake ratings

**Dashboard:**
- Rating filter hidden or disabled when viewing Reddit-only insights
- Platform filter allows isolating rated vs unrated sources

**Tests:** `test_normalizer.py` — Reddit sample → `rating=None`

---

### EC-08 — API Rate Limits (Twitter, Reddit, Play Store)

**Problem:** Source APIs return 429 or quota exhaustion during ingestion.

**Detection:**
- HTTP 429, rate-limit headers, PRAW/API exceptions

**Pipeline action:**
- Exponential backoff with jitter (e.g., 1s → 2s → 4s → max 60s)
- After max retries: switch to manual CSV fallback corpus
- Document fallback in `ingestion_run.metadata.fallback_used=True`

**Dashboard:**
- Overview source mix shows which sources used manual fallback
- Metadata panel documents corpus provenance

**Tests:** Mock 429 response → retry then fallback path

**Manual fallback:** CSV format documented in `docs/manual_corpus.md`

---

### EC-09 — Copyright / Verbatim Reproduction

**Problem:** Displaying user review text verbatim in dashboard may violate copyright and platform ToS.

**Pipeline action:**
- Synthesis stage paraphrases all `example_snippets[]` (max 3 per insight)
- Diff check: snippet must not match raw text above similarity threshold (e.g., >85%)
- Raw text stays in immutable raw store (internal only)

**Dashboard:**
- Evidence drill-down shows paraphrased snippets only
- Never render `raw_text` in API responses to frontend

**Tests:** `test_paraphrase.py` — snippets differ from raw; `test_api` — no raw_text field exposed

---

### EC-10 — Stale Insights (Now-Fixed UX Issues)

**Problem:** A complaint from 2023 about a missing category may no longer apply if Blinkit added that category in 2024.

**Detection:**
- Compare `latest_evidence_date` to pipeline run date
- If evidence span > 12 months old → `is_stale=True`

**Pipeline action:**
- Flag in synthesis; apply recency decay in ranking formula
- Do not delete — may still be useful with stale badge

**Dashboard:**
- Stale warning icon on insight card
- Deprioritized in default sort (ranked lower)
- Filter: "Include stale" toggle in Insight Explorer

**Tests:** `test_staleness.py` — evidence >12 months → `is_stale=True`

---

### EC-11 — Duplicate Records Across Ingestion Runs

**Problem:** Re-running ingestion may fetch the same review twice.

**Detection:**
- `record_id = SHA-256(platform + url + created_at)`

**Pipeline action:**
- Raw store append-only; duplicate `record_id` skipped or logged
- Ingestion is idempotent on `record_id`

**Tests:** `test_record_id_stability.py` — same input → same hash; re-ingest → no duplicate count increase

---

### EC-12 — Star-Only Reviews (No Text)

**Problem:** User submits rating only: ★★★★★ with empty review body.

**Detection:**
- Filter: `raw_text.strip() == ""` after trim

**Pipeline action:**
- Exclude from embed, cluster, and Groq labeling
- Retain in raw store and filter log as `star_only`
- Available for rating-only aggregate stats (e.g., avg rating by platform)

**Dashboard:**
- Counted in corpus overview "star-only (no text)" KPI
- Not included in insight cards

**Tests:** `test_filter.py` — empty text logged as star-only, not embedded

---

### EC-13 — Conflicting Insights on Same Theme

**Problem:** Same theme ("Electronics on Blinkit") may show `RETURN_POLICY_ANXIETY` for one segment and `AUTHENTICITY_DISTRUST` for another — averaging would hide segmentation.

**Example:**
- Segment A (parents): authenticity fear for kids' electronics
- Segment B (general): return policy confusion

**Pipeline action:**
- **Conflict policy:** emit **separate insight cards** — do not merge or average barriers
- Link cards as `related_insights[]` when same `theme_label`

**Dashboard:**
- Both cards visible in Insight Explorer and Segment view
- Signals RQ7 (which segments behave differently)

**Tests:** `test_conflict_policy.py` — opposing barriers → two cards, not one averaged

---

### EC-14 — Groq JSON Parse Failure

**Problem:** Groq returns malformed JSON or partial `CrossShoppingFrictionAnalysis`.

**Detection:**
- Pydantic validation failure on response
- JSON decode error

**Pipeline action:**
- Retry up to 2 times with stricter system prompt
- On final failure: log cluster as `UNLABELED`; exclude from synthesis or mark `low` confidence
- Increment `groq_calls_made` — alert if > 1.2 × N_clusters

**Tests:** `test_groq_schema.py` — mock invalid JSON → retry; `test_merged_call_rule.py` — call count guard

---

### EC-15 — HDBSCAN Noise Points

**Problem:** Segments that don't fit any cluster get label `-1` (noise).

**Pipeline action:**
- Assign to nearest cluster by cosine similarity, OR
- Bucket into `UNCLUSTERED` for manual review
- Do not silently discard

**Best approach:** If noise **>25%**, switch to KMeans (`k=20`). Use `min_cluster_size=3` for the reference corpus.

**Tests:** `test_cluster.py` — noise assignment behavior

---

### EC-16 — Long Reviews Exceeding Token Budget

**Problem:** A 2,000-word review cannot be sent whole to Groq.

**Pipeline action:**
- Sentence-level split in Preprocess (not doc-level)
- Cluster labeling uses 5–10 representative snippets only (~150 tokens each)
- Truncate/summarize before LLM call — never per-sentence Groq calls

**Tests:** Integration test — long review → cluster prompt under token limit

---

### EC-17 — Dashboard Sentiment Leak

**Problem:** Accidentally showing "65% negative" violates the project spec.

**Pipeline action:**
- API layer strips/forbids `sentiment_split` in responses
- Lint test: `test_api_no_sentiment.py`

**Dashboard rule:**
- Show `cognitive_barrier_split{}` and `dominant_funnel_leak_stage` only
- Replace any sentiment chart with Cognitive Barrier Chart

---

### EC-18 — Low Inter-Run Agreement

**Problem:** 10% validation re-sample disagrees with primary Groq pass on barrier or funnel stage.

**Detection:**
- Second Groq pass on 10% cluster sample
- Compute agreement % per field

**Pipeline action:**
- Log disagreement rate in `validation_runs`
- Downgrade affected insights to `medium` or `low` confidence
- Target: document actual %; aim ≥70% agreement

**Dashboard:**
- Validation panel shows agreement gauge and per-field breakdown

---

### EC-19 — HTML-Heavy Forum / Quora Content

**Problem:** Forum scrapes contain `<p>`, `<a href>`, markdown artifacts.

**Detection:**
- HTML tag presence in raw text

**Pipeline action:**
- Strip via `bleach` and markdown cleanup in Clean
- Raw store preserves original HTML verbatim

**Tests:** `test_clean.py` — HTML input → clean plain text output

---

### EC-21 — Thematic Template Repetition

**Problem:** ~10%+ of the reference corpus shares skeleton templates ("Blinkit is great for groceries but I never think to order {category} here") with different category words.

**Pipeline action:** Tag `template_family` in Filter; **do not exclude**. BGE clusters variants together; dedup merge at cosine **0.90** before Groq.

---

### EC-22 — Short Single-Sentence Reviews

**Problem:** Most normalized records are 40–120 chars (Twitter, Play Store). Sentence splitting creates useless fragments.

**Pipeline action:** If `len(raw_text) < 280` → one segment = whole record. Min segment length 20 chars after split.

---

### EC-23 — Search-Gap Language (Parallel Track)

**Problem:** ~47% of corpus contains wish/find/missing language — must not be diluted in general discovery clusters.

**Pipeline action:** **Track B** runs in parallel after embed: regex filter → HDBSCAN → TF-IDF labels. Zero Groq. Feeds RQ8 directly.

---

### EC-20 — Emoji-Only / Emoji-Heavy Sentences

**Problem:** "👍👍👍" or "😡 late again" may split or embed oddly.

**Pipeline action:**
- Emoji-aware sentence splitter in Preprocess (spaCy/pysbd rules)
- Retain emoji context unless segment is emoji-only empty semantic content
- Emoji-only segments: exclude from embed (similar to empty)

---

## 4. Phase-Wise Edge Cases

| Phase | Edge Cases Handled |
|-------|-------------------|
| **Phase 0 — Setup** | Secrets not committed; config validation |
| **Phase 1 — Ingestion** | EC-05 (store), EC-07, EC-08, EC-11 |
| **Phase 2 — Clean & Embed** | EC-01, EC-05, EC-06, EC-12, EC-19, EC-20 |
| **Phase 3 — Cluster & Groq** | EC-02, EC-03, EC-04, EC-14, EC-15, EC-16 |
| **Phase 4 — Synthesis & Validate** | EC-09, EC-10, EC-13, EC-18 |
| **Phase 5 — Dashboard** | EC-04 (view), EC-10 (badge), EC-17 |

---

## 5. Pipeline-Stage Edge Cases

| Stage | Edge Cases | Key Behavior |
|-------|------------|--------------|
| **1. Filter** | Duplicates, bots, empty text, star-only, review-bomb | Exclude with audit log; never delete raw |
| **2. Preprocess** | Emoji-heavy, very short sentences, multi-language | Sentence-level split; retain metadata |
| **3. Clean** | HTML, logistics, Hinglish, competitor mentions, category aliases | Tag and normalize; controlled vocabulary |
| **4. Embed** | Empty segments, logistics-only (configurable skip), cache miss | BGE batch + SHA-256 cache |
| **5–7. Groq Label** | Sarcasm, long text, JSON failure, merged-call violation | 1 call/cluster; truncate; retry |
| **8. Search-Gap** | Non-English wish phrases, sparse matches | BGE-only; TF-IDF labels; no Groq |
| **9. Theme Extract** | Taxonomy version drift | Versioned taxonomy; skip re-label if unchanged |
| **10. Synthesis** | Conflicts, stale evidence, low diversity | Separate cards; recency decay; confidence tiers |
| **11. Validate** | Low agreement, missing audit | Log metrics; downgrade confidence |
| **12. Dashboard** | Sentiment leak, verbatim evidence | Paraphrase only; barrier charts |

---

## 6. Data-Quality & Content Edge Cases

| Scenario | Handling | Discard? |
|----------|----------|----------|
| Exact duplicate review | Exclude from pipeline | No — logged in audit |
| Near-duplicate (paraphrase) | Treated as separate unless hash matches | No |
| Bot/template spam | Exclude from pipeline | No — logged |
| Empty text | Exclude from embed/LLM | No — raw retained |
| Star-only | Skip embed/LLM | No — rating stats only |
| Logistics-only complaint | Tag; exclude from discovery clusters | No |
| Off-topic (not Blinkit) | Optional keyword filter at ingest | Log only |
| Non-English (non-Hinglish) | `language="excluded"`; log % | No — raw retained |
| Single-word review ("Good") | Pass through; may cluster as low-signal | No |
| ALL CAPS / excessive punctuation | Normalize in Clean | No |

---

## 7. ML / LLM Edge Cases

| Scenario | Model | Handling |
|----------|-------|----------|
| Per-segment Groq calls requested | Groq | **Blocked** — cluster first; 1 call/cluster |
| Four separate calls for barrier/funnel/competitor/price | Groq | **Blocked** — merged `CrossShoppingFrictionAnalysis` |
| Embedding same text twice | BGE-small | SHA-256 cache hit — skip recompute |
| Cluster centroid similarity > 0.90 | BGE-small | Merge clusters pre-Groq to reduce redundant calls |
| Taxonomy unchanged on re-run | Groq | Skip re-labeling; reuse cached analysis |
| Groq rate limit / timeout | Groq | Retry with backoff; log failed clusters |
| BGE OOM on large batch | BGE-small | Reduce batch size 128 → 64 → 32 |
| HDBSCAN all noise | HDBSCAN | Fallback to KMeans with K=20 |
| Search-gap with <5 matches | BGE + regex | Skip cluster; log as insufficient |
| Validation 10% sample all agree | Groq | Upgrade confidence where platform rule also met |

---

## 8. Validation Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Agreement rate < 50% | Show actual % in dashboard; do not claim "validated" |
| Human audit fail on high-confidence insight | Downgrade to medium; log in audit table |
| Insight with 1 platform only | Cannot be `high` confidence (requires ≥2 platforms) |
| Conflicting insights same theme | Both kept; linked; not averaged |
| Stale insight (>12 months) | `is_stale=True`; deprioritized; badge shown |
| Re-run produces different barriers | Expected — log both runs; show agreement rate |
| Empty validation sample | Skip agreement calc; warn in run summary |
| All clusters unlabeled (Groq outage) | Pipeline fails gracefully; no insight cards generated |

---

## 9. Dashboard & API Edge Cases

| Scenario | Handling |
|----------|----------|
| Filter returns zero insights | Empty state message; suggest broadening filters |
| Reddit-only filter + rating filter | Disable rating filter (no ratings on Reddit) |
| Insight with no paraphrased snippets | Hide evidence drill-down; show "evidence unavailable" |
| Stale insight in default sort | Ranked lower via recency decay |
| `% negative` requested by old client | API returns 400 or strips field |
| Large insight corpus (1000+ cards) | Paginate `/api/insights`; default page size 20 |
| Concurrent filter combinations | All filters AND-combined; document in API |
| Missing validation run data | Validation panel shows "No validation run yet" |
| Review-bomb flagged run | Overview warning banner |

---

## 10. Operational & Infrastructure Edge Cases

| Scenario | Handling | Phase |
|----------|----------|-------|
| `GROQ_API_KEY` missing | Fail fast at pipeline start with clear error | 3 |
| ChromaDB corruption | Rebuild from embedding cache + metadata DB | 2 |
| Disk full during raw ingest | Fail ingest; do not partial-write without run_id | 1 |
| Partial pipeline run (crash mid-stage) | Resume from last completed stage via `run_id` | All |
| Taxonomy version bump | Re-label all clusters; new `taxonomy_version` tag | 3 |
| Manual CSV malformed | Schema validation error; reject file with line numbers | 1 |
| Embedding model version change | Cache miss for all; full re-embed | 2 |
| Groq call count > 1.2 × clusters | Alert in logs — merged-call rule may be violated | 3 |

---

## 11. Risk Register (Edge-Case Related)

| Risk | Impact | Likelihood | Mitigation | Edge Case IDs |
|------|--------|------------|------------|---------------|
| Groq merged-call rule violated | High cost | Medium | Unit test + runtime counter | EC-14, EC-16 |
| Insufficient review corpus | Weak insights | Medium | Multi-source + manual CSV | EC-08 |
| Reddit/Twitter API blocked | Missing sources | High | Manual corpus; Play/App primary | EC-08 |
| HDBSCAN too many noise points | Few clusters | Medium | Tune params; KMeans fallback | EC-15 |
| Groq JSON parse failures | Missing labels | Medium | Retry + log unlabeled | EC-14 |
| Low inter-run agreement | Low confidence | Medium | Show actual %; tune prompt | EC-18 |
| Dashboard sentiment leak | Spec violation | Low | API lint test | EC-17 |
| Copyright verbatim leak | Legal risk | Medium | Paraphrase + diff test | EC-09 |
| Embedding recompute every run | Slow pipeline | Low | SHA-256 cache | EC-16 |
| Logistics confounding discovery | Wrong insights | High | Tag + exclude from clusters | EC-01 |

---

## 12. Test Coverage Matrix

| Edge Case ID | Unit Test | Integration Test | Manual QA |
|--------------|-----------|------------------|-----------|
| EC-01 | `test_clean.py` | clean_embed stage | Spot-check logistics tags |
| EC-02 | — | Groq sample review | Review sarcasm samples |
| EC-03 | `test_cluster.py` | cluster_label stage | Niche theme visible in dashboard |
| EC-04 | `test_clean.py`, `test_groq_schema.py` | Full pipeline | Competitor view |
| EC-05 | `test_clean.py` | Run summary | Overview excluded % |
| EC-06 | `test_filter.py` | Ingest burst | Overview banner |
| EC-07 | `test_normalizer.py` | Reddit ingest | Filter UI without rating |
| EC-08 | Mock 429 test | Manual fallback ingest | Metadata panel |
| EC-09 | `test_paraphrase.py` | Synthesis stage | Evidence drill-down |
| EC-10 | `test_staleness.py` | Full pipeline | Stale badge in UI |
| EC-11 | `test_record_id_stability.py` | Re-ingest | Audit log |
| EC-12 | `test_filter.py` | clean_embed | Overview KPI |
| EC-13 | `test_conflict_policy.py` | Synthesis | Segment view |
| EC-14 | `test_groq_schema.py` | Mock failure | Audit log |
| EC-15 | `test_cluster.py` | cluster_label | — |
| EC-16 | — | Long review test | Token log |
| EC-17 | `test_api_no_sentiment.py` | API E2E | UI walkthrough |
| EC-18 | `test_validation.py` | Full pipeline | Validation panel |
| EC-19 | `test_clean.py` | Forum ingest | — |
| EC-20 | `test_preprocess.py` | — | — |

---

## 13. Explicitly Out of Scope

These scenarios are **not handled** by the review analyzer dashboard (documented to avoid scope creep):

| Scenario | Reason |
|----------|--------|
| Real-time streaming ingestion | Batch-only architecture |
| Full multilingual NLP beyond English + Hinglish | Current language scope |
| In-app product changes or feature rollout | Analysis and dashboard only |
| Paid social-listening tools (Brandwatch, Sprinklr) | Cost / scope |
| Automated sarcasm detection model | Groq handles at cluster level |
| Image / video review content | Text-only pipeline |
| Private Blinkit internal data | Public feedback only |
| User PII redaction beyond paraphrase | Paraphrase mitigates; no dedicated NER PII pipeline |

---

## Appendix: Edge Case → Research Question Mapping

| Edge Case | Affected RQs | Notes |
|-----------|--------------|-------|
| EC-01 Logistics confounding | RQ2, RQ3, RQ6 | Must exclude to answer discovery questions |
| EC-04 Competitor contamination | RQ1, RQ4 | Feeds competitor benchmarking |
| EC-03 Niche themes | RQ7, RQ8 | Low volume but high signal |
| EC-13 Conflicting insights | RQ7 | Segmentation signal |
| EC-10 Stale insights | All | Recency affects all RQs |
| EC-05 Hinglish | RQ7 | Indian user segments |

---

*Document version: 1.0 — aligned with implementation-plan.md and architecture.md*
