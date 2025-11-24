"""
Manual warm-up entrypoint to prebuild EvidenceSeeker pipelines.

Usage:
    python -m app.scripts.warmup_pipelines [--limit 5]
"""

import argparse
import asyncio

from loguru import logger

from app.core.config import settings
from app.core.warmup import warmup_pipelines


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm EvidenceSeeker pipelines")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of Evidence Seekers to warm (defaults to EVSE_WARMUP_MAX or all)",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    limit = args.limit if args.limit is not None else settings.evse_warmup_max
    logger.info("Starting manual warmup (limit={})", limit or "none")
    await warmup_pipelines(limit=limit)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
