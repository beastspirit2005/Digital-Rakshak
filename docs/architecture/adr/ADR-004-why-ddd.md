# ADR 004: Domain-Driven Design (DDD) & Bounded Contexts

## Status
Accepted

## Context
Digital Rakshak is an enterprise-scale application with complex, overlapping domains (AI orchestration, evidence management, geospatial tracking, user auth). A standard flat MVC architecture would quickly result in highly coupled, fragile code where a change in a database schema breaks the public API.

## Decision
We adopt **Domain-Driven Design (DDD)** combined with strict **Bounded Contexts** and an **API Contract Layer**.

## Rationale
1. **Separation of Concerns**: Infrastructure (databases, SMTP) is completely decoupled from pure Domain business logic (Agent rules, confidence math).
2. **Bounded Contexts**: By isolating the system into explicit contexts (Identity & Access, Case Management, Intelligence, AI Platform, Prevention, Notifications, Administration), teams can scale and operate independently.
3. **API Contracts**: Instead of exposing internal SQLAlchemy or Pydantic domain models directly to the web, we use dedicated API contract schemas (`api/contracts/`). This ensures external stability even if internal domain logic undergoes massive refactoring.

## Consequences
- **Boilerplate**: DDD introduces significant initial boilerplate (Data Transfer Objects, Interfaces, Repositories).
- **Learning Curve**: Developers must strictly follow dependency inversion principles (e.g., Domain layer cannot import Infrastructure layer).
