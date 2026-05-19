from fastapi import APIRouter
from app.database.db import SessionLocal
from app.models.issue_model import Issue

router = APIRouter()

@router.get("/issues/{scan_id}")
def get_issues_by_scan(scan_id: int):
    db = SessionLocal()
    issues = db.query(Issue).filter_by(scan_job_id=scan_id).all()

    result = []
    for issue in issues:
        result.append({
            "id": issue.id,
            "file": issue.file,
            "line": issue.line,
            "severity": issue.severity,
            "description": issue.description,
            "fix": issue.fix
        })

    db.close()
    return result


@router.get("/issue/{issue_id}")
def get_issue(issue_id: int):
    db = SessionLocal()
    issue = db.query(Issue).filter_by(id=issue_id).first()

    if not issue:
        db.close()
        return {"error": "Issue not found"}

    result = {
        "id": issue.id,
        "file": issue.file,
        "line": issue.line,
        "severity": issue.severity,
        "description": issue.description,
        "fix": issue.fix,
        "scan_job_id": issue.scan_job_id
    }

    db.close()
    return result