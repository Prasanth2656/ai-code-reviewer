from sqlalchemy import Column, Integer, String
from app.database.db import Base

class Developer(Base):
    __tablename__ = "developers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)