# Team Contributions

Use this template to record actual work completed. Do not claim work that was not performed.

| Team member | Role | Work completed | Evidence / files | Date |
|---|---|---|---|---|
|  | Project Lead and Architect |  |  |  |
|  | Data and Policy Engine |  |  |  |
|  | AI Agent and RAG |  |  |  |
|  | Frontend and Backend Integration |  |  |  |
<<<<<<< HEAD
|  | Testing and Security |  |  |  |
=======
|  | Testing and Security | GitHub Actions CI (backend tests on Python 3.10/3.12/3.13 with coverage, evaluation run, frontend build, pip-audit, npm audit, Bandit, Docker build + smoke test + Trivy); Dependabot; 119 new test cases (rule-level, labelled dataset, API security, approval-workflow abuse, Ollama output safety); dependency review (removed 3 vulnerable packages from core requirements, pinned frontend deps); non-root Dockerfiles and .dockerignore; setup checker; fixes for Ollama prompt serialisation, malformed model replies and Gradio dashboard outputs. Prepared with AI coding assistance (Claude) and reviewed by the team member. | `.github/workflows/ci.yml`, `.github/dependabot.yml`, `backend/tests/conftest.py`, `backend/tests/test_rules.py`, `backend/tests/test_evaluation_dataset.py`, `backend/tests/test_security.py`, `scripts/check_setup.py`, `requirements*.txt`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`, `docs/testing.md` | 2026-11-04 |
>>>>>>> 4f3f30c (feat:Phase 6 -Testing, Security and DevOps)

## Collaboration Notes

- Record decisions made jointly and who contributed to them.
- Update this document during the project rather than reconstructing contributions at submission time.
