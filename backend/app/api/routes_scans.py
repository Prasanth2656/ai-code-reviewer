import json
from fastapi import APIRouter
from app.database.db import SessionLocal
from app.models.scan_job_model import ScanJob
from app.models.issue_model import Issue

router = APIRouter()

@router.get("/scans/{repo_id}")
def get_scans_for_repo(repo_id: int):
    """Return scan history for a given repository."""
    db = SessionLocal()
    scans = db.query(ScanJob).filter_by(repository_id=repo_id).order_by(
        ScanJob.created_at.desc()
    ).all()

    result = []
    for scan in scans:
        summary = {}
        try:
            summary = json.loads(scan.summary) if scan.summary else {}
        except Exception:
            pass
        result.append({
            "id": scan.id,
            "status": scan.status,
            "summary": summary,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        })

    db.close()
    return result
