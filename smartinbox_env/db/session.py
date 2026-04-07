# smartinbox_env/db/session.py
# ─────────────────────────────────────────────────────────────────
#  AsyncSessionManager  |  High-concurrency PostgreSQL interface
#  Uses asyncpg driver + SQLAlchemy 2.x async engine
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

# These imports are conditional — gracefully degrade if not installed
try:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from smartinbox_env.db.models import Base, EpisodeLog, EmailRecord
    _HAS_SQLALCHEMY = True
except ImportError:
    _HAS_SQLALCHEMY = False


DEFAULT_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://smartinbox:secret@localhost:5432/smartinbox_db"
)

# Connection pool settings tuned for high concurrency
_POOL_SIZE = 20
_MAX_OVERFLOW = 10
_POOL_TIMEOUT = 30


class AsyncSessionManager:
    """
    Manages async PostgreSQL sessions.

    Usage:
        mgr = AsyncSessionManager(db_url)
        await mgr.init_db()            # run once at startup
        await mgr.log_episode(metrics) # non-blocking fire-and-forget

    Falls back silently if SQLAlchemy / asyncpg not installed,
    so the env still runs in no-DB mode for hackathon testing.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or DEFAULT_DB_URL
        self._engine = None
        self._session_factory = None
        self._enabled = _HAS_SQLALCHEMY

        if self._enabled:
            self._engine = create_async_engine(
                self.db_url,
                pool_size=_POOL_SIZE,
                max_overflow=_MAX_OVERFLOW,
                pool_timeout=_POOL_TIMEOUT,
                pool_pre_ping=True,    # detect stale connections
                echo=False,
            )
            self._session_factory = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )

    async def init_db(self):
        """Create all tables. Call once at app startup."""
        if not self._enabled:
            return
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._enabled:
            yield None
            return
        async with self._session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    async def log_episode(self, metrics) -> None:
        """Persist episode summary to PostgreSQL (non-blocking)."""
        if not self._enabled:
            return
        try:
            latencies = metrics.step_latencies_ms or [0.0]
            avg_lat = sum(latencies) / len(latencies)
            p99_lat = sorted(latencies)[int(len(latencies) * 0.99)]

            record = EpisodeLog(
                episode_id=metrics.episode_id,
                task_id=metrics.task_id,
                final_score=metrics.final_score,
                total_reward=metrics.total_reward,
                ai_overrides=metrics.ai_overrides,
                security_blocks=metrics.security_blocks,
                avg_latency_ms=round(avg_lat, 2),
                p99_latency_ms=round(p99_lat, 2),
                started_at=datetime.fromtimestamp(metrics.start_ts, tz=timezone.utc),
            )
            async with self.session() as s:
                if s:
                    s.add(record)
        except Exception as e:
            # Logging errors should never crash the env
            print(f"[DB] log_episode error: {e}")

    async def close(self):
        if self._engine:
            await self._engine.dispose()
