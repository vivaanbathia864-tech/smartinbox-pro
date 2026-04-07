# smartinbox_env/env.py
# ─────────────────────────────────────────────────────────────────
#  SmartInbox-Pro  |  Production-Grade OpenEnv Email Environment
#  Upgraded from mini → peak-advanced architecture
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from smartinbox_env.ai_engine.categorizer import AICategorizer
from smartinbox_env.ai_engine.summarizer import ThreadSummarizer
from smartinbox_env.ai_engine.trigger_engine import SmartTriggerEngine
from smartinbox_env.db.session import AsyncSessionManager
from smartinbox_env.db.models import EmailRecord, EpisodeLog
from smartinbox_env.security.pgp import PGPHandler
from smartinbox_env.security.scanner import AttachmentScanner
from smartinbox_env.tasks import TASKS, grade_task


# ── Observation dtype (float32, shape=(12,)) ─────────────────────
# [spam, importance, urgency, promo, response_needed,
#  has_attachment, attachment_threat, pgp_signed, thread_depth,
#  sender_trust, time_sensitivity, ai_category_conf]
OBS_DIM = 12


@dataclass
class EpisodeMetrics:
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: int = 0
    start_ts: float = field(default_factory=time.time)
    step_latencies_ms: List[float] = field(default_factory=list)
    total_reward: float = 0.0
    predictions: List[int] = field(default_factory=list)
    ai_overrides: int = 0         # times AI auto-action fired
    security_blocks: int = 0      # attachments blocked by scanner
    final_score: float = 0.0


