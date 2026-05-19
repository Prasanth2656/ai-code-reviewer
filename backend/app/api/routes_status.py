from fastapi import APIRouter
from app.database.db import SessionLocal
from app.models.scan_job_model import ScanJob

router = APIRouter()

@router.get("/scan-status/{scan_id}")
def get_scan_status(scan_id: int):
    db = SessionLocal()
    scan = db.query(ScanJob).filter_by(id=scan_id).first()

    if not scan:
        db.close()
        return {"error": "Scan not found"}

    result = {
        "id": scan.id,
        "status": scan.status
    }

    db.close()
    return result