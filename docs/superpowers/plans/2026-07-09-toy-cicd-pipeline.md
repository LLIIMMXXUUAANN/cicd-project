# Toy CI/CD Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working "quotes" REST API with a full GitHub Actions CI/CD pipeline: lint + test on every push, Docker build + GHCR push on merge to `main`, auto-deploy to a Render staging service, then a manually-approved deploy of the exact same image to a Render production service.

**Architecture:** FastAPI app with an in-memory `QuoteStore`, tested with pytest via dependency injection (no test pollution between cases). Two GitHub Actions workflows: `ci.yml` (lint/test/build+push) and `cd.yml` (triggered by `ci.yml`'s success on `main`, deploys to Render via its REST API, gated by GitHub Environments).

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pytest, httpx, ruff, uv (dependency management), Docker, GitHub Actions, GHCR (GitHub Container Registry), Render.

Spec: `docs/superpowers/specs/2026-07-09-toy-cicd-pipeline-design.md`

---

## Prerequisites

- `uv` installed (https://docs.astral.sh/uv/getting-started/installation/)
- Docker Desktop installed and running
- `gh` CLI installed and authenticated (`gh auth status` should show a logged-in account)
- A Render account (free tier) — sign up at https://dashboard.render.com if you don't have one yet (needed starting Task 13, not before)

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "quotes-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
    "ruff>=0.7",
]

[tool.pytest.ini_options]
pythonpath = ["."]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- [ ] **Step 2: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 3: Sync dependencies**

Run: `uv sync`
Expected: creates `.venv/` and `uv.lock`, no errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore uv.lock
git commit -m "chore: scaffold project with uv"
```

---

### Task 2: Quote and QuoteCreate models

**Files:**
- Create: `app/__init__.py`
- Create: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from app.models import Quote, QuoteCreate


def test_quote_accepts_valid_fields():
    quote = Quote(id=1, text="Stay hungry", author="Steve Jobs")
    assert quote.id == 1
    assert quote.text == "Stay hungry"
    assert quote.author == "Steve Jobs"


def test_quote_rejects_empty_text():
    with pytest.raises(ValidationError):
        Quote(id=1, text="", author="Steve Jobs")


def test_quote_create_rejects_empty_author():
    with pytest.raises(ValidationError):
        QuoteCreate(text="Stay hungry", author="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'` (or `app` has no attribute `models` — `app/__init__.py` doesn't exist yet either).

- [ ] **Step 3: Create the empty package marker**

`app/__init__.py`: (empty file)

- [ ] **Step 4: Write the model**

`app/models.py`:

```python
from pydantic import BaseModel, Field


class Quote(BaseModel):
    id: int
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)


class QuoteCreate(BaseModel):
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/__init__.py app/models.py tests/test_models.py
git commit -m "feat: add Quote and QuoteCreate models"
```

---

### Task 3: QuoteStore (in-memory storage)

**Files:**
- Create: `app/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:

```python
from app.models import QuoteCreate
from app.store import QuoteStore


def test_new_store_is_empty():
    store = QuoteStore()
    assert store.list() == []


def test_create_assigns_sequential_ids():
    store = QuoteStore()
    first = store.create(QuoteCreate(text="First", author="A"))
    second = store.create(QuoteCreate(text="Second", author="B"))
    assert first.id == 1
    assert second.id == 2


def test_create_adds_to_list():
    store = QuoteStore()
    store.create(QuoteCreate(text="First", author="A"))
    assert len(store.list()) == 1


def test_get_returns_matching_quote():
    store = QuoteStore()
    created = store.create(QuoteCreate(text="First", author="A"))
    found = store.get(created.id)
    assert found is not None
    assert found.text == "First"


def test_get_returns_none_when_missing():
    store = QuoteStore()
    assert store.get(999) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.store'`.

- [ ] **Step 3: Write the store**

`app/store.py`:

```python
from app.models import Quote, QuoteCreate


class QuoteStore:
    def __init__(self) -> None:
        self._quotes: list[Quote] = []
        self._next_id = 1

    def list(self) -> list[Quote]:
        return self._quotes

    def get(self, quote_id: int) -> Quote | None:
        return next((q for q in self._quotes if q.id == quote_id), None)

    def create(self, payload: QuoteCreate) -> Quote:
        quote = Quote(id=self._next_id, text=payload.text, author=payload.author)
        self._quotes.append(quote)
        self._next_id += 1
        return quote
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store.py
git commit -m "feat: add in-memory QuoteStore"
```

---

### Task 4: FastAPI app skeleton + GET /quotes

**Files:**
- Create: `app/main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_store
from app.store import QuoteStore


@pytest.fixture
def client():
    fresh_store = QuoteStore()
    app.dependency_overrides[get_store] = lambda: fresh_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_quotes_empty(client):
    response = client.get("/quotes")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Write the app**

`app/main.py`:

```python
from fastapi import Depends, FastAPI

from app.models import Quote
from app.store import QuoteStore

app = FastAPI()

_store = QuoteStore()


def get_store() -> QuoteStore:
    return _store


@app.get("/quotes")
def list_quotes(store: QuoteStore = Depends(get_store)) -> list[Quote]:
    return store.list()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add FastAPI app with GET /quotes"
```

---

### Task 5: POST /quotes

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_main.py`:

```python
def test_create_quote_returns_201_and_assigns_id(client):
    response = client.post("/quotes", json={"text": "Just do it", "author": "Nike"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["text"] == "Just do it"
    assert body["author"] == "Nike"


def test_created_quote_appears_in_list(client):
    client.post("/quotes", json={"text": "Move fast", "author": "Meta"})
    response = client.get("/quotes")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_main.py -v`
Expected: FAIL with `405 Method Not Allowed` assertion errors (no POST route yet).

- [ ] **Step 3: Add the endpoint**

In `app/main.py`, change the import line and add the new endpoint:

```python
from fastapi import Depends, FastAPI

from app.models import Quote, QuoteCreate
from app.store import QuoteStore

app = FastAPI()

_store = QuoteStore()


def get_store() -> QuoteStore:
    return _store


@app.get("/quotes")
def list_quotes(store: QuoteStore = Depends(get_store)) -> list[Quote]:
    return store.list()


@app.post("/quotes", status_code=201)
def create_quote(payload: QuoteCreate, store: QuoteStore = Depends(get_store)) -> Quote:
    return store.create(payload)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_main.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add POST /quotes"
```

---

### Task 6: GET /quotes/{id}

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_main.py`:

```python
def test_get_quote_by_id_found(client):
    create_response = client.post("/quotes", json={"text": "Ship it", "author": "Amazon"})
    quote_id = create_response.json()["id"]
    response = client.get(f"/quotes/{quote_id}")
    assert response.status_code == 200
    assert response.json()["text"] == "Ship it"


def test_get_quote_by_id_not_found(client):
    response = client.get("/quotes/999")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_main.py -v`
Expected: FAIL with `404` for the first test (route doesn't exist yet, so both return 404 — the "found" case assertion on `response.json()["text"]` fails with `KeyError`/assertion mismatch).

- [ ] **Step 3: Add the endpoint**

In `app/main.py`, update the import and add the new endpoint:

```python
from fastapi import Depends, FastAPI, HTTPException

from app.models import Quote, QuoteCreate
from app.store import QuoteStore

app = FastAPI()

_store = QuoteStore()


def get_store() -> QuoteStore:
    return _store


@app.get("/quotes")
def list_quotes(store: QuoteStore = Depends(get_store)) -> list[Quote]:
    return store.list()


@app.post("/quotes", status_code=201)
def create_quote(payload: QuoteCreate, store: QuoteStore = Depends(get_store)) -> Quote:
    return store.create(payload)


@app.get("/quotes/{quote_id}")
def get_quote(quote_id: int, store: QuoteStore = Depends(get_store)) -> Quote:
    quote = store.get(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_main.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest -v`
Expected: 13 passed (3 model + 5 store + 5 main).

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add GET /quotes/{id}"
```

---

### Task 7: Lint pass

**Files:** (none new — verifying existing files)

- [ ] **Step 1: Run ruff check**

Run: `uv run ruff check .`
Expected: if any issues appear, run `uv run ruff check . --fix` and re-check until clean (`All checks passed!`).

- [ ] **Step 2: Run ruff format check**

Run: `uv run ruff format --check .`
Expected: if it reports files that would be reformatted, run `uv run ruff format .`, then re-run the check until it reports no changes needed.

- [ ] **Step 3: Commit (only if step 1 or 2 changed files)**

```bash
git add -u
git commit -m "style: apply ruff lint/format fixes"
```

---

### Task 8: Dockerfile and local verification

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Write the Dockerfile**

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY app ./app
RUN uv sync --locked --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write .dockerignore**

`.dockerignore`:

```
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.git
docs
tests
```

- [ ] **Step 3: Build the image locally**

Run: `docker build -t quotes-api:local .`
Expected: build completes successfully (`writing image sha256:...`, `naming to docker.io/library/quotes-api:local`).

- [ ] **Step 4: Run the container**

Run: `docker run -d -p 8000:8000 --name quotes-api-local quotes-api:local`
Expected: prints a container ID, no immediate exit.

- [ ] **Step 5: Verify it responds**

Run: `curl http://localhost:8000/quotes`
Expected: `[]`

Run: `curl -X POST http://localhost:8000/quotes -H "Content-Type: application/json" -d "{\"text\": \"Hello Docker\", \"author\": \"Me\"}"`
Expected: JSON body with `"id":1,"text":"Hello Docker","author":"Me"`

- [ ] **Step 6: Stop and remove the local container**

Run: `docker stop quotes-api-local && docker rm quotes-api-local`

- [ ] **Step 7: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "chore: add Dockerfile for containerized deploys"
```

---

### Task 9: Create the GitHub repo and push

**Files:** (none — repo/remote operations)

- [ ] **Step 1: Capture your GitHub username**

Run: `GH_OWNER=$(gh api user --jq .login) && echo "$GH_OWNER"`
Expected: prints your GitHub username. Keep this shell session open — later tasks reuse `$GH_OWNER`.

- [ ] **Step 2: Create the repo and push**

Run:
```bash
gh repo create "$GH_OWNER/cicd-project" --public --source=. --remote=origin --push
```
Expected: repo created at `https://github.com/<GH_OWNER>/cicd-project`, current branch pushed, `origin` remote set.

*(Public visibility is required for the simplest path in Task 12 — Render pulling the built image without needing a registry credential. If you'd rather keep the repo private, Task 12 has a note on the extra Render config that requires.)*

- [ ] **Step 3: Verify**

Run: `gh repo view --web`
Expected: opens the new repo in your browser with the commits you made so far.

---

### Task 10: CI workflow — lint + test

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest -v
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint and test jobs"
git push
```

- [ ] **Step 3: Watch it run**

Run: `gh run watch`
Expected: both `lint` and `test` jobs complete with a green checkmark.

---

### Task 11: CI workflow — build and push to GHCR

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the build job**

Append to `.github/workflows/ci.yml` (same indentation level as `lint:` and `test:` under `jobs:`):

```yaml
  build:
    needs: [lint, test]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Compute lowercase image name
        id: image
        run: echo "name=ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_OUTPUT"
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ steps.image.outputs.name }}:${{ github.sha }}
            ${{ steps.image.outputs.name }}:latest
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add Docker build and GHCR push job"
git push
```

- [ ] **Step 3: Watch it run**

Run: `gh run watch`
Expected: `lint`, `test`, and `build` all complete successfully (this push is to `main`, so `build` should run, not skip).

- [ ] **Step 4: Verify the image exists**

Run: `gh api "/users/$GH_OWNER/packages/container/cicd-project/versions" --jq '.[0].metadata.container.tags'`
Expected: a JSON array containing `latest` and a full commit SHA.

---

### Task 12: Make the GHCR package public

**Files:** (none — GitHub UI configuration)

- [ ] **Step 1: Open package settings**

Run: `gh browse --repo "$GH_OWNER/cicd-project" --settings` won't reach package settings directly — instead open:
`https://github.com/users/$GH_OWNER/packages/container/cicd-project/settings`
(replace `$GH_OWNER` with the value from Task 9, Step 1)

- [ ] **Step 2: Change visibility**

Scroll to "Danger Zone" → "Change visibility" → select **Public** → confirm by typing the package name.

- [ ] **Step 3: Verify**

Run: `curl -s -o /dev/null -w "%{http_code}" "https://ghcr.io/v2/$GH_OWNER/cicd-project/manifests/latest"`
Expected: not `401` (some non-auth-error status — GHCR's anonymous manifest access returns `200`/`404` depending on the exact request, but never `401 Unauthorized`, once the package is public).

*(If you kept the repo private in Task 9, skip this task, and instead configure a registry credential on each Render service in Task 13 using a GitHub Personal Access Token with `read:packages` scope.)*

---

### Task 13: Render — create staging and production services

**Files:** (none — Render dashboard configuration)

- [ ] **Step 1: Get your Render API key**

Go to https://dashboard.render.com/settings/api-keys → "Create API Key" → copy it somewhere safe (you'll paste it into GitHub secrets in Task 14).

- [ ] **Step 2: Create the staging service**

In the Render dashboard: **New** → **Web Service** → **Deploy an existing image from a registry**
- Image URL: `ghcr.io/<GH_OWNER>/cicd-project:latest` (replace `<GH_OWNER>` with your username)
- Name: `quotes-api-staging`
- Instance Type: Free
- Click **Deploy Web Service**

Expected: after the first deploy finishes, the service shows a live URL like `https://quotes-api-staging.onrender.com`.

- [ ] **Step 3: Verify staging responds**

Run: `curl https://quotes-api-staging.onrender.com/quotes`
Expected: `[]`

- [ ] **Step 4: Create the production service**

Repeat Step 2, but:
- Name: `quotes-api-production`

Expected: a second live URL like `https://quotes-api-production.onrender.com`.

- [ ] **Step 5: Record the service IDs**

Run: `curl -s -H "Authorization: Bearer <RENDER_API_KEY>" https://api.render.com/v1/services | jq '.[] | {name: .service.name, id: .service.id}'`
(replace `<RENDER_API_KEY>` with the key from Step 1)
Expected: JSON showing the `srv-xxxxxxxxxxxx` id for both `quotes-api-staging` and `quotes-api-production`. Save both — you'll need them in Task 14.

---

### Task 14: GitHub Environments — staging, production, reviewer, secrets

**Files:** (none — GitHub UI + gh CLI configuration)

- [ ] **Step 1: Create the staging environment**

Run: `gh api --method PUT "repos/$GH_OWNER/cicd-project/environments/staging"`
Expected: JSON response describing the new `staging` environment (no error).

- [ ] **Step 2: Create the production environment**

Run: `gh api --method PUT "repos/$GH_OWNER/cicd-project/environments/production"`
Expected: JSON response describing the new `production` environment.

- [ ] **Step 3: Add a required reviewer to production**

Open `https://github.com/$GH_OWNER/cicd-project/settings/environments` in your browser → click **production** → check **Required reviewers** → add yourself → **Save protection rules**.

- [ ] **Step 4: Add secrets to the staging environment**

Run each (replace the placeholder values with the real key/IDs from Task 13):
```bash
gh secret set RENDER_API_KEY --env staging --body "<RENDER_API_KEY>"
gh secret set RENDER_STAGING_SERVICE_ID --env staging --body "<staging srv- id>"
```

- [ ] **Step 5: Add secrets to the production environment**

```bash
gh secret set RENDER_API_KEY --env production --body "<RENDER_API_KEY>"
gh secret set RENDER_PRODUCTION_SERVICE_ID --env production --body "<production srv- id>"
```

- [ ] **Step 6: Verify**

Run: `gh secret list --env staging` and `gh secret list --env production`
Expected: each shows the two secrets you just set.

---

### Task 15: CD workflow — deploy-staging

**Files:**
- Create: `.github/workflows/cd.yml`

- [ ] **Step 1: Write the workflow**

`.github/workflows/cd.yml`:

```yaml
name: CD

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

jobs:
  deploy-staging:
    if: github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Trigger Render deploy
        id: deploy
        run: |
          IMAGE="ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]'):${{ github.event.workflow_run.head_sha }}"
          RESPONSE=$(curl -s -X POST "https://api.render.com/v1/services/${{ secrets.RENDER_STAGING_SERVICE_ID }}/deploys" \
            -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d "{\"imageUrl\": \"$IMAGE\"}")
          echo "$RESPONSE"
          DEPLOY_ID=$(echo "$RESPONSE" | jq -r '.id')
          if [ -z "$DEPLOY_ID" ] || [ "$DEPLOY_ID" = "null" ]; then
            echo "Could not parse a deploy id from the Render response above — check the field name and adjust the jq filter."
            exit 1
          fi
          echo "deploy_id=$DEPLOY_ID" >> "$GITHUB_OUTPUT"
      - name: Poll deploy status
        run: |
          for i in $(seq 1 30); do
            STATUS=$(curl -s -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
              "https://api.render.com/v1/services/${{ secrets.RENDER_STAGING_SERVICE_ID }}/deploys/${{ steps.deploy.outputs.deploy_id }}" | jq -r '.status')
            echo "status: $STATUS"
            if [ "$STATUS" = "live" ]; then
              exit 0
            fi
            case "$STATUS" in
              build_failed|update_failed|canceled|pre_deploy_failed)
                echo "Deploy failed with status: $STATUS"
                exit 1
                ;;
            esac
            sleep 10
          done
          echo "Timed out waiting for deploy to go live"
          exit 1
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/cd.yml
git commit -m "cd: add staging auto-deploy via Render API"
git push
```

- [ ] **Step 3: Watch CI then CD run**

Run: `gh run watch` (run it twice — once for the `CI` run, then again for the `CD` run it triggers)
Expected: `CI` completes green, then `CD`'s `deploy-staging` job completes green.

- [ ] **Step 4: Verify the first manual response body**

Before trusting the polling loop blindly: open the `deploy-staging` job's logs in the Actions tab and confirm the raw `$RESPONSE` JSON printed in "Trigger Render deploy" actually has an `id` field at the top level. If Render's response nests it differently (e.g. under a `deploy` key), update the `jq -r '.id'` filter in `cd.yml` to match, commit, and push again.

- [ ] **Step 5: Verify staging shows the new deploy**

Run: `curl https://quotes-api-staging.onrender.com/quotes`
Expected: `[]` (still empty in-memory state, since it's a fresh container — but confirms the new image is live and healthy).

---

### Task 16: CD workflow — deploy-production (gated)

**Files:**
- Modify: `.github/workflows/cd.yml`

- [ ] **Step 1: Add the production job**

Append to `.github/workflows/cd.yml` (same indentation level as `deploy-staging:` under `jobs:`):

```yaml
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Trigger Render deploy
        id: deploy
        run: |
          IMAGE="ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]'):${{ github.event.workflow_run.head_sha }}"
          RESPONSE=$(curl -s -X POST "https://api.render.com/v1/services/${{ secrets.RENDER_PRODUCTION_SERVICE_ID }}/deploys" \
            -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d "{\"imageUrl\": \"$IMAGE\"}")
          echo "$RESPONSE"
          DEPLOY_ID=$(echo "$RESPONSE" | jq -r '.id')
          if [ -z "$DEPLOY_ID" ] || [ "$DEPLOY_ID" = "null" ]; then
            echo "Could not parse a deploy id from the Render response above."
            exit 1
          fi
          echo "deploy_id=$DEPLOY_ID" >> "$GITHUB_OUTPUT"
      - name: Poll deploy status
        run: |
          for i in $(seq 1 30); do
            STATUS=$(curl -s -H "Authorization: Bearer ${{ secrets.RENDER_API_KEY }}" \
              "https://api.render.com/v1/services/${{ secrets.RENDER_PRODUCTION_SERVICE_ID }}/deploys/${{ steps.deploy.outputs.deploy_id }}" | jq -r '.status')
            echo "status: $STATUS"
            if [ "$STATUS" = "live" ]; then
              exit 0
            fi
            case "$STATUS" in
              build_failed|update_failed|canceled|pre_deploy_failed)
                echo "Deploy failed with status: $STATUS"
                exit 1
                ;;
            esac
            sleep 10
          done
          echo "Timed out waiting for deploy to go live"
          exit 1
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/cd.yml
git commit -m "cd: add gated production deploy via Render API"
git push
```

- [ ] **Step 3: Watch the run pause for approval**

Run: `gh run watch` (for the new `CD` run triggered by this push's `CI`)
Expected: `deploy-staging` completes, then the run shows `deploy-production` waiting — "Waiting for review".

- [ ] **Step 4: Approve the deployment**

Run: `gh run list --workflow=CD.yml --limit 1 --json databaseId --jq '.[0].databaseId'` to get the run ID, then open it:
`gh run view <run-id> --web`
In the browser, click **Review deployments** → check **production** → **Approve and deploy**.

- [ ] **Step 5: Confirm it completes**

Run: `gh run watch <run-id>`
Expected: `deploy-production` completes green.

- [ ] **Step 6: Verify production responds**

Run: `curl https://quotes-api-production.onrender.com/quotes`
Expected: `[]`

---

### Task 17: End-to-end verification

**Files:**
- Modify: `tests/test_store.py` (trivial addition, to produce a real change to push through the pipeline)

- [ ] **Step 1: Make a small real change**

Append to `tests/test_store.py`:

```python
def test_get_returns_none_for_negative_id():
    store = QuoteStore()
    assert store.get(-1) is None
```

- [ ] **Step 2: Run it locally first**

Run: `uv run pytest tests/test_store.py -v`
Expected: 6 passed.

- [ ] **Step 3: Commit and push to main**

```bash
git add tests/test_store.py
git commit -m "test: add negative id edge case for QuoteStore.get"
git push
```

- [ ] **Step 4: Watch the full pipeline**

Run: `gh run watch` for the triggered `CI` run — expect `lint`, `test`, `build` all green.
Then run: `gh run watch` again for the `CD` run it triggers — expect `deploy-staging` green, then `deploy-production` paused on review.

- [ ] **Step 5: Approve production**

Same as Task 16 Step 4: `gh run view <run-id> --web` → **Review deployments** → approve.

- [ ] **Step 6: Confirm both environments are live and serving traffic**

Run: `curl https://quotes-api-staging.onrender.com/quotes` and `curl https://quotes-api-production.onrender.com/quotes`
Expected: both return `[]` (a fresh container has empty in-memory state — the point of this check is confirming both are up and responding, not persisted data).

At this point you have a complete, working CI/CD pipeline: push → lint/test → build/push image → auto-deploy staging → manually-approved deploy of the exact same image to production.
