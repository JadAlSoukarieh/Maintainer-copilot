from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from maintcopilot_api.services.report_service import ReportSummaryService

router = APIRouter(tags=["reports"])


@router.get("/reports/summary")
def reports_summary() -> dict:
    repo_root = _repo_root()
    return ReportSummaryService(repo_root).summary()


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "artifacts").exists() and (parent / "reports").exists():
            return parent
    return current.parents[5]
