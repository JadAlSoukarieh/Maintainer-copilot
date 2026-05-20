#!/usr/bin/env python3
from __future__ import annotations


def main() -> int:
    print("Demo widget DB seeding is intentionally not wired in this helper yet.")
    print("Use API_ENABLE_DEMO_WIDGET_FALLBACK=true for the local widget demo until Postgres seed wiring is added.")
    print("The fallback is limited to public_widget_id=demo-widget and remains disabled by default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
