# ADR 002: Use Neo4j for the Intelligence Graph

## Status
Accepted

## Context
A major component of Digital Rakshak's effectiveness is identifying "Campaigns" — networks of interconnected scam numbers, bank accounts, fake domains, and mule UPI IDs. Relational databases like PostgreSQL can perform recursive queries (CTEs), but they scale poorly when traversing deep networks (e.g., finding the 4th degree connection between a victim and a kingpin).

## Decision
We will deploy **Neo4j Community Edition** as a dedicated Graph Database layer within our broader "Intelligence Graph". It will act as the source of truth for entity relationships (Nodes = Phones, Emails, UPIs, IPs; Edges = Transferred_To, Called, Hosted_On).

## Rationale
1. **Cypher Query Language**: Cypher is specifically designed to pattern-match graph relationships natively, making threat hunting queries highly intuitive.
2. **Performance at Depth**: Neo4j uses index-free adjacency, meaning traversing a relationship takes constant time ($O(1)$) regardless of the total graph size, unlike SQL joins which degrade.
3. **Visualization Support**: Native integration with frontend visualization libraries like Cytoscape.js is robust.

## Consequences
- **Polyglot Persistence Sync**: We must ensure data consistency between PostgreSQL (cases/users) and Neo4j (entities/relationships). This is mitigated by our Redis Stream event bus which async updates the graph.
- **Hardware Profile**: Neo4j Community runs well on our target hardware but requires a dedicated 2GB JVM heap allocation.
