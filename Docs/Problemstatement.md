# Problem Statement: Blinkit Review Analyzer Dashboard

## Context

Blinkit users repeat-buy same categories (groceries, snacks, essentials) and rarely cross-shop adjacent categories (pet, baby, personal care). This project is a **review analyzer dashboard**: it mines public feedback to explain why, surfaces validated causal insights in filterable views, and does **not** output raw sentiment scores or serve as a throwaway prototype.

---

## Tech Constraints (fixed)

| Component | Choice |
|-----------|--------|
| **LLM inference** | Groq API (fast, cheap — use for classification/synthesis calls, not embeddings) |
| **Embeddings** | BGE-small (local/lightweight — for semantic clustering, theme dedup, RAG retrieval) |

### Token Efficiency (required)

- Chunk text before embedding (sentence-level, not full-review)
- Truncate/summarize long reviews pre-LLM-call
- Batch embedding requests
- Cache embeddings to avoid recompute
- Use embeddings for clustering/routing and reserve Groq LLM calls only for final labeling/synthesis (not per-sentence) to minimize token spend

### Single Merged-Call Rule (critical)

`cognitive_barrier`, `funnel_leak_stage`, `competitor_entity/advantage`, and `price_sensitivity_detected` are four fields but must be extracted in **one Groq call per cluster**, not four separate calls — the Pydantic schema below is the structured-output contract for that single call (Groq supports JSON-mode/function-calling; request the full `CrossShoppingFrictionAnalysis` object in one response).

> **Never loop the same cluster through the LLM multiple times for different fields.** This keeps cost at 1 call/cluster regardless of how many classification dimensions are added later.

---

## Research Questions

Every insight must map to ≥1 of the following:

| ID | Question |
|----|----------|
| **RQ1** | Why same-category repeat buying? |
| **RQ2** | What blocks new-category exploration? |
| **RQ3** | How do users discover products today? |
| **RQ4** | Role of habit (reorder/"regulars")? |
| **RQ5** | What info/trust builds confidence to try new category? |
| **RQ6** | Recurring frustrations (any category)? |
| **RQ7** | Which segments experiment more? |
| **RQ8** | Recurring unmet needs? |

---

## Data Sources

- Play Store reviews
- App Store reviews
- Reddit (posts + comments, keyword search)
- Twitter/X (fallback: manual sample if API-limited)
- Forums / Quora

**Normalize all to one schema before processing; never discard raw text.**

---

## Pipeline (fixed order)

### 1. Filter
Remove spam/bot/template/duplicate/empty-content reviews; keep star-only/no-text entries but log separately.

### 2. Preprocess
Sentence-level split (not doc-level), emoji-aware, retain metadata (platform, rating, date, url).

### 3. Clean
Strip HTML/markdown noise; map category mentions to controlled vocabulary (e.g. `"dog food"` → `pet_supplies`); tag delivery/logistics-only content separately from discovery-relevant content.

### 4. Embed
BGE-small on cleaned sentence segments → vector store for clustering / theme dedup / semantic search-gap analysis (RAG). Batch + cache.

> **Implementation note:** Embed **`embed_text`** (enriched with category/competitor prefix), not raw text. Short records (<280 chars) use a single segment. Dual-track clustering (discovery + search-gap) runs in parallel — see [architecture.md](./architecture.md).

### 5. Friction Classification (replaces basic sentiment)
Sentiment alone ("negative") doesn't explain why. Each cluster is classified into a `user_cognitive_barrier` (see schema below) instead of, or alongside, positive/negative/neutral. This directly answers RQ2 / RQ5 / RQ6 / RQ8 with causal reasons, not just polarity.

### 6. Funnel Leak Stage Tagging
Classify where cross-shop intent broke down:

| Stage | Description |
|-------|-------------|
| `DISCOVERY` | Didn't know category existed |
| `CONSIDERATION` | Browsed, brand/variant missing |
| `CONVERSION` | Added to cart, backed out — price/fee |
| `POST_PURCHASE_RETENTION` | Bought once, distrust after |

Directly answers **RQ3**.

### 7. Competitor Benchmarking (NER + comparative extraction)
Detect competitor mentions (Amazon, Nykaa, Myntra, Zepto, Instamart) and extract the triplet:

`[Blinkit category]` → `[competitor]` → `[competitor advantage: assortment/price/trust/delivery]`

Feeds RQ1 / RQ4 (habitual lock-in elsewhere).

