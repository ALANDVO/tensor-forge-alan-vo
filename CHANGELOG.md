# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to tensor-forge are recorded here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-16

### Added
- New app: **tensor-forge** — forges agent-native CLI command manifests from
  Python source code via deterministic AST analysis.
- `ForgeEngine`: offline, LLM-free engine that recovers callable entry points
  (function definitions, `argparse` call sites, `__main__` blocks) with typed
  argument schemas and renders executable shell command templates.
- `POST /api/forge` returning a `ForgeResponse` manifest.
- SQLite persistence of saved forges (`POST /api/forges`, `GET /api/forges`,
  `GET /api/forges/{id}`), including source + result + audit trail.
- `GET /health` and `GET /` root endpoints.
- FastAPI application factory (`create_app`) and async lifespan init.
- Frontend: React + TypeScript + Vite dashboard to paste source, forge, view
  commands, copy them, and export the manifest as JSON.
- Dockerized backend and frontend with nonroot users, healthchecks, and
  `compose.yaml` (Keycloak gated behind the `auth` profile for a future
  milestone).
- CI workflow: backend pytest, frontend typecheck/build/test, Docker builds.

### Planned (not implemented this round)
- OIDC Keycloak SAML-brokering authentication and role authorization.
- Opt-in LLM advisory explanations (OpenAI/Anthropic/Gemini/Ollama adapters).
- Multi-language source support (JS/TS/Go/Rust) beyond Python.