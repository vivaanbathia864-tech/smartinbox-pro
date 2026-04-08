from __future__ import annotations

from typing import Literal

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class SmartInboxProAction(Action):
    """Classification action for the current email."""

    label: Literal[0, 1, 2] = Field(
        ...,
        description="Classification label where 0=spam, 1=normal, and 2=urgent.",
    )
    explanation: str | None = Field(
        default=None,
        description="Optional short rationale for the selected label.",
    )


class SmartInboxProObservation(Observation):
    """Typed observation returned by the SmartInbox-Pro environment."""

    instruction: str = Field(
        ...,
        description="Short instruction telling the agent how to act on this email.",
    )
    features: list[float] = Field(
        default_factory=list,
        description="12-dimensional email feature vector used for classification.",
    )
    email_id: str = Field(default="", description="Unique identifier for the email.")
    subject: str = Field(default="", description="Email subject line.")
    sender: str = Field(default="", description="Email sender address.")
    body_preview: str = Field(
        default="",
        description="Short preview of the email body for context.",
    )
    thread_summary: str = Field(
        default="",
        description="AI-generated one-line summary of the email thread.",
    )
    task_id: int = Field(..., description="Current task identifier.")
    task_name: str = Field(..., description="Human-readable task name.")
    difficulty: str = Field(..., description="Task difficulty label.")
    step_index: int = Field(..., description="Zero-based email index within the task.")
    total_emails: int = Field(..., description="Number of emails in the current task.")
    remaining_emails: int = Field(
        ...,
        description="How many emails remain after this observation.",
    )
    valid_labels: list[str] = Field(
        default_factory=lambda: ["0=spam", "1=normal", "2=urgent"],
        description="Allowed labels for the next action.",
    )
    last_action: int | None = Field(
        default=None,
        description="Most recent action applied to the environment, if any.",
    )
    last_action_name: str | None = Field(
        default=None,
        description="Human-readable version of the last action.",
    )
    grader_score: float = Field(
        default=0.001,
        description="Task-level grader score, always kept strictly inside (0, 1).",
    )
    score: float = Field(
        default=0.001,
        description="Alias for grader_score for validator compatibility.",
    )


class SmartInboxProState(State):
    """Typed state for tracking the current episode."""

    task_id: int = Field(..., description="Current task identifier.")
    task_name: str = Field(..., description="Current task name.")
    difficulty: str = Field(..., description="Current task difficulty.")
    task_description: str = Field(..., description="Task objective shown to the agent.")
    current_step: int = Field(..., description="Number of actions already taken.")
    total_emails: int = Field(..., description="Total emails in the current task.")
    predictions_so_far: list[int] = Field(
        default_factory=list,
        description="Action history for the current episode.",
    )
    total_reward_so_far: float = Field(
        default=0.0,
        description="Accumulated reward for the current episode.",
    )
    ai_overrides: int = Field(
        default=0,
        description="How many times the AI override logic changed the action.",
    )
    security_blocks: int = Field(
        default=0,
        description="How many malicious attachments were blocked.",
    )
    avg_step_latency_ms: float = Field(
        default=0.0,
        description="Average step latency in milliseconds.",
    )
    grader_score: float = Field(
        default=0.001,
        description="Latest task-level grader score, always kept strictly inside (0, 1).",
    )
    final_score: float = Field(
        default=0.001,
        description="Alias for grader_score for validator compatibility.",
    )
    done: bool = Field(default=False, description="Whether the episode has ended.")
    current_email_id: str | None = Field(
        default=None,
        description="Identifier of the next email to classify, if any.",
    )
    current_email_subject: str | None = Field(
        default=None,
        description="Subject of the next email to classify, if any.",
    )
    current_email_sender: str | None = Field(
        default=None,
        description="Sender of the next email to classify, if any.",
    )
