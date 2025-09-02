"""RouteWise AI - Main CLI entrypoint
Provides direct access to MCP workflow via simple command line interface.
For enhanced interactive CLI, use: python -m src.clients.cli_client
"""
from __future__ import annotations

import argparse
from src.utils.logger import get_logger
from src.orchestrator.router import MCPRouter


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for main entrypoint"""
    p = argparse.ArgumentParser(
        description="RouteWise AI - Travel Planning with MCP Agents",
        epilog="For interactive mode: python -m src.clients.cli_client"
    )
    p.add_argument("query", type=str, help="Travel query, e.g., 'Delhi to Jaipur, 2 days, budget'")
    p.add_argument("--no-save", action="store_true", help="Do not save outputs to files")
    return p.parse_args()


def main():
    logger = get_logger("main")
    args = parse_args()
    router = MCPRouter()
    md = router.route(args.query, save=(not args.no_save))
    print("\n=== Final Itinerary (Markdown) ===\n")
    print(md)


if __name__ == "__main__":
    main()