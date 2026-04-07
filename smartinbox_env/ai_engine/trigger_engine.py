# smartinbox_env/ai_engine/trigger_engine.py
# ─────────────────────────────────────────────────────────────────
#  SmartTriggerEngine  |  Rule-driven auto-action system
#  Fires auto-actions when AI confidence exceeds threshold,
#  bypassing the agent to simulate real inbox automation.
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from smartinbox_env.ai_engine.categorizer import AICategorizerResult


@dataclass
class TriggerResult:
    fired: bool
    auto_action: Optional[int]    # None = no override; 0/1/2 = forced action
    trigger_name: str
    reason: str


class SmartTriggerEngine:
    """
    Evaluates an email + AI result and decides whether to fire
    an automatic action, overriding the agent's choice.

    Rules (evaluated in priority order):
    ─────────────────────────────────────
    1. HIGH_SPAM     : AI says spam with conf ≥ threshold → auto-archive (0)
    2. CRITICAL_INFRA: infra category + urgency_score > 0.95 → auto-escalate (2)
    3. KNOWN_SENDER  : sender_trust ≥ 0.95 → auto-normal (1)
    4. MALICIOUS_LINK: body contains known phishing patterns → auto-spam (0)
    """

    PHISHING_PATTERNS = [
        "click here immediately",
        "verify your identity",
        "bank details",
        "send your password",
        "account suspended",
    ]

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold

    def evaluate(self, email: Dict, ai_result: AICategorizerResult) -> TriggerResult:
        features = email.get("features", [])
        urgency  = features[2] if len(features) > 2 else 0.0
        trust    = email.get("sender_trust", 0.5)
        body     = email.get("body", "").lower()

        # Rule 1: High-confidence spam
        if ai_result.label == 0 and ai_result.confidence >= self.threshold:
            return TriggerResult(
                fired=True, auto_action=0,
                trigger_name="HIGH_SPAM",
                reason=f"AI spam confidence {ai_result.confidence:.2f} ≥ {self.threshold}"
            )

        # Rule 2: Critical infra + extreme urgency
        if ai_result.category == "infra" and urgency >= 0.95:
            return TriggerResult(
                fired=True, auto_action=2,
                trigger_name="CRITICAL_INFRA",
                reason=f"Infra category + urgency={urgency:.2f}"
            )

        # Rule 3: Trusted sender → normal
        if trust >= 0.95 and ai_result.label != 0:
            return TriggerResult(
                fired=True, auto_action=1,
                trigger_name="KNOWN_SENDER",
                reason=f"Sender trust={trust:.2f}"
            )

        # Rule 4: Phishing keyword
        if any(phrase in body for phrase in self.PHISHING_PATTERNS):
            return TriggerResult(
                fired=True, auto_action=0,
                trigger_name="MALICIOUS_LINK",
                reason="Phishing keyword detected in body"
            )

        return TriggerResult(
            fired=False, auto_action=None,
            trigger_name="NONE", reason="No trigger matched"
        )
