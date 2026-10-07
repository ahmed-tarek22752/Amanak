from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, CheckRecord, ReportRecord

engine = create_engine("sqlite:///./amanak.db", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_db() -> None:
    Base.metadata.create_all(bind=engine)


def hash_user(user_id: str | int) -> str:
    import hashlib

    return hashlib.sha256(f"amanak:{user_id}".encode("utf-8")).hexdigest()[:32]


def record_check(platform: str, verdict: str, scam_type: str, score: float, user_id: str | int, extra: dict[str, Any] | None = None) -> None:
    with SessionLocal() as session:
        record = CheckRecord(
            timestamp=datetime.utcnow(),
            platform=platform,
            verdict=verdict,
            scam_type=scam_type,
            score=float(score),
            user_hash=hash_user(user_id),
            data=extra or {},
        )
        session.add(record)
        session.commit()


def record_report(platform: str, verdict: str, scam_type: str, user_id: str | int, masked_message: str | None = None) -> None:
    with SessionLocal() as session:
        report = ReportRecord(
            timestamp=datetime.utcnow(),
            platform=platform,
            verdict=verdict,
            scam_type=scam_type,
            user_hash=hash_user(user_id),
            masked_message=masked_message,
        )
        session.add(report)
        session.commit()


def get_stats() -> dict[str, Any]:
    ensure_db()
    with SessionLocal() as session:
        total_checks = session.query(CheckRecord).count()
        scams = session.query(CheckRecord).filter(CheckRecord.verdict == "scam").count()
        cautions = session.query(CheckRecord).filter(CheckRecord.verdict == "caution").count()
        safe = session.query(CheckRecord).filter(CheckRecord.verdict == "safe").count()

        top_types = (
            session.query(CheckRecord.scam_type, func.count(CheckRecord.scam_type).label("count"))
            .filter(CheckRecord.scam_type != "unknown")
            .group_by(CheckRecord.scam_type)
            .order_by(func.count(CheckRecord.scam_type).desc())
            .limit(5)
            .all()
        )

        checks_per_day = []
        for row in session.query(
            func.date(CheckRecord.timestamp).label("day"),
            func.count(CheckRecord.id).label("count"),
        ).group_by(func.date(CheckRecord.timestamp)).order_by(func.date(CheckRecord.timestamp).desc()).limit(30):
            checks_per_day.append({"date": row.day, "count": row.count})

        platforms = (
            session.query(CheckRecord.platform, func.count(CheckRecord.id).label("count"))
            .group_by(CheckRecord.platform)
            .all()
        )

    return {
        "total_checks": total_checks,
        "scams_caught": scams,
        "cautions": cautions,
        "safe": safe,
        "top_scam_types": [{"name": row[0], "count": row[1]} for row in top_types],
        "checks_per_day": checks_per_day,
        "platform_breakdown": [{"platform": row[0], "count": row[1]} for row in platforms],
    }
