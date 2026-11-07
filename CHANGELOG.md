# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed
- `argparse` entry point extraction in `backend/app/services/parser.py`:
  Implemented `_argparse_entry_points()` to detect `add_argument()` calls and
  extract typed argument schemas. Boolean flags (`store_true`/`store_false`)
  now render as toggles with correct defaults. Positional arguments are
  required by default; optional flags are optional by default. Explicit
  `type=` annotations map to appropriate CLI types (integer, string, etc.).
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