from __future__ import annotations

from typing import Any, Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

from .models import SmartInboxProAction, SmartInboxProObservation, SmartInboxProState


class SmartInboxProEnv(
    EnvClient[SmartInboxProAction, SmartInboxProObservation, SmartInboxProState]
):
    """OpenEnv client for the SmartInbox-Pro environment."""

    def _step_payload(self, action: SmartInboxProAction) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"label": action.label}
        if action.explanation:
            payload["explanation"] = action.explanation
        if action.metadata:
            payload["metadata"] = action.metadata
        return payload

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SmartInboxProObservation]:
        obs_payload = dict(payload.get("observation", {}))
        obs_payload["done"] = payload.get("done", obs_payload.get("done", False))
        obs_payload["reward"] = payload.get("reward", obs_payload.get("reward"))
        observation = SmartInboxProObservation(**obs_payload)
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> SmartInboxProState:
        return SmartInboxProState(**payload)
