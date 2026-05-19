from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    developer_id = Column(Integer, ForeignKey("developers.id"))

    developer = relationship("Developer")