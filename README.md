# tensor-forge — Alan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


**Problem.** Agentic software agents need reliable, executable CLI commands for every
tool they drive. For new applications the available CLI surface is sparse and
inaccurate, so agents fail and humans spend time hand-fixing commands (upstream
need: generating more complete, more accurate CLIs from a target app's source).
tensor-forge forges **agent-native CLI command manifests** directly from source
code so agents can act on an app immediately.

**Implemented approach (this release).** A deterministic, offline engine parses
Python source with the standard `ast` module, recovers callable entry points
(function definitions, `argparse` call sites, and `__main__` blocks), extracts
typed argument schemas from signatures and annotations, and renders executable
shell command templates. This is program synthesis from code structure: no LLM
key, no network, no training data required.

**Intended user.** Developers and agent-framework maintainers who want a
reproducible CLI surface for a code target, or a baseline to measure CLI
coverage/accuracy against.

> **Round 1 checkpoint.** CLI forging from Python source is implemented and
> tested end-to-end. Authentication, LLM advisory, and multi-language support
> are **planned** milestones — see `PLAN.md` and `STATUS.md`. The app runs in a
> local demo mode by default.

---

## AI/ML evaluation

tensor-forge's implemented ML-adjacent work is **deterministic source-to-CLI
synthesis**: recovering a structured program interface from code structure and
rendering an executable command template per entry point.

- **Data provenance:** the engine consumes the source code you submit (no
  external dataset, no credentials, no network calls).
- **Baseline:** AST-driven argument recovery + shell template rendering (this
  release). Accuracy is bounded by Python `ast` coverage: annotations, defaults,
  `argparse` introspection, and `__main__` detection.
- **Reproducible command:**

  ```bash
  python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
  DATABASE_URL="sqlite:///:memory:" PYTHONPATH=backend \
    .venv/bin/python -c "
import sys; sys.path.insert(0,'backend')
from app.services.forge import ForgeEngine
src = 'def greet(name: str, times: int = 1, verbose: bool = False) -> str:\\n    \"\"\"Greet a person.\"\"\"\\n    return name\\n'
r = ForgeEngine().forge(src, 'myapp')
for c in r.commands: print(c.rendered)
"
  ```
  ```
  myapp greet <NAME> [--times <VALUE>] [--verbose]
  ```

- **Measured results:** backend test suite passes (30 tests) covering domain
  recovery, argument typing, argparse detection, malformed/unsupported input
  rejection, persistence, and the real HTTP boundary. Frontend build typechecks
  and 3 component tests pass. No LLM was invoked; no numbers were measured
  via an external model.
- **Failure cases / limitations:** Python-only in this release; anonymous /
  `*args, **kwargs` parameters are not expanded into typed args; boolean flags
  render as `--flag`/`--no-flag` toggles; no authentication yet (see Security).

---

## Features

- `POST /api/forge` — analyze pasted Python source and return a forged CLI
  manifest (stateless compute).
- Manifest per entry point: command name, kind, docstring, argument schema
  (name, Python type, CLI type, required/default, help), and a rendered shell
  command template.
- `POST /api/forges` / `GET /api/forges` / `GET /api/forges/{id}` — persist and
  retrieve forged manifests in SQLite with an audit log.
- Responsive React + TypeScript + Vite dashboard: paste source, forge, copy
  commands, and export the manifest as JSON.
- Deterministic offline engine — works without any LLM key.

Planned: OIDC/Keycloak SAML brokering, opt-in LLM advisory explanations,
multi-language source support.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │                Browser (frontend)            │
                    │  React + TS + Vite  (typed API client)        │
                    └───────────────┬──────────────────────────────┘
                     REST JSON    │
                    ┌─────────────▼──────────────┐
                    │   FastAPI backend          │
                    │   ┌──────────────┐         │
     source  ───────►│   ForgeEngine   │         │
                     │   (ast parser   │         │
                     │    + renderer)  │         │
                     └──────┬──────────┘         │
                            │                     │  ┌──────────────────┐
                            ▼                     │  │ SQLite (forges   │
                    SQLAlchemy models            │  │  + audit_log)     │
                            │                     │  └──────────────────┘
                    ┌───────┴────────┐            │
                    │  /api/forge    │            │
                    │  /api/forges   │            │
                    │  /health       │            │
                    └────────────────┘            │
                    │  pydantic schemas            │
                    └──────────────────────────────┘
```

- `backend/app/main.py` — FastAPI factory `create_app` + lifespan DB init.
- `backend/app/services/parser.py` — AST entry-point recovery.
- `backend/app/services/forge.py` — `ForgeEngine` + command renderer.
- `backend/app/services/audit.py` — audit log writer.
- `backend/app/models/` — SQLAlchemy `Forge`/`AuditLog` + pydantic schemas.
- `backend/app/api/` — routes (`/api/forge`, `/api/forges`, `/health`).
- `frontend/src/` — React dashboard + typed `api.ts` client.

## Install & run

```bash
# backend
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
DATABASE_URL="sqlite:///:memory:" PYTHONPATH=backend .venv/bin/python -m pytest backend/tests
DATABASE_URL="sqlite:///./tensor-forge.db" PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend
cd frontend
npm ci
npm run dev          # http://localhost:5173
npm test
npm run build

# all services (local)
docker compose up --build
```

Or with Docker directly:

```bash
docker build -f backend/Dockerfile -t tensor-forge-backend .
docker build -f frontend/Dockerfile -t tensor-forge-frontend .
docker compose up -d
# frontend: http://127.0.0.1:8080   backend API: http://127.0.0.1:8000
```

## API endpoint reference

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health`                  | Service health. |
| `GET`  | `/`                        | Service info. |
| `POST` | `/api/forge`               | `{source, program_name, language?}` → forge manifest (stateless). |
| `POST` | `/api/forges`              | Forge + persist; returns saved forge detail. |
| `GET`  | `/api/forges`              | List saved forges (`limit`, `offset`). |
| `GET`  | `/api/forges/{id}`         | Forge detail (source + result + audit fields). |
| `GET`  | `/api/audit`               | Recent audit log entries. |

`POST /api/forge` response envelope:
```json
{
  "program_name": "myapp",
  "language": "python",
  "commands": [
    {
      "name": "greet", "kind": "function", "docstring": "Greet a person.",
      "location": "line 1",
      "rendered": "myapp greet <NAME> [--times <VALUE>] [--verbose]",
      "arguments": [
        {"name": "name", "py_type": "str", "cli_type": "string",
         "required": true, "default": null, "help": "Greet a person."}
      ]
    }
  ],
  "error": null
}
```

## Tests

```bash
# backend (30 tests)
DATABASE_URL="sqlite:///:memory:" PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v

# frontend (3 tests)
cd frontend && npm test

# build/typecheck
cd frontend && npm run build
```

Backend covers domain recovery, argument typing, argparse/bool defaults, malformed
and unsupported input (422), SQLite persistence, the audit log, and the real HTTP
boundary via `TestClient`. Frontend covers form render, the forge workflow, and
JSON export.

## Provider configuration

The deterministic core needs **no** LLM key. Opt-in LLM advisory is a planned
milestone; when enabled, only `LLM_API_KEY` is a secret, and `LLM_PROVIDER`,
`LLM_MODEL`, `LLM_BASE_URL` configure the adapter (OpenAI-compatible, Anthropic,
Gemini, Ollama). Errors are bounded and redacted; the core never fabricates.

| Variable | Purpose | Default | Secret? |
|----------|---------|---------|---------|
| `DATABASE_URL` | SQLite path | `sqlite:///./tensor-forge.db` | No |
| `DEMO_MODE` | Local-only demo binding | `true` | No |
| `LLM_PROVIDER` | Advisory model provider | — | No |
| `LLM_API_KEY` | Advisor key (server-side only) | — | **Yes** |
| `LLM_MODEL` | Advisor model | — | No |
| `LLM_BASE_URL` | Advisor base URL | adapter default | No |

## Security limitations

- **Round 1:** no authentication. `auth` = `none` in `portfolio.json`. The app
  binds `127.0.0.1` in demo mode and refuses production deployment until the
  auth milestone. Do **not** expose the default deployment to the public internet.
- **Planned:** OIDC authorization-code login via Keycloak (state + nonce + PKCE)
  with viewer/operator/admin roles. SAML upstream IdPs configured through
  Keycloak identity brokering (realm import documented), not reimplemented natively.
- No credential values are committed; `.env` is git-ignored. See `.env.example`.

## SSO / SAML setup (planned milestone)

To enable once the `auth-oidc` milestone is implemented:

1. Start Keycloak: `docker compose --profile auth up -d keycloak` (localhost:8081).
2. Import the realm from `docs/realm-tensor-forge.json` (provided in the auth
   milestone). The realm exposes `tensor-forge` OIDC client + viewer/operator/admin
   roles.
3. For SAML IdPs (e.g. Azure AD, Okta): configure Keycloak
   **Identity brokering** → add a SAML provider with the IdP metadata URL /
   certificate; map `email`→`email`, set the first login profile to auto-create
   users. No native SAML code lives in tensor-forge — brokering is delegated to
   Keycloak.

## Project layout

```
tensor-forge-alan-vo/
├── backend/
│   ├── app/main.py              # FastAPI create_app()
│   ├── app/core/config.py       # settings
│   ├── app/models/{db,schema}.py
│   ├── app/services/{parser,forge,audit}.py
│   ├── app/api/{forge,health}.py
│   ├── backend/tests            # 30 pytest tests
│   └── backend/requirements.txt
├── frontend/                    # React + TS + Vite
│   ├── src/{App,api,components,main, index.css}
│   └── frontend/tests/App.test.tsx
├── compose.yml                  # backend + frontend + Keycloak (auth profile)
├── pyproject.toml
├── portfolio.json
└── CHANGELOG.md
```

## License

MIT — see `LICENSE`.

---

*Alan Vo* — <alanvo@gmail.com> · GitHub `ALANDVO` · AI & Machine Learning.