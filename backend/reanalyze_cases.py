"""
Digital Rakshak - Case Re-Analysis and Graph Rebuilder

PURPOSE:
    Re-runs Groq AI entity extraction on ALL existing cases that have
    missing or empty Neo4j graph data. Rebuilds PhoneNumber, UPI_ID,
    BankAccount, and URL nodes + INVOLVES relationships in Neo4j so
    the Graph Explorer and Spatial Map cluster lines work correctly.

USAGE (run from inside the backend/ folder):

    # Default - only re-analyze cases with zero Neo4j nodes (safe):
    python reanalyze_cases.py

    # Force re-analyze ALL cases (even those with existing graph data):
    python reanalyze_cases.py --force

    # Dry run - print what would happen, make NO actual changes:
    python reanalyze_cases.py --dry-run

    # Only process the N oldest cases:
    python reanalyze_cases.py --limit 50
"""

import asyncio
import argparse
import sys
import os
import re
import json
import httpx
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from core.config import settings
from domain.models.case import Case
from infrastructure.graph.neo4j_client import IntelligenceGraph

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# llama-3.1-8b-instant has much higher rate limits on Groq free tier
GROQ_MODEL         = "openai/gpt-oss-20b"       # Primary: fast, available, good limits
GROQ_FALLBACK      = "qwen/qwen3.6-27b"         # Fallback: better JSON, lower limits
GROQ_API_URL       = "https://api.groq.com/openai/v1/chat/completions"
INTER_REQUEST_WAIT = 4.0    # Seconds between each request
MAX_RETRIES        = 3      # Max retries per model on 429
RETRY_BASE_WAIT    = 8.0    # Base wait on 429 (reads Retry-After header if available)

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
def ok(m):   print("[OK]  " + str(m), flush=True)
def warn(m): print("[!!]  " + str(m), flush=True)
def err(m):  print("[XX]  " + str(m), flush=True)
def info(m): print("[>>]  " + str(m), flush=True)
def head(m): print("\n" + str(m), flush=True)


# ---------------------------------------------------------------------------
# 1. Groq entity extraction (with retry + fallback)
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = (
    "You are an elite Cyber Threat Intelligence Entity Extractor for India. "
    "Analyze the scam report text below and extract ALL identifiable threat entities. "
    "Respond ONLY with raw JSON, no markdown, no explanation. "
    "Use this exact schema: "
    '{"phone_numbers": [], "upi_ids": [], "urls": [], "bank_accounts": [], '
    '"estimated_latitude": 20.5937, "estimated_longitude": 78.9629, '
    '"threat_class": "UPI Fraud", "confidence_score": 0.85} '
    "Empty list [] if no matches. Estimate lat/lng from city/state in text; default Central India. "
    "SCAM TEXT: "
)


