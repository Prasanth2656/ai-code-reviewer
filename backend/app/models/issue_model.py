from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.db import Base

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    file = Column(String)
    line = Column(Integer)
    severity = Column(String)   # High | Medium | Low
    description = Column(Text)
    fix = Column(Text)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id"))

    scan_job = relationship("ScanJob", back_populates="issues")