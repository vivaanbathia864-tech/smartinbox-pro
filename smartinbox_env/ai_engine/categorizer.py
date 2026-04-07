# smartinbox_env/ai_engine/categorizer.py
# ─────────────────────────────────────────────────────────────────
#  AI Categorizer  |  Heuristic + ML-ready auto-classification
#  In production: swap _heuristic_predict() with a fine-tuned
#  transformer (e.g., distilbert-base-uncased on email datasets).
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AICategorizerResult:
    label: int          # 0=Spam, 1=Normal, 2=Urgent
    confidence: float   # 0.0 – 1.0
    category: str       # e.g. "billing", "security", "newsletter"
    reasoning: str      # one-line explanation


# Keyword lists used by the heuristic engine
_SPAM_SIGNALS = [
    r"\bfree\b", r"\bwin\b", r"\bcongratulations\b", r"\bclaim\b",
    r"\blottery\b", r"\bprize\b", r"\bgift card\b", r"\bno prescription\b",
    r"\bmake money\b", r"\bhot singles\b", r"\bclick here\b",
]
_URGENT_SIGNALS = [
    r"\burgent\b", r"\bcritical\b", r"\bimmediate\b", r"\bimmediately\b",
    r"\bdown\b", r"\bbreach\b", r"\bviolation\b", r"\bdeadline today\b",
    r"\bfire alarm\b", r"\brate limit\b", r"\bfailed\b",
]
_CATEGORY_MAP = {
    "billing":    [r"\bpayment\b", r"\binvoice\b", r"\bbilling\b", r"\bsubscription\b"],
    "security":   [r"\bbreach\b", r"\bsecurity\b", r"\bunauthorized\b", r"\bpgp\b"],
    "infra":      [r"\bserver\b", r"\bapi\b", r"\bbackup\b", r"\bdatabase\b", r"\bfirewall\b"],
    "legal":      [r"\blegal\b", r"\bcompliance\b", r"\bgdpr\b", r"\bcopyright\b"],
    "hr":         [r"\bonboarding\b", r"\bperformance review\b", r"\bholiday\b", r"\bnewsletter\b"],
    "sales":      [r"\bclient\b", r"\bcontract\b", r"\binvestor\b", r"\bproposal\b"],
}


class AICategorizer:
    """
    Categorizes an email into (label, category, confidence).

    Plug-in points for production ML:
      • Replace _heuristic_predict() with a model.predict() call
      • Feed self._feature_text() into a tokenizer
      • Keep the AICategorizerResult dataclass — env.py depends on it
    """

    def predict(self, email: Dict) -> AICategorizerResult:
        text = self._feature_text(email)
        features = email.get("features", [0.5] * 5)

        # ── Feature-based confidence from env features ────────────
        spam_feat   = features[0] if len(features) > 0 else 0.5
        urgency_feat = features[2] if len(features) > 2 else 0.5

        # ── Heuristic keyword scoring ─────────────────────────────
        spam_hits    = self._count_hits(text, _SPAM_SIGNALS)
        urgent_hits  = self._count_hits(text, _URGENT_SIGNALS)

        spam_score   = 0.5 * spam_feat   + 0.5 * min(spam_hits / 3.0, 1.0)
        urgent_score = 0.5 * urgency_feat + 0.5 * min(urgent_hits / 2.0, 1.0)

        # ── Decision + confidence ─────────────────────────────────
        if spam_score > 0.65:
            label, confidence = 0, round(spam_score, 3)
            reasoning = f"Spam signals detected (score={spam_score:.2f})"
        elif urgent_score > 0.60:
            label, confidence = 2, round(urgent_score, 3)
            reasoning = f"Urgency signals detected (score={urgent_score:.2f})"
        else:
            normal_conf = 1.0 - max(spam_score, urgent_score)
            label, confidence = 1, round(normal_conf, 3)
            reasoning = "No strong spam or urgency signals found"

        category = self._detect_category(text)
        return AICategorizerResult(
            label=label, confidence=confidence,
            category=category, reasoning=reasoning
        )

    # ── helpers ───────────────────────────────────────────────────
    @staticmethod
    def _feature_text(email: Dict) -> str:
        return (
            f"{email.get('subject', '')} "
            f"{email.get('body', '')} "
            f"{email.get('sender', '')}"
        ).lower()

    @staticmethod
    def _count_hits(text: str, patterns: List[str]) -> int:
        return sum(1 for p in patterns if re.search(p, text))

    @staticmethod
    def _detect_category(text: str) -> str:
        for category, patterns in _CATEGORY_MAP.items():
            if any(re.search(p, text) for p in patterns):
                return category
        return "general"
