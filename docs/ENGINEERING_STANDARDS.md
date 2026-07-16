# Digital Rakshak Engineering Standards

## 1. Coding & Type Conventions
- **Strict Typing:** All Python code MUST use strict type hints (`typing.Dict`, `typing.Optional`, or modern Python 3.10+ syntax `dict | None`).
- **Interfaces First:** Define abstract base classes (`abc.ABC`) or `Protocols` in `backend/shared/contracts/` before writing concrete implementations.
- **Data Transfer Objects (DTOs):** Use Pydantic models for all data crossing layer boundaries (API -> RAIC -> Capability -> RIE). No raw dictionaries.

## 2. Folder Structure Conventions
- **`backend/core/`**: Configuration, logging, global exceptions, and dependency injection wiring.
- **`backend/shared/`**: Enums, constants, events, and context classes that are universally accessed.
- **`backend/raic/`**: Agents, orchestration logic, and workflow graphs. (Business logic).
- **`backend/rie/`**: Runtimes and hardware interfacing. (No business logic).

## 3. Naming Conventions
- **Classes:** PascalCase (e.g., `ThreatAgent`, `InvestigationContext`).
- **Interfaces:** Prefix with `I` (e.g., `IThreatRuntime`, `IAgent`).
- **Variables/Functions:** snake_case (e.g., `execute_pipeline`, `agent_result`).
- **Events:** Past tense PascalCase indicating what happened (e.g., `InvestigationStarted`, `EvidenceUploaded`).

## 4. Error Handling
- Never return generic HTTP 500 exceptions from agents.
- Raise specific domain exceptions defined in `backend/shared/exceptions/` (e.g., `AgentExecutionError`, `RuntimeUnavailableError`).
- The `API` layer uses global exception handlers to map these domain exceptions to standard HTTP status codes.

## 5. Event Driven Architecture
- Direct function calls between distinct domains are discouraged.
- State changes MUST emit a strongly typed event via the Event Bus.
- Components subscribe to events (e.g., `CommandCenter` listens for `ThreatCompleted`).

## 6. Git Strategy
- **Master Branch:** Production-ready code ONLY.
- **Develop Branch:** Integration branch.
- **Feature Branches:** Forked from `develop`, prefixed with `feature/` (e.g., `feature/architecture-v3`).
- **Commits:** Follow conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`).