async def extract_entities(scam_text: str) -> dict:
    """Call Groq to extract entities. Retries with backoff on 429, falls back to qwen."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured in .env")

    headers = {
        "Authorization": "Bearer " + settings.GROQ_API_KEY,
        "Content-Type": "application/json",
    }

    for model in [GROQ_MODEL, GROQ_FALLBACK]:
        for attempt in range(1, MAX_RETRIES + 1):
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": EXTRACTION_PROMPT + scam_text}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(GROQ_API_URL, headers=headers, json=payload)

                if resp.status_code == 429:
                    retry_after = (
                        resp.headers.get("retry-after")
                        or resp.headers.get("x-ratelimit-reset-requests")
                    )
                    wait = float(retry_after) if retry_after else RETRY_BASE_WAIT * attempt
                    warn("429 on " + model + " attempt " + str(attempt) + "/" + str(MAX_RETRIES)
                         + " - waiting " + str(int(wait)) + "s...")
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                raw  = data["choices"][0]["message"]["content"]
                raw  = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
                result = json.loads(raw)
                if model != GROQ_MODEL:
                    info("Used fallback model " + model)
                return result

            except json.JSONDecodeError as exc:
                warn("JSON parse error on " + model + " attempt " + str(attempt) + ": " + str(exc))
                if attempt == MAX_RETRIES:
                    break
                await asyncio.sleep(2.0)
            except httpx.HTTPStatusError:
                raise  # bubble up non-429 HTTP errors

        if model == GROQ_MODEL:
            warn("Switching from " + GROQ_MODEL + " to fallback " + GROQ_FALLBACK + "...")

    raise RuntimeError("All models and retries exhausted")


# ---------------------------------------------------------------------------
# 2. Write entities to Neo4j
# ---------------------------------------------------------------------------
async def write_to_neo4j(graph: IntelligenceGraph, case_number: str,
                          entities: dict, dry_run: bool) -> int:
    mapping = {
        "PhoneNumber": entities.get("phone_numbers", []),
        "UPI_ID":      entities.get("upi_ids", []),
        "URL":         entities.get("urls", []),
        "BankAccount": entities.get("bank_accounts", []),
    }
    count = 0
    for etype, values in mapping.items():
        for v in values:
            v = str(v).strip()
            if not v:
                continue
            if not dry_run:
                await graph.add_case_entity_link(case_number, etype, v)
            count += 1
    return count


# ---------------------------------------------------------------------------
# 3. Check whether a case already has Neo4j data
# ---------------------------------------------------------------------------
async def already_has_graph_data(graph: IntelligenceGraph, case_number: str) -> bool:
    return len(await graph.get_entities_for_case(case_number)) > 0


# ---------------------------------------------------------------------------
# 4. Backfill coords + confidence â€” uses a FRESH session per case
#    to avoid connection timeout after long Groq waits
# ---------------------------------------------------------------------------
async def backfill_postgres(engine, case_id: str, case_lat, case_lng,
                             case_score, result: dict, dry_run: bool) -> bool:
    changed = False
    lat   = result.get("estimated_latitude")
    lng   = result.get("estimated_longitude")
    score = result.get("confidence_score")

    needs_coords = lat and lng and (case_lat is None or case_lng is None)
    needs_score  = score is not None and case_score is None

    if not needs_coords and not needs_score:
        return False

    changed = True
    if dry_run:
        return changed

    # Fresh session so we never get a stale/closed connection
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            stmt = select(Case).where(Case.id == case_id)
            row  = await session.execute(stmt)
            case = row.scalar_one_or_none()
            if case is None:
                return False
            if needs_coords:
                case.latitude  = float(lat)
                case.longitude = float(lng)
            if needs_score:
                case.threat_confidence_score = float(score)
            await session.commit()
    except Exception as exc:
        warn("DB backfill failed for " + str(case_id) + ": " + str(exc))
        changed = False

    return changed


# ---------------------------------------------------------------------------
# 5. Process a single case (receives plain-dict row, not SQLAlchemy object)
# ---------------------------------------------------------------------------
async def process_case(row: dict, engine, graph: IntelligenceGraph,
                        force: bool, dry_run: bool, stats: dict):
    cn    = row["case_number"]
    pre   = "[DRY] " if dry_run else ""

    if not force and await already_has_graph_data(graph, cn):
        info("SKIP  " + cn + " - already has Neo4j data")
        stats["skipped"] += 1
        return

    if not row["scam_text"] or len(row["scam_text"].strip()) < 10:
        warn("SKIP  " + cn + " - scam_text empty")
        stats["skipped"] += 1
        return

    try:
        result     = await extract_entities(row["scam_text"])
        node_count = await write_to_neo4j(graph, cn, result, dry_run)
        backfilled = await backfill_postgres(
            engine,
            row["id"], row["latitude"], row["longitude"],
            row["threat_confidence_score"], result, dry_run
        )

        phones = result.get("phone_numbers", [])
        upis   = result.get("upi_ids", [])
        urls   = result.get("urls", [])
        banks  = result.get("bank_accounts", [])

        ok(pre + cn
           + " -> phones:" + str(len(phones))
           + " upis:"  + str(len(upis))
           + " urls:"  + str(len(urls))
           + " banks:" + str(len(banks))
           + " | " + str(node_count) + " neo4j nodes"
           + " | coords=" + ("backfilled" if backfilled else "ok"))
        stats["processed"]        += 1
        stats["entities_written"] += node_count

    except httpx.HTTPStatusError as exc:
        err("FAIL  " + cn + " HTTP " + str(exc.response.status_code)
            + ": " + exc.response.text[:120])
        stats["failed"] += 1
    except Exception as exc:
        err("FAIL  " + cn + " " + type(exc).__name__ + ": " + str(exc))
        stats["failed"] += 1


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------
async def main(force: bool, dry_run: bool, limit: int):
    head("=== Digital Rakshak - Case Re-Analysis & Graph Rebuilder ===")
    print("  Primary model : " + GROQ_MODEL)
    print("  Fallback model: " + GROQ_FALLBACK)
    print("  Request delay : " + str(INTER_REQUEST_WAIT) + "s between each case")
    print("  Force         : " + str(force))
    print("  Dry-run       : " + str(dry_run))
    print("  Limit         : " + (str(limit) if limit else "ALL"))
    print("  Started       : " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    graph  = IntelligenceGraph()
    stats  = {"processed": 0, "skipped": 0, "failed": 0, "entities_written": 0}

    # Load ALL case data into plain Python dicts immediately
    # so we never hold an open DB cursor during long Groq waits
    info("Connecting to Postgres to load cases...")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        q = select(Case).order_by(Case.created_at.asc())
        if limit:
            q = q.limit(limit)
        rows  = await session.execute(q)
        cases_orm = rows.scalars().all()
        # Convert to plain dicts â€” no more SQLAlchemy lazy-load risk
        cases = [
            {
                "id":                      str(c.id),
                "case_number":             c.case_number,
                "scam_text":               c.scam_text,
                "latitude":                c.latitude,
                "longitude":               c.longitude,
                "threat_confidence_score": c.threat_confidence_score,
            }
            for c in cases_orm
        ]

    head("Found " + str(len(cases)) + " case(s) to evaluate")

    for i, row in enumerate(cases):
        info("[" + str(i + 1) + "/" + str(len(cases)) + "] " + row["case_number"])
        await process_case(row, engine, graph, force, dry_run, stats)
        if i + 1 < len(cases):
            await asyncio.sleep(INTER_REQUEST_WAIT)

    head("=== Summary ===")
    ok("Processed        : " + str(stats["processed"]))
    info("Skipped          : " + str(stats["skipped"]))
    if stats["failed"]:
        err("Failed           : " + str(stats["failed"]))
    ok("Entities written : " + str(stats["entities_written"]))
    if dry_run:
        warn("DRY-RUN mode - no actual changes were made.")
    print("")
    ok("Done! Refresh the Graph Explorer and Spatial Map to see connections.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-analyze existing cases and rebuild Neo4j graph connections."
    )
    parser.add_argument("--force",   action="store_true",
                        help="Re-analyze ALL cases including those with existing Neo4j data.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making any changes.")
    parser.add_argument("--limit",   type=int, default=0,
                        help="Only process N oldest cases (default: all).")
    args = parser.parse_args()
    asyncio.run(main(force=args.force, dry_run=args.dry_run, limit=args.limit))

