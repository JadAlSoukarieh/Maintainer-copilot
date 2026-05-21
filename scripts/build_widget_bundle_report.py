#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "services/widget/dist"
REPORT_PATH = REPO_ROOT / "reports/widget_bundle_report.json"


def main() -> int:
    if not DIST_DIR.exists():
        print("Widget dist directory is missing. Run `cd services/widget && npm run build` first.")
        return 1

    assets: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(DIST_DIR.rglob("*")):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total_bytes += size
        assets.append(
            {
                "path": path.relative_to(DIST_DIR).as_posix(),
                "size_bytes": size,
            }
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "dist_dir": str(DIST_DIR.relative_to(REPO_ROOT)),
                "asset_count": len(assets),
                "total_size_bytes": total_bytes,
                "assets": assets,
                "notes": [
                    "Demo mode still serves the widget through the widget service.",
                    "Production path is build dist -> serve via CDN/MinIO/static host -> point /widget.js iframe at that widget URL.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
