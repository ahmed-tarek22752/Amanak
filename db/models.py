from __future__ import annotations

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CheckRecord(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    platform = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    scam_type = Column(String, default="unknown")
    score = Column(Float, default=0.0)
    user_hash = Column(String, nullable=False)
    data = Column(JSON, default=dict)


class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    user_hash = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    scam_type = Column(String, default="unknown")
    masked_message = Column(String, nullable=True)
