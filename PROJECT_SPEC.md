# AI Resume & Career Intelligence Platform — Project Spec

> Source of truth: the target README for this repository. This spec restates it
> verbatim where possible; anything below the "Derived requirements" heading is
> an interpretation added for implementation and is marked as such.

## Overview

An evidence-grounded resume/job-description analysis platform for two audiences:

- **Job Seekers** — upload a resume + a job description and get a job-fit score,
  matched/missing skills with evidence, a learning roadmap, and a mock interview
  with AI feedback — plus multi-role career intelligence, resume quality checks,
  an ATS/recruiter preview, and external evidence checks (GitHub, LinkedIn).
- **Job Providers / Recruiters** — set a job description once, then upload and
  compare multiple candidate resumes against it using the exact same analysis
  engine.

Every score and claim is grounded in real extracted text, not invented. When AI
is unavailable (no key, `DEMO_MODE`, or a provider failure), every feature
degrades to an honest, clearly-labeled deterministic fallback instead of
guessing — the app never fabricates a fact about a candidate.

## Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite, PyMuPDF/python-docx for parsing,
  Sentence Transformers for local semantic matching, and the Google Gen AI SDK
  (Gemini) for AI-assisted extraction/generation.
- **Frontend**: React + Vite (JavaScript), axios, recharts, lucide-react.

## Setup

> Target platform is **Windows / PowerShell only**. The commands below are the
> README's setup steps translated to PowerShell; the maintained copy lives in
> `README.md`.

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and fill in `GOOGLE_API_KEY` (get one free, no billing
required, at https://aistudio.google.com/apikey) to enable live AI features.
Leaving it blank, or setting `DEMO_MODE=true`, runs the app fully in its
deterministic fallback mode — useful for development without a key.

```powershell
uvicorn main:app --reload
```

The API serves at `http://localhost:8000`; `/health` reports whether AI is
configured.

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env   # only needed if the backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### Tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

The test suite never makes live AI or network calls — every AI/network
dependency is mocked so tests are deterministic and free to run.

## Feature map

| Area | What it does |
|---|---|
| Resume/JD parsing | PDF, DOCX, TXT resumes; TXT/pasted-text job descriptions only |
| AI structured analysis | Extracts skills/experience/education with quoted evidence, never invented |
| Skill matching & scoring | Exact/literal/semantic evidence matching, priority-weighted job-fit score |
| Learning roadmap & interview prep | Per-gap roadmap with a real YouTube search link; mock interview questions |
| Interview answer feedback | AI evaluates a typed practice answer and suggests one follow-up question |
| Career intelligence | Radar of fit across common role profiles, plus a career trajectory timeline |
| Resume intelligence | Bullet quality/quantification checks, an AI rewrite workspace with before/after |
| ATS / recruiter view | Raw-parse preview, JD↔resume keyword diff, heuristic 6-second scan |
| External evidence | GitHub profile/language check, manual LinkedIn consistency check, fairness scan |
| Job Provider mode | One job description, many candidates, same engine, side-by-side comparison |

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.

---

## Derived requirements (interpretation, not in the README)

These follow directly from the README's promises and should hold in every phase:

1. **Evidence invariant** — any skill/experience/education item surfaced to the
   user carries a quote that is a substring of the extracted resume text. AI
   output whose quote cannot be located in the source is dropped, not shown.
2. **Fallback labeling** — every API response that could involve AI includes a
   field indicating how it was produced (`sources`: extraction `ai`/`fallback`, semantic
   `enabled`/`disabled`/`unavailable`, plus plain-language notices), and the UI
   shows that label visibly.
3. **AI gating** — AI is used only when `GOOGLE_API_KEY` is set **and**
   `DEMO_MODE` is not `true`; provider errors fall back per request rather than
   failing the request.
4. **Test isolation** — Gemini, Sentence Transformers model download, GitHub
   API, and any HTTP call are behind injectable interfaces so `pytest` runs
   offline.
5. **Score disclaimer** — every score display includes the "application-generated
   estimate, not an official ATS or hiring decision" label.
6. **Single engine** — Job Provider mode calls the same analysis service as the
   Job Seeker flow; no separate scoring path.
7. **JD input restriction** — job descriptions accept `.txt` upload or pasted
   text only; other formats are rejected with a clear error.

## Approved decisions

- Curated skill taxonomy (375 skills in Phase 1) stored as JSON (fallback extraction and
  validation of AI output).
- No authentication; single local SQLite database.
- Frontend verification is a build check only (`npm run build`); no Vitest for now.
- Windows / PowerShell is the only supported development platform for docs.

## Build phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Skeleton: FastAPI + SQLite + `/health`, React/Vite status page, env examples | Done |
| 1 | Parsing + deterministic extraction/matching/scoring, first end-to-end UI | Done |
| 2 | Gemini provider layer, AI structured analysis, semantic matching | Done |
| 3 | Learning roadmap, interview questions, answer feedback | Done |
| 4 | Resume intelligence, ATS/recruiter view | Done |
| 5 | Career intelligence (role radar, trajectory timeline) | Done |
| 6 | External evidence (GitHub, LinkedIn, fairness scan) | Done |
| 7 | Job Provider mode | Done |
| 8 | Hardening and final README | Done |
