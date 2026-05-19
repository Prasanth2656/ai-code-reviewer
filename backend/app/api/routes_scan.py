import json
import shutil
from fastapi import APIRouter, HTTPException
from app.schemas.scan_schema import ScanRequest
from app.services.github_service import clone_repository
from app.services.parser_service import extract_repo_info
from app.services.analyzer_service import analyze_repository
from app.database.db import SessionLocal
from app.models.developer_model import Developer
from app.models.repo_model import Repository
from app.models.scan_job_model import ScanJob
from app.models.issue_model import Issue

router = APIRouter()

@router.post("/scan")
async def scan_repository(data: ScanRequest):
    db = SessionLocal()
    repo_path = None

    try:
        developer_name, repo_name = extract_repo_info(data.repo_url)

        # --- Clone repository ---
        repo_path = clone_repository(data.repo_url)

        # --- Run AI analysis ---
        summary, issues = analyze_repository(repo_path)

        # --- Persist to DB ---

        # 1. Get or create Developer
        developer = db.query(Developer).filter_by(username=developer_name).first()
        if not developer:
            developer = Developer(username=developer_name)
            db.add(developer)
            db.flush()

        # 2. Get or create Repository
        repository = db.query(Repository).filter_by(
            name=repo_name, developer_id=developer.id
        ).first()
        if not repository:
            repository = Repository(name=repo_name, developer_id=developer.id)
            db.add(repository)
            db.flush()

        # 3. Create ScanJob
        scan_job = ScanJob(
            status="completed",
            summary=json.dumps(summary),
            repository_id=repository.id,
        )
        db.add(scan_job)
        db.flush()

        # 4. Store Issues
        for issue_data in issues:
            issue = Issue(
                file=issue_data.get("file", "unknown"),
                line=issue_data.get("line", 0),
                severity=issue_data.get("severity", "Medium"),
                description=issue_data.get("description", ""),
                fix=issue_data.get("fix", ""),
                scan_job_id=scan_job.id,
            )
            db.add(issue)

        db.commit()

        return {
            "scan_id": scan_job.id,
            "developer": developer_name,
            "repository": repo_name,
            "summary": summary,
            "issues": issues,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
        # Clean up cloned repo
        if repo_path:
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
            except Exception:
                pass