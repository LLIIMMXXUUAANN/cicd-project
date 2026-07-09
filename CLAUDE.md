# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository.

## What this project is

A deliberately small FastAPI "quotes" API, built as the vehicle for a complete
GitHub Actions CI/CD pipeline (lint → test → Docker build → GHCR push → auto-deploy
to Render staging → manually-approved deploy to Render production). The app's
simplicity is intentional — do not add features to it beyond what the pipeline
needs to exercise. See `README.md` for the full architecture and
`docs/superpowers/specs/` and `docs/superpowers/plans/` for the original design
rationale and task-by-task history, including what changed after code review.

## Stack

Python 3.12+, FastAPI, uvicorn, pytest, httpx, ruff, `uv` for dependency management.
No database — storage is an in-memory list in `app/store.py`. Do not add a database
or persistence layer without an explicit request; it's out of scope by design.

## Commands

```bash
uv sync                          # install dependencies
uv run uvicorn app.main:app --reload   # run locally
uv run pytest -v                 # run tests
uv run ruff check .              # lint
uv run ruff format --check .     # format check (use `ruff format .` to fix)
```

CI runs exactly these lint/test commands (with `--locked` on `uv sync`) — if they
pass locally, they should pass in CI.

## Structure

```
app/
  models.py   # Quote (id, text, author) and QuoteCreate (text, author — no id)
  store.py    # QuoteStore: in-memory list, list()/get(id)/create(payload)
  main.py     # FastAPI app, 3 endpoints, dependency-injected store via get_store()
tests/
  test_models.py  # unit tests on the Pydantic models
  test_store.py   # unit tests on QuoteStore directly (no HTTP)
  test_main.py    # integration tests via TestClient, using a per-test fresh store
```

**Test isolation matters here**: `tests/test_main.py`'s `client` fixture overrides
`get_store` with a fresh `QuoteStore()` per test via `app.dependency_overrides`. Any
new test that hits the API must use this `client` fixture — instantiating
`TestClient(app)` directly bypasses the override and shares state with other tests.

## The CI/CD pipeline

`.github/workflows/ci.yml` — `lint` and `test` run on every push/PR; `build` (Docker
build + push to GHCR, tagged with the commit SHA and `latest`) only runs on a push
to `main`, after `lint`/`test` succeed.

`.github/workflows/cd.yml` — triggered by `workflow_run` after `ci.yml` completes.
`deploy-staging` runs automatically; `deploy-production` (`needs: deploy-staging`,
`environment: production`) pauses for a required-reviewer approval in GitHub's UI
before running. Both jobs deploy the *same* SHA-tagged image — never rebuild an
image to "promote" it between environments.

If you touch either workflow file, preserve the hardening that's already there:
explicit `curl --max-time 15` timeouts and `if ! X=$(curl ...); then ...; fi`
failure handling (don't rely on bash pipefail defaults inside a `run:` step), the
`concurrency: cd-deploy` group, and `timeout-minutes` on the CD jobs. These were all
added after a real bug was found in review — see the plan doc for the story.

## Secrets

`RENDER_API_KEY`, `RENDER_STAGING_SERVICE_ID`, `RENDER_PRODUCTION_SERVICE_ID` live in
GitHub Environment secrets (`staging` and `production`), never in the repo. Never
suggest hardcoding them, writing them to a `.env` file that gets committed, or
printing them in a workflow step — GitHub masks known secrets in logs, but don't
rely on that as the only protection.

## Working conventions

- Follow TDD for app code: write the failing test, watch it fail, implement, watch
  it pass. The existing tests are the pattern to follow.
- Keep the app's scope to exactly the 3 endpoints (`GET /quotes`, `POST /quotes`,
  `GET /quotes/{id}`) unless explicitly asked to extend it.
- Run `uv run pytest -v` and `uv run ruff check .` before considering any change to
  `app/` or `tests/` complete.
- This repo is public and the GHCR package is public (required for Render to pull it
  without a registry credential) — don't commit anything that shouldn't be visible
  to anyone.