class SmartInboxEnv(gym.Env):
    """
    SmartInbox-Pro: Production-ready OpenEnv email triage environment.

    Upgrades over mini version
    ──────────────────────────
    • Observation: 5-dim  →  12-dim (security + AI features injected)
    • Async DB logging to PostgreSQL via AsyncSession
    • AI categorizer assigns category confidence as feature
    • PGP signature status surfaced in observation
    • Attachment scanner blocks malicious payloads before step()
    • SmartTriggerEngine fires auto-actions (e.g., auto-archive spam)
    • Thread summarizer used in info dict for agent context
    • Episode metrics tracked with per-step latency
    """

    metadata = {"render_modes": ["human", "json"]}

    def __init__(
        self,
        task_id: int = 1,
        render_mode: Optional[str] = None,
        db_url: Optional[str] = None,
        enable_ai_engine: bool = True,
        enable_security: bool = True,
        auto_trigger_threshold: float = 0.9,
    ):
        super().__init__()
        assert task_id in [1, 2, 3], "task_id must be 1, 2, or 3"

        self.task_id = task_id
        self.render_mode = render_mode
        self.enable_ai_engine = enable_ai_engine
        self.enable_security = enable_security
        self.auto_trigger_threshold = auto_trigger_threshold

        # ── Action / Observation spaces ───────────────────────────
        self.action_space = spaces.Discrete(3)  # 0=Spam, 1=Normal, 2=Urgent
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32
        )

        # ── Sub-systems ───────────────────────────────────────────
        self._ai = AICategorizer() if enable_ai_engine else None
        self._summarizer = ThreadSummarizer() if enable_ai_engine else None
        self._triggers = SmartTriggerEngine(threshold=auto_trigger_threshold)
        self._pgp = PGPHandler() if enable_security else None
        self._scanner = AttachmentScanner() if enable_security else None
        self._db = AsyncSessionManager(db_url) if db_url else None

        # ── Episode state ─────────────────────────────────────────
        self.emails: List[Dict] = []
        self.current_step: int = 0
        self.done: bool = False
        self.metrics: EpisodeMetrics = EpisodeMetrics()
        self._loop = asyncio.new_event_loop()

    # ─────────────────────────────────────────────────────────────
    # reset()
    # ─────────────────────────────────────────────────────────────
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
        task_id: Optional[int] = None,
    ) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        if task_id:
            self.task_id = task_id

        task = TASKS[self.task_id]
        self.emails = task["emails"]
        self.current_step = 0
        self.done = False
        self.metrics = EpisodeMetrics(task_id=self.task_id)

        obs = self._build_obs(self.current_step)
        info = self._build_info(self.current_step)

        if self.render_mode == "human":
            self._render_email(self.current_step)

        return obs, info

    # ─────────────────────────────────────────────────────────────
    # step()
    # ─────────────────────────────────────────────────────────────
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        assert not self.done, "Episode done. Call reset()."
        assert self.action_space.contains(action), f"Invalid action: {action}"

        t_start = time.perf_counter()
        email = self.emails[self.current_step]

        # ── Security gate (attachment scan) ───────────────────────
        if self.enable_security and self._scanner:
            threat = self._scanner.scan(email)
            if threat.blocked:
                self.metrics.security_blocks += 1
                # Force spam classification on malicious attachment
                action = 0

        # ── AI auto-trigger override ──────────────────────────────
        if self.enable_ai_engine and self._ai:
            ai_result = self._ai.predict(email)
            triggered = self._triggers.evaluate(email, ai_result)
            if triggered.auto_action is not None:
                self.metrics.ai_overrides += 1
                action = triggered.auto_action

        # ── Reward calculation ────────────────────────────────────
        correct_label = email["label"]
        if action == correct_label:
            reward = 1.0
        elif abs(action - correct_label) == 1:
            reward = 0.25
        else:
            reward = -0.5

        self.metrics.predictions.append(action)
        self.metrics.total_reward += reward
        self.current_step += 1

        terminated = self.current_step >= len(self.emails)
        self.done = terminated

        # ── Build next obs ────────────────────────────────────────
        obs = self._build_obs(self.current_step)
        info = self._build_info(self.current_step - 1, action=action, reward=reward)

        if terminated:
            final_score = grade_task(self.task_id, self.metrics.predictions)
            self.metrics.final_score = final_score
            info["final_score"] = final_score
            info["episode_metrics"] = self._serialize_metrics()

            if self._db:
                self._loop.run_until_complete(
                    self._db.log_episode(self.metrics)
                )

        # ── Latency tracking ──────────────────────────────────────
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        self.metrics.step_latencies_ms.append(round(elapsed_ms, 2))

        if self.render_mode == "human" and not terminated:
            self._render_step(self.current_step - 1, action, correct_label, reward)

        return obs, reward, terminated, False, info

    # ─────────────────────────────────────────────────────────────
    # state()  — OpenEnv spec
    # ─────────────────────────────────────────────────────────────
    def state(self) -> Dict[str, Any]:
        task = TASKS[self.task_id]
        avg_latency = (
            round(sum(self.metrics.step_latencies_ms) / len(self.metrics.step_latencies_ms), 2)
            if self.metrics.step_latencies_ms else 0.0
        )
        return {
            "episode_id": self.metrics.episode_id,
            "task_id": self.task_id,
            "task_name": task["name"],
            "difficulty": task["difficulty"],
            "current_step": self.current_step,
            "total_emails": len(self.emails),
            "predictions_so_far": self.metrics.predictions,
            "total_reward_so_far": self.metrics.total_reward,
            "ai_overrides": self.metrics.ai_overrides,
            "security_blocks": self.metrics.security_blocks,
            "avg_step_latency_ms": avg_latency,
            "done": self.done,
        }

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────
    def _build_obs(self, idx: int) -> np.ndarray:
        """Build 12-dim observation vector, enriched with AI + security features."""
        if idx >= len(self.emails):
            return np.zeros(OBS_DIM, dtype=np.float32)

        email = self.emails[idx]
        base = list(email["features"])  # original 5 dims

        # ── AI features ───────────────────────────────────────────
        ai_conf = 0.5
        if self.enable_ai_engine and self._ai:
            result = self._ai.predict(email)
            ai_conf = result.confidence

        # ── Security features ─────────────────────────────────────
        has_attachment = float(bool(email.get("attachments")))
        attachment_threat = 0.0
        pgp_signed = 0.0
        if self.enable_security:
            if self._scanner and has_attachment:
                scan = self._scanner.scan(email)
                attachment_threat = scan.threat_score
            if self._pgp:
                pgp_signed = float(self._pgp.verify(email).valid)

        # ── Derived features ──────────────────────────────────────
        thread_depth = min(float(email.get("thread_depth", 0)) / 10.0, 1.0)
        sender_trust = email.get("sender_trust", 0.5)
        time_sensitivity = email.get("time_sensitivity", base[2])  # fallback to urgency

        extended = base + [
            has_attachment,
            attachment_threat,
            pgp_signed,
            thread_depth,
            sender_trust,
            time_sensitivity,
            ai_conf,
        ]
        return np.array(extended[:OBS_DIM], dtype=np.float32)

    def _build_info(
        self,
        idx: int,
        action: Optional[int] = None,
        reward: Optional[float] = None,
    ) -> Dict:
        if idx >= len(self.emails):
            return {"done": True}

        email = self.emails[idx]
        info: Dict[str, Any] = {
            "email_id": email["id"],
            "subject": email["subject"],
            "sender": email["sender"],
            "step": idx,
            "total": len(self.emails),
        }

        if action is not None:
            info["action_taken"] = action
            info["reward"] = reward

        # Thread summary from AI engine
        if self.enable_ai_engine and self._summarizer:
            info["thread_summary"] = self._summarizer.summarize(email)

        return info

    def _serialize_metrics(self) -> Dict:
        m = self.metrics
        return {
            "episode_id": m.episode_id,
            "task_id": m.task_id,
            "final_score": m.final_score,
            "total_reward": m.total_reward,
            "ai_overrides": m.ai_overrides,
            "security_blocks": m.security_blocks,
            "avg_latency_ms": (
                round(sum(m.step_latencies_ms) / len(m.step_latencies_ms), 2)
                if m.step_latencies_ms else 0.0
            ),
            "p99_latency_ms": (
                sorted(m.step_latencies_ms)[int(len(m.step_latencies_ms) * 0.99)]
                if m.step_latencies_ms else 0.0
            ),
        }

    def _render_email(self, idx: int):
        if idx < len(self.emails):
            e = self.emails[idx]
            print(f"\n📧 Email {idx + 1}/{len(self.emails)}")
            print(f"   From    : {e['sender']}")
            print(f"   Subject : {e['subject']}")

    def _render_step(self, idx: int, action: int, correct: int, reward: float):
        labels = {0: "Spam", 1: "Normal", 2: "Urgent"}
        mark = "✅" if action == correct else "❌"
        print(f"  {mark} Step {idx+1}: Pred={labels[action]} | True={labels[correct]} | R={reward:+.2f}")

    def close(self):
        if self._loop and not self._loop.is_closed():
            self._loop.close()
