from __future__ import annotations

from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

try:
    from ..models import SmartInboxProAction, SmartInboxProObservation, SmartInboxProState
except ImportError:
    from models import SmartInboxProAction, SmartInboxProObservation, SmartInboxProState

from smartinbox_env.env import SmartInboxEnv
from smartinbox_env.tasks import TASKS

LABEL_NAMES = {0: "spam", 1: "normal", 2: "urgent"}


class SmartInboxProEnvironment(Environment):
    """OpenEnv wrapper around the existing SmartInbox gym-style environment."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(
        self,
        task_id: int = 1,
        enable_ai_engine: bool = True,
        enable_security: bool = True,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        self._task_id = task_id
        self._enable_ai_engine = enable_ai_engine
        self._enable_security = enable_security
        self._render_mode = render_mode
        self._episode_id = str(uuid4())
        self._env: SmartInboxEnv | None = None
        self._state = self._empty_state(task_id)

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        task_id: int | None = None,
        enable_ai_engine: bool | None = None,
        enable_security: bool | None = None,
        render_mode: str | None = None,
        **_: Any,
    ) -> SmartInboxProObservation:
        """Reset the episode and optionally switch task or runtime options."""
        if task_id is not None:
            self._validate_task_id(task_id)
            self._task_id = task_id
        if enable_ai_engine is not None:
            self._enable_ai_engine = bool(enable_ai_engine)
        if enable_security is not None:
            self._enable_security = bool(enable_security)
        if render_mode is not None:
            self._render_mode = render_mode

        self._episode_id = episode_id or str(uuid4())
        self._recreate_env()

        obs, info = self._env.reset(seed=seed, task_id=self._task_id)
        self._state = self._build_state()
        return self._build_observation(obs, info, reward=None, done=False)

    def step(
        self,
        action: SmartInboxProAction,
        timeout_s: float | None = None,
        **_: Any,
    ) -> SmartInboxProObservation:
        """Execute a classification action for the current email."""
        del timeout_s
        if self._env is None:
            raise RuntimeError("Environment is not initialized. Call reset() first.")

        obs, reward, terminated, truncated, info = self._env.step(action.label)
        done = bool(terminated or truncated)
        self._state = self._build_state()
        return self._build_observation(obs, info, reward=reward, done=done)

    @property
    def state(self) -> SmartInboxProState:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="SmartInbox-Pro",
            description="Email triage environment with AI and security-aware observations.",
            version="2.0.0",
            author="SmartInbox Team",
        )

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None

    def _recreate_env(self) -> None:
        self.close()
        self._env = SmartInboxEnv(
            task_id=self._task_id,
            render_mode=self._render_mode,
            enable_ai_engine=self._enable_ai_engine,
            enable_security=self._enable_security,
        )

    def _build_state(self) -> SmartInboxProState:
        env_state = self._env.state() if self._env is not None else {}
        current_email = self._current_email()
        task = TASKS[self._task_id]
        return SmartInboxProState(
            episode_id=self._episode_id,
            step_count=int(env_state.get("current_step", 0)),
            task_id=int(env_state.get("task_id", self._task_id)),
            task_name=str(env_state.get("task_name", task["name"])),
            difficulty=str(env_state.get("difficulty", task["difficulty"])),
            task_description=str(task["description"]),
            current_step=int(env_state.get("current_step", 0)),
            total_emails=int(env_state.get("total_emails", len(task["emails"]))),
            predictions_so_far=list(env_state.get("predictions_so_far", [])),
            total_reward_so_far=float(env_state.get("total_reward_so_far", 0.0)),
            ai_overrides=int(env_state.get("ai_overrides", 0)),
            security_blocks=int(env_state.get("security_blocks", 0)),
            avg_step_latency_ms=float(env_state.get("avg_step_latency_ms", 0.0)),
            done=bool(env_state.get("done", False)),
            current_email_id=current_email.get("id") if current_email else None,
            current_email_subject=current_email.get("subject") if current_email else None,
            current_email_sender=current_email.get("sender") if current_email else None,
        )

    def _build_observation(
        self,
        obs: Any,
        info: dict[str, Any],
        reward: float | None,
        done: bool,
    ) -> SmartInboxProObservation:
        email = self._email_by_id(info.get("email_id", ""))
        step_index = int(info.get("step", self._state.current_step))
        total_emails = self._state.total_emails
        remaining_emails = max(total_emails - self._state.current_step, 0)
        last_action = info.get("action_taken")

        return SmartInboxProObservation(
            instruction="Classify the current email as spam (0), normal (1), or urgent (2).",
            features=self._to_float_list(obs),
            email_id=info.get("email_id", ""),
            subject=info.get("subject", ""),
            sender=info.get("sender", ""),
            body_preview=(email.get("body", "")[:240] if email else ""),
            thread_summary=info.get("thread_summary", ""),
            task_id=self._state.task_id,
            task_name=self._state.task_name,
            difficulty=self._state.difficulty,
            step_index=step_index,
            total_emails=total_emails,
            remaining_emails=remaining_emails,
            last_action=last_action,
            last_action_name=LABEL_NAMES.get(last_action) if last_action is not None else None,
            done=done,
            reward=reward,
            metadata={
                "task_description": self._state.task_description,
                "ai_overrides": self._state.ai_overrides,
                "security_blocks": self._state.security_blocks,
                "avg_step_latency_ms": self._state.avg_step_latency_ms,
            },
        )

    def _empty_state(self, task_id: int) -> SmartInboxProState:
        task = TASKS[task_id]
        return SmartInboxProState(
            episode_id=self._episode_id,
            step_count=0,
            task_id=task_id,
            task_name=task["name"],
            difficulty=task["difficulty"],
            task_description=task["description"],
            current_step=0,
            total_emails=len(task["emails"]),
            predictions_so_far=[],
            total_reward_so_far=0.0,
            ai_overrides=0,
            security_blocks=0,
            avg_step_latency_ms=0.0,
            done=False,
            current_email_id=task["emails"][0]["id"],
            current_email_subject=task["emails"][0]["subject"],
            current_email_sender=task["emails"][0]["sender"],
        )

    def _current_email(self) -> dict[str, Any] | None:
        if self._env is None or not self._env.emails:
            return None
        idx = self._env.current_step
        if idx < 0 or idx >= len(self._env.emails):
            return None
        return self._env.emails[idx]

    def _email_by_id(self, email_id: str) -> dict[str, Any] | None:
        if not email_id:
            return None
        for email in TASKS[self._task_id]["emails"]:
            if email["id"] == email_id:
                return email
        return None

    @staticmethod
    def _to_float_list(obs: Any) -> list[float]:
        if hasattr(obs, "tolist"):
            return [float(value) for value in obs.tolist()]
        return [float(value) for value in obs]

    @staticmethod
    def _validate_task_id(task_id: int) -> None:
        if task_id not in TASKS:
            raise ValueError(f"Unsupported task_id: {task_id}. Expected one of {sorted(TASKS)}.")
