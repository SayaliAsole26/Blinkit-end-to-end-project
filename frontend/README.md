# Blinkit Review Analyzer — Frontend (Vercel)

Static dashboard from Google Stitch export. Deployed to Vercel; data from Railway FastAPI.

## Pages

| Route | File | Stitch source |
|-------|------|---------------|
| `/` | `public/index.html` | `overview_dashboard` |
| `/insights` | `public/insights.html` | `insight_explorer` |
| `/barriers` | `public/barriers.html` | `cognitive_barrier_chart` |
| `/evidence` | `public/evidence.html` | `evidence_drill_down_panel` |

## Local dev

**Terminal 1 — API**
```powershell
$env:PYTHONPATH="src"
$env:BLINKIT_DATA_DIR="data"
$env:INSIGHTS_RUN_ID="run_phase4_final"
$env:CORS_ORIGINS="http://localhost:3000"
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000 (API wired to http://localhost:8000)
```

Live pages: `/` (Overview), `/insights.html` (Insight Explorer).

## Deploy

See [Docs/deployment-plan-frontend-vercel.md](../Docs/deployment-plan-frontend-vercel.md).

Vercel settings:
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `public`
