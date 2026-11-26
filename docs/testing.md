# Testing, Security and DevOps

This document covers contribution area 6: how SentinelAI is tested, what the CI pipeline checks,
the dependency and container security review, and how to verify a fresh setup.

## 1. Test suites

| File | Cases | What it proves |
|---|---:|---|
| `backend/tests/test_policy.py` | 4 | Original smoke tests for the policy engine (clean profile, reproducibility, prompt-injection in descriptions). |
| `backend/tests/test_api.py` | 6 | Original API flow tests: seeding, filters, review tool traces, approval workflow, exports. |
| `backend/tests/test_rules.py` | 47 | Every rule GOV-001 … GOV-010 has a positive and a negative case, plus boundaries (exactly 90 vs 91 days stale, naive timestamps, missing owner variants), exact score arithmetic, the 100-point cap, risk-level thresholds, audit fields on each finding and deterministic output. |
| `backend/tests/test_evaluation_dataset.py` | 15 | Runs the independently labelled `data/evaluation_cases.json` cases through the engine. A missed rule (false negative) or an extra rule (false positive) fails the specific case. Also checks the dataset covers all ten rules. |
| `backend/tests/test_security.py` | 57 | Input validation (IDs, enums, list sizes, unknown fields, query bounds, SQL-looking input), approval-workflow abuse (apply before approval, after rejection, double decisions, invalid decisions, mismatched changes, disabling approvals), CORS, CSV formula-injection protection, and the guarantee that the optional Ollama layer can never change scores or findings and falls back safely on every failure mode. |
| **Total** | **129** | |

Shared fixtures live in `backend/tests/conftest.py`:

- `client` gives a FastAPI `TestClient` on a fresh in-memory SQLite database seeded with the 36 synthetic agents, with `OLLAMA_URL` cleared so no test reaches a real model.
- `make_profile(**overrides)` builds a clean low-risk agent profile for rule tests.
- `new_agent(**overrides)` creates a synthetic agent through the API.

Ollama is never contacted in tests; `httpx.post` is replaced with fakes that simulate a good answer,
a hostile answer that tries to change scores, a connection error, non-JSON text, a JSON array and a
`null` recommendation list.

## 2. Running the checks locally

From the repository root, with the virtual environment active:

```powershell
python -m pip install -r requirements-dev.txt     # app + pytest-cov, pip-audit, bandit
python scripts/check_setup.py                     # verify Python, packages, Node, ports, files
python -m pytest backend/tests -q                 # all tests
python -m pytest backend/tests -q --cov=backend/app --cov-report=term-missing   # with coverage
python scripts/run_evaluation.py                  # regenerate reports/evaluation/results.json
pip-audit -r requirements.txt                     # known-vulnerability scan (core API)
bandit -r backend/app backend/gradio_app.py scripts -ll   # static security analysis
cd frontend; npm ci; npm run build; npm audit --audit-level=high
```

Run a single file or test with `python -m pytest backend/tests/test_security.py -q` or
`-k "gov006"`.

## 3. Continuous integration

`.github/workflows/ci.yml` runs on every push to any branch, on every pull request into `main`, and on demand (Actions tab → CI → Run workflow).

| Job | Steps | Fails the build when |
|---|---|---|
| **Backend tests** (Python 3.10, 3.12, 3.13) | install `requirements-dev.txt`, `check_setup.py --backend-only`, pytest with coverage, `run_evaluation.py`, upload `coverage.xml`, `pytest-report.xml` and `results.json` as artifacts | any test fails, or an evaluation workflow check fails |
| **Frontend build** (Node 22) | `npm ci`, `npm run build` (TypeScript check + Vite build) | type errors or build errors |
| **Security scans** | `pip-audit` on the core requirements, `pip-audit` on the optional Gradio requirements (report only), Bandit at medium severity and above, `npm audit --audit-level=high` | a known vulnerability in core Python packages, a medium/high Bandit finding, or a high/critical npm advisory |
| **Docker build and smoke test** | `docker compose build`, start the API, wait for its health check, call `/api/health` and `/api/ready` (expects 36 agents), confirm the container is not running as root, Trivy image scan (report only), tear down | an image fails to build, the API is not healthy, or it runs as root |

`.github/dependabot.yml` opens weekly update PRs for pip and npm packages and monthly PRs for
GitHub Actions and Docker base images, so CI re-checks every dependency bump.

## 4. Security review results

Reviewed on 2026-11-04 against commit `ed697d5`, and re-checked after the Area 2 merges (commit `5f5d9f1` on 2026-11-19 and `d895fa3` on 2026-11-26).

