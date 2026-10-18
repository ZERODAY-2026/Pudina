"""Send a short prompt to the configured Gemma backend."""

from __future__ import annotations

import sys

from src.llm import GemmaClient, GemmaClientError


def main() -> int:
    """Generate and print a short response from Gemma."""
    try:
        response = GemmaClient().generate(
            "In one short sentence, explain what a database table is.",
            max_tokens=80,
        )
    except GemmaClientError as exc:
        print(f"Gemma smoke test failed: {exc}", file=sys.stderr)
        return 1
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
