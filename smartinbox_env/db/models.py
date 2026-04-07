# smartinbox_env/db/models.py
# ─────────────────────────────────────────────────────────────────
#  PostgreSQL ORM Models  |  SQLAlchemy 2.x async style
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Index,
    Integer, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EmailRecord(Base):
    """Stores every email processed by the environment."""
    __tablename__ = "email_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    episode_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email_id: Mapped[str] = mapped_column(String(16), nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False)

    sender: Mapped[str]  = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(512))

    # AI engine output
    ai_label: Mapped[Optional[int]]      = mapped_column(Integer)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ai_category: Mapped[Optional[str]]   = mapped_column(String(64))

    # Security
    threat_score: Mapped[float] = mapped_column(Float, default=0.0)
    blocked: Mapped[bool]       = mapped_column(Boolean, default=False)
    pgp_valid: Mapped[bool]     = mapped_column(Boolean, default=False)

    # Agent decision
    agent_action: Mapped[Optional[int]] = mapped_column(Integer)
    correct_label: Mapped[int]          = mapped_column(Integer)
    reward: Mapped[float]               = mapped_column(Float)

    # Performance
    step_latency_ms: Mapped[float] = mapped_column(Float)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_email_records_episode_task", "episode_id", "task_id"),
    )


class EpisodeLog(Base):
    """Aggregated per-episode summary for leaderboard + analytics."""
    __tablename__ = "episode_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    episode_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    task_id: Mapped[int]    = mapped_column(Integer, nullable=False)

    final_score: Mapped[float]    = mapped_column(Float)
    total_reward: Mapped[float]   = mapped_column(Float)
    ai_overrides: Mapped[int]     = mapped_column(Integer, default=0)
    security_blocks: Mapped[int]  = mapped_column(Integer, default=0)

    avg_latency_ms: Mapped[float] = mapped_column(Float)
    p99_latency_ms: Mapped[float] = mapped_column(Float)

    started_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_episode_logs_task_score", "task_id", "final_score"),
    )
