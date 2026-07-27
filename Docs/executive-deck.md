# Blinkit Discovery Engine — Executive Deck
## 10-slide summary · Pipeline run `run_phase4_final`

> **Full report:** [final-discovery-engine-report.md](./final-discovery-engine-report.md)  
> **Live demo:** https://blinkit-end-to-end-project.vercel.app

---

## Slide 1 — Title

**Blinkit Cross-Category Discovery Engine**  
AI-powered analysis of public feedback to explain why users repeat-buy groceries but rarely cross-shop adjacent categories.

**117 validated insights · 800 evidence records · 4 platforms · 82% label agreement**

---

## Slide 2 — The Problem

Blinkit wins on **speed for groceries** but users don't expand into:
- Personal care · Pet supplies · Baby care · Electronics · Home essentials

**Core question:** Why don't users cross-shop — and what would change that?

---

## Slide 3 — What We Built

| Component | Description |
|-----------|-------------|
| **Ingestion** | App Store, Play Store, Reddit, forums → unified schema |
| **Intelligence** | BGE-small clustering + Groq structured labeling |
| **Output** | 117 insight cards mapped to 8 research questions |
| **Validation** | Re-label agreement on held-out sample |
| **Dashboard** | Read-only Vercel UI + Railway API |

**Principle:** Causal barriers, not sentiment scores.

---

## Slide 4 — How It Works (3 steps)

```
GATHER → ANALYZE → DELIVER
 800      Cluster     117 insight
records   + Label     cards +
          (1 Groq      Validation
           call/cluster)
```

1. **Gather** public reviews/posts (880-day window)  
2. **Cluster** semantically (BGE + HDBSCAN), label barriers/funnel/competitors (Groq)  
3. **Synthesize** ranked insight cards; validate on 11-cluster sample  

---

## Slide 5 — Headline Numbers

| Metric | Value |
|--------|-------|
| Insights generated | **117** |
| High confidence | **83 (71%)** |
| Dominant barrier | **Assortment Gap (73%)** |
| Primary funnel leak | **Discovery (66%)** |
| Validation agreement | **82%** overall · **100%** on barriers |

**Bottom line:** Users fail to cross-shop because they **don't know**, **can't find**, or **already buy elsewhere**.

---

## Slide 6 — Research Questions at a Glance

| RQ | Question | #1 Answer |
|----|----------|-----------|
| **RQ1** | Why repeat same categories? | Grocery-only habit; other needs met on Amazon/Nykaa |
| **RQ2** | What blocks exploration? | Limited brands/variants (Assortment Gap) |
| **RQ3** | How do users discover? | Outside Blinkit — friends, competitors, not in-app |
| **RQ4** | Role of habits? | Reorder routines lock grocery; parallel habits elsewhere |
| **RQ5** | What trust info needed? | Assortment proof, authenticity, return policy |
| **RQ6** | Recurring frustrations? | Missing products, hidden categories, search fails |
| **RQ7** | Who experiments more? | New parents, first-time buyers (not grocery loyalists) |
| **RQ8** | Unmet needs? | Personal care, pet, baby, electronics gaps |

---

## Slide 7 — Top 5 Insights (by evidence)

1. **Missing personal care** — 23 mentions · Assortment Gap · Discovery  
2. **Grocery assortment gap** — 22 mentions · 3 platforms  
3. **Limited awareness outside groceries** — 21 mentions · Awareness Deficit  
4. **Vitamins & personal care gap** — 20 mentions · Consideration  
5. **Limited brands & higher prices** — 20 mentions · Consideration  

**Competitors cited most:** Amazon (breadth), Nykaa (personal care), Zepto (grocery)

---

## Slide 8 — Validation (Quality Assurance)

| Field | Agreement |
|-------|-----------|
| Cognitive barriers | **100%** |
| Competitor mentions | **100%** |
| Funnel stage | **82%** |
| **Overall** | **82%** |

- 11 clusters independently re-labeled by Groq  
- 83 high-confidence insights safe for prioritization  
- 34 medium-confidence insights for exploration  

*Visible on dashboard → Validation page*

---

## Slide 9 — Recommendations

1. **Expand personal care & baby assortment** — highest evidence density  
2. **Fix in-app discovery** — 66% of leaks happen before users even browse  
3. **Compete on breadth vs Nykaa/Amazon** — users default there today  
4. **Target new parents & first-time buyers** — least habit-locked segments  
5. **Prioritize high-confidence insights (83)** for roadmap decisions  

---

## Slide 10 — Demo & Next Steps

**Live dashboard:** https://blinkit-end-to-end-project.vercel.app

| View | Shows |
|------|-------|
| Overview | KPIs + top insights |
| Insight Explorer | Filter RQ1–RQ8 |
| RQ Map | Coverage per research question |
| Validation | Agreement rates |

**Next:** Refresh corpus with live 2025–2026 data → `run_phase5_live`

---

*Deck v1.0 · Derived from [full report](./final-discovery-engine-report.md)*
