# quotes-api

A tiny in-memory "quotes" REST API used as the vehicle for a complete GitHub Actions
CI/CD pipeline: lint → test → build a Docker image → push it to GHCR → auto-deploy to
a Render staging service → deploy the *same* image to production only after a human
approves it.

The app itself is intentionally minimal. The pipeline is the point.

## Live services

- Staging: https://quotes-api-staging.onrender.com/quotes
- Production: https://quotes-api-production.onrender.com/quotes

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/quotes` | List all quotes |
| `POST` | `/quotes` | Create a quote (`{"text": str, "author": str}`) → `201` |
| `GET` | `/quotes/{id}` | Fetch one quote by id → `200` or `404` |

Interactive docs are available at `/docs` on any running instance (FastAPI's built-in
OpenAPI UI).

Storage is a plain in-memory list (`app/store.py`) — nothing persists across a
container restart. That's deliberate: this project is about the pipeline, not a
database.

## Running locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Then visit http://localhost:8000/docs.

## Running the tests

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

## Running in Docker

```bash
docker build -t quotes-api:local .
docker run -p 8000:8000 quotes-api:local
curl http://localhost:8000/quotes
```

## The pipeline

```
git push to main
   │
   ▼
CI (.github/workflows/ci.yml)
   lint ──┐
          ├──► build (Docker → GHCR, tagged with commit SHA + latest)
   test ──┘
   │
   ▼  (workflow_run trigger)
CD (.github/workflows/cd.yml)
   deploy-staging (automatic)
          │
          ▼
   deploy-production (needs: deploy-staging, environment: production
                       — paused until a required reviewer approves)
```

The same Docker image, tagged with the triggering commit's SHA, is deployed to both
staging and production — nothing is rebuilt between environments. That's what makes
this continuous *delivery*, not just "deploy from source twice."

### Required GitHub configuration

Two GitHub Environments must exist (`staging`, `production`), each with:

- `RENDER_API_KEY` — a Render API key
- `RENDER_STAGING_SERVICE_ID` / `RENDER_PRODUCTION_SERVICE_ID` — the corresponding
  Render service's `srv-...` id

`production` additionally requires a reviewer configured under its protection rules —
that single setting is what makes `deploy-production` pause for approval.

### Render configuration

Two Render Web Services, each configured to deploy an existing image from a registry
(`ghcr.io/<owner>/cicd-project`), not to build from source. The GHCR package is
**private** — Render authenticates to pull it using a reusable Workspace-level
**Container Registry Credential** (Registry: GitHub Container Registry, Username:
the GitHub owner, Personal Access Token: a classic PAT scoped to `read:packages`
only, with an expiration set — not "No expiration"). That credential is attached to
both `quotes-api-staging` and `quotes-api-production` under each service's settings.

CI still pushes to GHCR using the workflow's automatic `GITHUB_TOKEN` regardless of
the package's visibility — only the *pull* side (Render) needs a credential; the
*push* side (CI) always has one implicitly.

## Project docs

- [`docs/superpowers/specs/2026-07-09-toy-cicd-pipeline-design.md`](docs/superpowers/specs/2026-07-09-toy-cicd-pipeline-design.md) — the original design spec
- [`docs/superpowers/plans/2026-07-09-toy-cicd-pipeline.md`](docs/superpowers/plans/2026-07-09-toy-cicd-pipeline.md) — the task-by-task implementation plan, including notes on what changed after code review