### 8. Search-Gap Clustering
Embed "wish it had X" / "couldn't find X" phrasings via BGE-small, cluster to surface **Inventory Void** themes (e.g., repeated requests for stationery, kids' toys) — directly answers **RQ8**.

> **Note:** Steps 5–7 are logically distinct fields but are extracted together in **one Groq call per cluster** using the `CrossShoppingFrictionAnalysis` schema below — not as three separate LLM passes. Step 8 (search-gap) is embedding-only and needs no LLM call at all.

### 9. Theme Extraction
Cluster via embeddings first (cheap), then one Groq LLM call per cluster (not per record) to assign `user_cognitive_barrier` + theme label + RQ tags. Maintain versioned taxonomy for consistency.

### 10. Insight Synthesis
Aggregate `cognitive_barrier` + `funnel_leak_stage` + `competitor_advantage` + frequency + source-diversity + segment into insight cards (schema below). Rank by frequency × cross-source corroboration × recency.

### 11. Validate
See [Validation](#validation-must-be-demonstrable-not-claimed) section.

### 12. Dashboard
Render insight cards, filterable.

---

## Pydantic Data Contract

Per-segment classification, used in Steps 5–7:

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field

class CrossShoppingFrictionAnalysis(BaseModel):
    user_cognitive_barrier: Literal[
        "AWARENESS_DEFICIT",      # didn't know category existed
        "AUTHENTICITY_DISTRUST",  # fake/refurbished/duplicate fear
        "ASSORTMENT_GAP",         # searched, brand/variant not found
        "CONVENIENCE_MISMATCH",   # category doesn't fit 10-min urgency use-case
        "RETURN_POLICY_ANXIETY",  # unclear return/replace/defective handling
        "NONE_GROCERY_LOYAL"      # regular buyer, no cross-shop intent shown
    ] = Field(description="Primary cognitive reason blocking cross-shop action")

    funnel_leak_stage: Literal[
        "DISCOVERY", "CONSIDERATION", "CONVERSION", "POST_PURCHASE_RETENTION"
    ]

    competitor_entity: Optional[str] = None       # e.g. "Nykaa", "Amazon"
    competitor_advantage: Optional[Literal[
        "ASSORTMENT", "PRICE", "TRUST", "DELIVERY_SPEED", "RETURN_POLICY"
    ]] = None

    price_sensitivity_detected: bool = Field(
        description="True if user explicitly compares Blinkit price vs Amazon/Flipkart/local store"
    )
```

---

## Insight Card Schema (fixed output contract)

```json
{
  "insight_id": "...",
  "statement": "...",
  "related_RQs": [],
  "theme_tags": [],
  "evidence_count": 0,
  "source_diversity": 0,
  "cognitive_barrier_split": {},
  "dominant_funnel_leak_stage": "...",
  "competitor_mentions": [
    { "entity": "...", "advantage": "...", "count": 0 }
  ],
  "example_snippets": [],
  "confidence_tier": "high|medium|low",
  "segment_relevance": []
}
```

| Field | Description |
|-------|-------------|
| `cognitive_barrier_split{}` | % per barrier type — replaces plain `sentiment_split` |
| `example_snippets[]` | Paraphrased, max 3 |
| `confidence_tier` | `high` \| `medium` \| `low` |

---

## Validation (must be demonstrable, not claimed)

- Sample re-run through second extraction pass → log agreement/disagreement rate
- Human spot-audit of random insight sample → pass/fail logged, shown in dashboard
- **High confidence** requires ≥2 distinct source platforms corroborating
- Flag insights >12 months old as potentially stale
- Conflicting insights on same theme: keep both, don't average (signals segmentation, RQ7)

---

## Dashboard Requirements

| View | Description |
|------|-------------|
| **Overview** | Corpus size, source mix, cognitive-barrier distribution |
| **Insight Explorer** | Filter by RQ / theme / barrier-type / funnel-stage / confidence / segment |
| **Cognitive Barrier Chart** | e.g., "72% of Electronics friction = Return Policy Anxiety, 18% = Authenticity Distrust" |
| **Funnel Leak Stage Breakdown** | Discovery / Consideration / Conversion / Post-Purchase |
| **Competitor Benchmarking** | Top competitor + advantage per category |
| **RQ-Mapped View** | Top insights per RQ1–8 |
| **Segment View** | Segment-level insight breakdown |
| **Evidence Drill-Down** | Paraphrased only |
| **Validation Panel** | Agreement %, audit results |

### Key Reframe

> The dashboard should **never** show plain "X% negative" — it must show which **cognitive barrier** and which **funnel stage** is driving friction, per category.

---

## Edge Cases to Handle

| Edge Case | Handling |
|-----------|----------|
| Delivery/logistics complaints confounding discovery signal | Tag, don't discard |
| Sarcasm / mixed sentiment | Handle in classification pipeline |
| Low-volume-but-high-signal niche themes | Don't discard for low frequency |
| Cross-platform comparison contamination | Blinkit vs Zepto/Instamart mentions |
| Hinglish / code-mixed text | Log excluded %, don't silently drop |
| Review-bombing / spam spikes | Detect, flag separately |
| Missing metadata | Reddit has no star rating — sentiment from text only |
| API rate limits | Documented manual-fallback corpus |
| Copyright | Paraphrase only, never verbatim reproduction |
| Stale insights | From now-fixed UX issues — flag accordingly |

---

## Out of Scope (for this review analyzer dashboard)

- Real-time streaming ingestion
- Full multilingual NLP beyond English + Hinglish
- In-app product changes, experiments, or feature rollout (analysis only)
- Paid social-listening tools

---

## Deliverables

1. **Architecture** — ingestion → clean → embed → cluster → Groq-label → synthesize → store → dashboard, specifying where BGE-small vs. Groq is invoked
2. **Phased build plan** — schema/ingestion → clean/embed → theme analysis → validation → dashboard
3. **Edge-case handling matrix** — mapped to list above
4. **Token-cost notes** — where embeddings replace LLM calls, where batching/caching applies
5. **Review analyzer dashboard** — all nine filterable views with validation metrics
