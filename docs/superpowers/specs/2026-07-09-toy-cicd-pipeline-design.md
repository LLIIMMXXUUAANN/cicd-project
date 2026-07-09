# Toy CI/CD Pipeline — Design Spec

Date: 2026-07-09

## Purpose

A learning project to build a real, working CI/CD pipeline end-to-end using GitHub Actions,
covering: automated testing, linting, containerized builds, artifact registries, multi-environment
deployment, and a manual approval gate before production. The app itself is intentionally trivial —
it exists only to give the pipeline something real to test, build, and deploy.

Scope is capped at: lint → test → build → push image → deploy staging (auto) → deploy production
(manual approval gate). Anything beyond that (rollback automation, canary releases, a standing QA
environment, matrix builds) is an explicit stretch goal, not part of this spec.

## Architecture Overview

```
Push to feature branch / PR
   └─▶ CI workflow: lint → test   (fast feedback, no build)

Push/merge to main
   └─▶ CI workflow: lint → test → build+tag Docker image → push to GHCR
        └─▶ CD workflow (triggered on CI success via workflow_run):
              deploy-staging (auto, no gate)
                 → Render API: point staging service at new image tag, deploy
              deploy-production (needs: deploy-staging)
                 → gated by GitHub Environment "production" (required reviewer)
                 → Render API: point prod service at the *same* image tag, deploy
```

Key principle: one image, built once, tagged with the git SHA, promoted unchanged from
staging → production. Nothing is rebuilt between environments — that is what makes this
"continuous delivery" rather than "deploy from source twice."

## The App

A minimal "quotes" REST API — no persistence layer, in-memory list only. This keeps the project
focused on the pipeline rather than on database/data-modeling concerns.

- `GET /quotes` — list all quotes
- `GET /quotes/{id}` — get one quote
- `POST /quotes` — add a quote

Stack: FastAPI + uvicorn (gives free OpenAPI docs at `/docs`, useful for demoing after deploy).

## Repo Structure

```
cicd-project/
├── app/
│   ├── main.py          # FastAPI app + routes
│   └── models.py        # Pydantic Quote model
├── tests/
│   └── test_quotes.py   # pytest — unit tests on the model, integration tests via TestClient
├── Dockerfile
├── pyproject.toml       # deps + ruff config, managed with uv
├── .dockerignore
└── .github/
    └── workflows/
        ├── ci.yml
        └── cd.yml
```

## Testing Strategy

- **Unit tests**: validate the `Quote` Pydantic model in isolation (no HTTP).
- **Integration tests**: exercise the FastAPI endpoints via `TestClient` (e.g. POST a quote, then
  GET it back by id).
- **No standing "test environment"**: tests run inside the ephemeral GitHub Actions runner — a
  fresh VM spun up per job and destroyed after. This ephemeral runner *is* the CI part of "CI/CD";
  there is no persistent server dedicated to running tests.
- Local verification before pushing: `uv run pytest`, `uv run ruff check .`, plus a local
  `docker build` + `docker run` to hit the API on localhost — so app bugs and CI/YAML bugs aren't
  debugged simultaneously.

## CI Workflow (`ci.yml`)

Triggers: `push` (all branches) and `pull_request` into `main`.

Jobs:
1. **lint** — checkout, `uv sync`, `ruff check .` and `ruff format --check .`
2. **test** — checkout, `uv sync`, `pytest` (runs in parallel with lint)
3. **build** — `needs: [lint, test]`, only runs
   `if: github.ref == 'refs/heads/main' && github.event_name == 'push'` (skipped on PRs)
   - Docker build, tag as `ghcr.io/<owner>/quotes-api:<git-sha>` and also `:latest`
   - Push to GHCR using the automatic `GITHUB_TOKEN` (no extra secret required for this step)

Every PR gets fast lint+test feedback. Only merges to `main` produce a deployable image.

## CD Workflow (`cd.yml`)

Triggers: `workflow_run`, fires after `ci.yml` completes successfully on `main`. This guarantees CD
only ever runs against a commit that already passed lint, test, and build.

Jobs:
1. **deploy-staging** — `environment: staging` (no protection rules, deploys immediately)
   - Calls Render's API: update the staging service's image reference to
     `ghcr.io/<owner>/quotes-api:<git-sha>`, trigger deploy
   - Polls Render's API briefly to confirm the deploy actually succeeded (not just "triggered")
2. **deploy-production** — `environment: production` (protected, requires manual reviewer approval)
   - `needs: deploy-staging`
   - Same API call pattern against the prod service, using the *same* image tag staging just got

**Secrets** (set via GitHub → Settings → Environments, scoped per-environment so PR builds/forks
never see them):
- `RENDER_API_KEY`
- `RENDER_STAGING_SERVICE_ID`
- `RENDER_PRODUCTION_SERVICE_ID`

**Approval gate**: configured in the GitHub UI, not YAML — Settings → Environments →
"production" → Required reviewers. When `deploy-production` reaches that job, it pauses and shows
a "Review deployments" button in the Actions tab until approved.

## Error Handling

Deliberately minimal — no auto-rollback, since that's a stretch goal, not core to the learning
objective:

- Lint/test failure → `build` never runs (blocked via `needs:`), nothing deploys.
- Build/push failure → CD never triggers (its `workflow_run` trigger only fires on CI success).
- Render API call failure (bad service ID, expired key, etc.) → job fails visibly in the Actions
  tab; re-run manually after fixing.
- Staging succeeds but production deploy fails after approval → staging is already on the new
  version, production stays on the old version until fixed and re-approved. This is an acceptable,
  realistic failure mode to observe once.

## Environments Summary

| Env | Persistent? | Trigger | Purpose |
|---|---|---|---|
| CI runner | No (ephemeral) | every push/PR | lint, unit + integration tests, build |
| Staging | Yes (Render service) | auto, on CI success on `main` | verify the real deployed artifact before prod |
| Production | Yes (Render service) | manual approval, after staging | real (toy) production |

## Explicit Non-Goals (Stretch Goals, Not In Scope)

- Automatic rollback on failed production deploy
- A standing QA/dev environment separate from staging
- Canary or blue/green deployment
- Matrix builds across multiple Python versions
- Dependency caching tuning
