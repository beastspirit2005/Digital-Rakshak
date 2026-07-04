# ADR 001: Use Redis Streams for Event Bus

## Status
Accepted

## Context
Digital Rakshak requires a high-throughput, low-latency messaging system to decouple the 12 AI agents from the core API gateway and database transaction layers. We need a way to orchestrate asynchronous background tasks (like updating Neo4j or PostGIS) without blocking the primary investigator workflow. 

Options considered:
- RabbitMQ
- Apache Kafka
- Redis Streams

## Decision
We will use **Redis Streams** as our primary event bus. We will define a strict **Event Catalog** (e.g., `case.created`, `threat.verified`) rather than free-form keys.

## Rationale
1. **Infrastructure Footprint**: We already require Redis for session management, OTP rate-limiting, and caching. Re-using it for Streams prevents us from having to deploy and maintain a heavy Kafka cluster or Erlang-based RabbitMQ instance.
2. **Performance**: Redis operates entirely in memory (with RDB/AOF persistence), providing sub-millisecond latencies perfect for fast AI orchestration.
3. **Consumer Groups**: Redis Streams natively supports consumer groups, allowing us to fan-out events (e.g., a single `case.created` event can be independently consumed by the Graph Agent and the Geospatial Agent).

## Consequences
- **Memory Limits**: Unlike Kafka which streams from disk, Redis Streams hold data in memory. We must strictly enforce `MAXLEN` caps (e.g., `MAXLEN ~ 10000`) on streams to prevent out-of-memory crashes on the 32GB RAM hardware baseline.
- **Monitoring**: We need to monitor consumer group lag closely to ensure agents are keeping up with the event ingestion rate.
