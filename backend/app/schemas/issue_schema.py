from pydantic import BaseModel

class IssueResponse(BaseModel):
    id: int
    file: str
    line: int
    severity: str
    description: str
    fix: str
    scan_job_id: int

    class Config:
        from_attributes = True
