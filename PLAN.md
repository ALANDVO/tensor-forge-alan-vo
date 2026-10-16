# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

cli-forge-core

## Roadmap

### cli-forge-core — CLI Forge: AST-based CLI command forging from Python source

Status: done

Acceptance:
- POST /api/forge with Python source returns a manifest of callable entry points with typed argument schemas
- Each generated command is executable shell syntax: program <name> [--flag value]...
- Argparse/argparse.parse_args call sites are detected as real entry points
- Malformed source returns a 422 with a safe error message, never a 500
- Unsupported-language input is rejected with 422

Implementation: `backend/app/services/parser.py`, `backend/app/services/forge.py`, `backend/app/api/forge.py`

Tests: `backend/tests/test_forge_engine.py`, `backend/tests/test_api.py`

### cli-forge-frontend — CLI Forge dashboard: paste source, view forged commands, export

Status: done

Acceptance:
- Form to paste Python source and submit
- Results rendered as copyable shell commands
- Export as JSON button works

Implementation: `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/components/ForgeForm.tsx`, `frontend/src/components/ForgeResult.tsx`

Tests: `frontend/src/App.test.tsx`

### forge-persistence — Save, list and retrieve forged manifests in SQLite

Status: done

Acceptance:
- POST /api/forges saves a forge result
- GET /api/forges lists saved forges with pagination
- GET /api/forges/{id} returns a saved forge

Implementation: `backend/app/models/db.py`, `backend/app/api/forge.py`

Tests: `backend/tests/test_api.py`

### auth-oidc — OIDC Keycloak SAML-brokering authentication and role authorization

Status: planned

Acceptance:
- state+nonce+PKCE authorization code login through Keycloak
- viewer/operator/admin roles enforced on data endpoints
- SAML identity brokering documented

### llm-advisory — Opt-in LLM advisory explanations with provider adapters

Status: planned

Acceptance:
- LLM_API_KEY only credential; OpenAI/Anthropic/Gemini/Ollama adapters
- Advisory label, bounded timeouts, redacted errors, never fabricated success

### multi-language — Support JS/TS, Go and Rust source targets

Status: planned

Acceptance:
- ES/TS AST or parser service extracts entry points
- Go/Rust function recovery via go/parser and syn

