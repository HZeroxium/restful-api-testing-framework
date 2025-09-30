# AGENTS — Hexagonal Architecture Guide (Python 3.12, FastAPI + Pydantic + LangGraph/LangChain + ADK + LlamaIndex)

## 1) Baseline Stack

- Runtime: Python 3.12, `venv`.
- Web/API: FastAPI + Uvicorn (dev), Gunicorn+Uvicorn workers (prod).
- Schemas/Config: Pydantic v2 + pydantic-settings (fail fast on missing secrets).
- HTTP: httpx AsyncClient with explicit timeouts, retries (idempotent only), and connection pooling.
- Orchestration: LangGraph (preferred); LangChain integrations where useful; Google ADK for Gemini/Google-centric; LlamaIndex for document-native routing.
- State/Cache: Redis (+ in-process LRU) via `CachePort` implementations.
- Observability: OpenTelemetry (FastAPI + httpx instrumented), structured JSON logs, optional LangSmith/Arize Phoenix traces.
- Testing & Eval: Pytest + pytest-asyncio, contract tests, Ragas/DeepEval for agent quality gates.

## 2) Target Project Layout (hexagonal)

```bash
├─ app/                      # FastAPI edge (routers, deps, DTOs, middleware)
│  ├─ api/
│  │  ├─ routers/
│  │  ├─ deps/
│  │  └─ dto/
│  └─ middleware/
├─ domain/                   # Core: entities, value objects, domain services, ports
│  ├─ entities/
│  ├─ services/
│  └─ ports/
├─ application/              # Use-cases/orchestrators (depend only on ports)
│  ├─ use_cases/
│  └─ services/
├─ adapters/                 # Implementations of ports
│  ├─ http/                  # FastAPI controllers (primary adapter)
│  ├─ rest/                  # httpx REST client(s)
│  ├─ llm/                   # LLM-backed tools (constraint miners, generators)
│  ├─ reporting/             # Reporter/exporters
│  ├─ cache/                 # Redis, file, memory caches
│  └─ logging/               # Logger adapter
├─ infra/                    # Cross-cutting: DI, observability, configs
│  ├─ di/
│  ├─ observability/
│  └─ configs/               # pydantic-settings; env templates
├─ agents/                   # LangGraph graphs, tool policies; depend on ports
├─ shared/                   # Pure utilities (framework-agnostic)
├─ tests/                    # unit, integration, contract, eval
├─ data/                     # specs and fixtures
├─ docs/
└─ scripts/
```

## 3) Ports and Adapters — Core Principles

- Dependency rule: domain → none; application → domain (ports); adapters/edge → application; infra wires dependencies.
- Define interfaces in `domain/ports/` for: `OpenAPIParserPort`, `ConstraintMiningPort`, `TestDataGenerationPort`, `TestScriptGenerationPort`, `TestExecutionPort`, `ReportingPort`, `RestClientPort`, `CachePort`, `LoggerPort`.
- Wrap existing tools from `src/tools/**` as adapters implementing ports. No business logic in adapters.
- Domain models live in `domain/entities/`. API I/O lives in `app/api/dto/`.
- Use-cases in `application/use_cases/` orchestrate by calling ports; they never import concrete adapters.

## 4) Agent Patterns & Guidance

- Agents (LangGraph/LangChain/ADK/LlamaIndex) must call use-cases or ports, not concrete adapters.
- Keep tools small, deterministic where possible, side-effect aware, schema-driven.
- Add safety rails: validate inputs/outputs (Pydantic), redact PII, require approvals for destructive acts.
- Control budgets: cap steps/tokens, parallel tools with limits, deadlines; degrade gracefully with cached/partial results.

## 5) API Edge Policies

- DTOs (request/response) in `app/api/dto/`, validated via Pydantic v2; forbid unknown fields.
- Apply rate limits, payload size caps; standardized problem+json errors.
- Provide `/health/live`, `/health/ready`, `/metrics`. Use backpressure for streaming (SSE/WebSocket).

## 6) Observability

- Auto-instrument FastAPI + httpx. Propagate trace context into agents/tools.
- Add spans: route, tool, tokens_in/out, cost_estimate, cache_hit, retries.
- Redact secrets/PII in logs and traces.

## 7) Testing & Evaluation

- Unit tests for domain services and adapters (mock ports), integration for adapters, contract for API.
- Ragas/DeepEval: smoke in CI on changed components; nightly full eval.

## 8) Security

- OAuth2/JWT, short-lived tokens, rotated keys, scopes via dependencies.
- Tool allowlists; schema-validated arguments; network egress allowlist; no raw shell.
- Secrets via env/secret store only (pydantic-settings in `infra/configs`).

## 9) Migration Notes (from current src/)

- Move `src/schemas/tools/*` → `domain/entities/` (core) and `app/api/dto/` (edge DTOs).
- Move `src/tools/core/*` and `src/tools/llm/*` → `adapters/llm/`, `adapters/rest/`, `adapters/reporting/` implementing ports.
- Move `src/common/logger/*` → `adapters/logging/`; `src/common/cache/*` → `adapters/cache/` behind `CachePort`.
- Orchestrations like `src/api_test_runner.py` → `application/use_cases/` (+ API router in `app/api/routers/`).

## 10) “When in Doubt”

- Present 2 options with trade-offs (latency, cost, reliability, complexity) and recommend one.
- Ship rollback notes and monitoring signals to revisit after rollout.
