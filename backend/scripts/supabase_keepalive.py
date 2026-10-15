#!/usr/bin/env python3
"""
Digital Rakshak — Supabase Anti-Pause Heartbeat Script.

Executes an authenticated ping against Supabase Storage and Auth services
to prevent free-tier projects from pausing after 7 days of inactivity.

Usage:
    python backend/scripts/supabase_keepalive.py
    python backend/scripts/supabase_keepalive.py --loop --interval 43200
"""

import argparse
import asyncio
import datetime
import os
import sys
import time

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from runtime.supabase_keepalive import supabase_keepalive


async def main() -> None:
    parser = argparse.ArgumentParser(description="Supabase Anti-Pause Keep-Alive Utility")
    parser.add_argument("--loop", action="store_true", help="Run continuously as a daemon")
    parser.add_argument("--interval", type=int, default=43200, help="Loop interval in seconds (default: 43200 / 12h)")
    args = parser.parse_args()

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Digital Rakshak Supabase Keep-Alive Tool")
    print(f"Project Ref : {supabase_keepalive.project_ref}")
    print(f"Restore URL : {supabase_keepalive.restore_url}")
    print("-" * 65)

    if args.loop:
        print(f"Running continuously. Pinging every {args.interval} seconds ({args.interval / 3600:.1f} hours)...")
        await supabase_keepalive.start_daemon(interval_seconds=args.interval)
    else:
        print("Sending instant heartbeat ping to Supabase...")
        res = await supabase_keepalive.ping()
        print(f"Status       : {res.get('status').upper()}")
        print(f"HTTP Status  : {res.get('http_status')}")
        print(f"Latency      : {res.get('latency_ms')} ms")
        print(f"Is Paused?   : {res.get('is_paused')}")
        if res.get("error"):
            print(f"Details      : {res.get('error')}")
        if res.get("is_paused"):
            print(f"ACTION REQ   : Open {res.get('restore_url')} and click 'Restore project'.")
        else:
            print("SUCCESS      : Supabase inactivity timer has been successfully reset!")


if __name__ == "__main__":
    asyncio.run(main())
