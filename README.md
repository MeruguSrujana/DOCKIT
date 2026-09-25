# DOCKIT — SIH26190 Prototype

Case-centric document lifecycle & provenance system for legal and investigation documents.
Team SCRITHM.

This is a real, database-backed implementation of the approved architecture — not a mockup.
Every workflow transition, hash, and audit entry described below was tested against a running
instance before this was written.

((((## Quick start (Docker — matches the deployed architecture)

```bash
docker compose up --build
```

((- Backend API: http://localhost:8000 (docs at /docs)
- Frontend: http://localhost:5173
- Postgres runs inside Docker; the backend seeds demo data automatically on first boot.))

## Quick start (local dev, no Docker — uses SQLite)

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m app.seed        # creates dockit.db + demo users/case
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev)))))
```

## Demo accounts

All seeded with password `Dockit@2026`:

| Username    | Role                    |
|-------------|-------------------------|
| io.sharma   | Investigating Officer   |
| fo.rao      | Forensic Officer        |
| pp.iyer     | Prosecutor              |
| cc.das      | Court Clerk             |
| admin       | Admin / Case Records    |

A single synthetic demo case (`CASE-2026-014`) is seeded with one registered FIR. It is entirely
fictional — see architecture constraint on demonstration data.

## What's genuinely implemented

- **Auth & RBAC**: real JWT auth against DB-stored, hashed passwords. Every mutating endpoint
  checks the caller's role server-side (`app/security.py::ACTION_ROLES`) — the frontend hides
  buttons for convenience only; it is never the authorization boundary.
- **Workflow engine**: real branching state machine (`app/workflow.py`) for both documents and
  evidence. Invalid transitions are rejected with HTTP 409. Verified: `received → under_review`
  (further investigation required) works, and re-approving an already-approved document is
  correctly rejected.
- **Versioning & integrity**: every version is content-addressed with a real SHA-256 hash,
  chained to the previous version's hash. `POST /documents/{id}/versions/{vid}/verify`
  recomputes the hash from the actual stored bytes — this was tested by tampering a file
  on disk directly and confirming the mismatch is detected and logged as an `integrity_failure`
  event.
- **Provenance**: a single append-only `events` table is the sole source of the timeline, the
  audit trail, and the readiness calculation. Nothing UPDATEs or DELETEs a row in that table.
- **Documentary Readiness**: computed live from real document/event state — completeness %,
  pending review count, integrity failure count, and a missing-document-type checklist. This is
  rule-based aggregation, explicitly not AI (see architecture §19/§13 constraints).
- **Evidence linkage**: physical custody chain (collected → sealed → transferred → received →
  examined → report generated → used → archived) linkable to a digital document.
- **Mock adapters**: `/adapters/mock-cctns/receive` and `/adapters/mock-ecourts/send` log a real
  event but do not call any live government system — labeled as such in both the API docstrings
  and the UI.
- **Storage separation**: document content lives in `backend/storage/` (object-storage stand-in),
  metadata lives in Postgres/SQLite. No document content is embedded in the frontend.

## What's intentionally NOT built (per MVP boundary agreed earlier in this project)

- AI-assisted drafting, multilingual UI, offline-first sync, real PKI signatures, and real
  government API integration are all out of scope for this prototype — see the earlier
  MVP-boundary document for the reasoning. Nothing in this codebase pretends otherwise.
- Structured document *templates* exist in the data model and are seeded (`Forensic Examination
  Request`, `Seizure Memo`), but the frontend doesn't yet render a template-driven creation form —
  document creation currently takes freeform title/content. Wiring the template schema into the
  creation form is the next piece of frontend work if you want that feature demoable.
- Search is not yet implemented as an endpoint.

## Architecture correspondence

This implementation follows the blueprint delivered earlier in this project directly:
Client (React) → Access (JWT + CORS) → Application (Case/Document/Evidence/Workflow/Readiness
services, as FastAPI routers within one modular monolith — not microservices) → Data (Postgres +
object storage) → Integration (two mocked adapters). See `DOCKIT_Architecture_Blueprint.mermaid`
from the earlier deliverable for the full diagram.

## Before any real deployment

Change `DOCKIT_SECRET_KEY` and the Postgres password in `docker-compose.yml`. Neither is
suitable for anything beyond a local demo.