### Dependency scan

| Scope | Before | After | Change |
|---|---|---|---|
| Python core API (`requirements.txt`) | 3 vulnerable packages: **gradio 4.44.1** (43 advisories), **pillow 10.4.0** (66, pulled in by Gradio 4), **pytest 8.4.2** (2) | **0 known vulnerabilities** | Gradio moved to the optional `requirements-gradio.txt`; pytest raised to `>=9.0.3`. The API and its Docker image no longer install Gradio or Pillow. |
| Optional Gradio dashboard (`requirements-gradio.txt`) | as above | Gradio upgraded to `>=6.16` (fixes all Gradio 4.x/5.x advisories). **Pillow 12.x advisories remain**: Gradio 6 requires `pillow<13`, and the fixes are in Pillow 13. | **Accepted risk**: the dashboard binds to `127.0.0.1`, has no image upload or image processing, and is optional. CI reports this scan without failing. Re-check when Gradio allows Pillow 13 (Dependabot will open the PR). |
| Frontend (`npm audit`) | 0 vulnerabilities | 0 vulnerabilities | Six packages were declared as `"latest"`. They are now pinned to the exact lockfile versions with caret ranges, so installs are reproducible and Dependabot can track them. |
| Static analysis (Bandit) | 2 low-severity notes (subprocess use in `run_evaluation.py`) | 0 medium/high. Low-severity notes only: the same subprocess notes, plus `random` in Area 2's synthetic data generator | Accepted: fixed argument list, `sys.executable`, no shell; `random` only produces synthetic demo data, never secrets or tokens. |

### Code and configuration review

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | The Ollama prompt could not be serialised (`created_at` datetimes in findings made `json.dumps` raise), so the optional narrative mode **always** fell back silently and never actually ran. | Medium (functional) | **Fixed** in `review.py` (`default=str`) and covered by `test_llm_cannot_change_scores_or_findings`. |
| 2 | A model reply that was valid JSON but not an object (e.g. a list) crashed `/api/reviews` with a 500. A reply with a bad `recommendations` value mixed model text into a report still labelled `deterministic_fallback`. | Medium | **Fixed**: object check, and model text is only adopted after the whole reply parses. Covered by `test_llm_failures_fall_back_to_deterministic_report`. |
| 3 | Model-written `summary` and `recommendations` are shown to analysts without grounding checks (scores and findings are already protected). | Low | **Documented** for the AI Agent and RAG area. Consider rejecting recommendations that do not map to a finding's remediation. |
| 4 | Both containers ran as `root`. | Medium | **Fixed**: the API runs as uid 10001 (`sentinel`), the frontend as the image's `node` user. CI asserts the API uid is not 0. |
| 5 | The Docker build context included `.git`, `.venv`, `node_modules` and the local database. | Low | **Fixed** with `.dockerignore`. |
| 6 | `gradio_app.py` returned a dict with string keys for three output components, so the dashboard errored on load. | Low (functional) | **Fixed**: it now returns one value per output. |
| 7 | A Playwright artifact (`frontend/test-results/.last-run.json`) was committed. | Info | **Removed** and ignored. |
| 8 | No authentication; reviewer names are free text, so attribution can be spoofed. | Info | **Documented** limitation (local, synthetic MVP; see `docs/security.md`). |
| 9 | `LIKE` wildcards (`%`, `_`) in search text are not escaped, so they act as wildcards. | Info | Documented. Values are still bound parameters (no SQL injection, see `test_search_text_is_treated_as_data_not_sql`). |

Already in place and now covered by tests: Pydantic bounds on every input, a localhost-only
Ollama endpoint, a CORS allow-list for the local dashboard, CSV formula-injection escaping, and
approval plus separate confirmation before any simulated change.

## 5. Verifying a fresh setup

`scripts/check_setup.py` checks:

- the Python version (3.10+) and an active virtual environment
- the required backend packages, with the optional Gradio package reported separately
- the required repository files
- Node.js (20.19+ or 22.12+, which Vite 8 requires) and npm
- whether the frontend dependencies are installed
- whether ports 8000 and 5173 are free
- whether `OLLAMA_URL` points to a local endpoint

It prints `[OK]`, `[WARN]`, `[FAIL]` or `[INFO]` per check and exits with code 1 if any required check fails.

Docker users upgrading from an earlier build: the API container no longer runs as root. If an old
`sentinel-data` volume was created by the root container, recreate it once with
`docker compose down -v` (this deletes only the local synthetic database).
