from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="completed")
    summary = Column(Text, nullable=True)   # JSON string of summary stats
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    repository = relationship("Repository")
    issues = relationship("Issue", back_populates="scan_job")