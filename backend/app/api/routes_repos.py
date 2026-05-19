from fastapi import APIRouter
from app.database.db import SessionLocal
from app.models.repo_model import Repository
from app.models.developer_model import Developer

router = APIRouter()

@router.get("/repos")
def get_all_repositories():
    db = SessionLocal()
    repos = db.query(Repository).all()

    result = []
    for repo in repos:
        developer = db.query(Developer).filter_by(id=repo.developer_id).first()
        result.append({
            "id": repo.id,
            "name": repo.name,
            "developer": developer.username if developer else None
        })

    db.close()
    return result


@router.get("/repos/{repo_id}")
def get_repository(repo_id: int):
    db = SessionLocal()
    repo = db.query(Repository).filter_by(id=repo_id).first()

    if not repo:
        db.close()
        return {"error": "Repository not found"}

    developer = db.query(Developer).filter_by(id=repo.developer_id).first()

    result = {
        "id": repo.id,
        "name": repo.name,
        "developer": developer.username if developer else None
    }

    db.close()
    return result