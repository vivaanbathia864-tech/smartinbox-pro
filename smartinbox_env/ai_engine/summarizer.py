# smartinbox_env/ai_engine/summarizer.py
from __future__ import annotations
from typing import Dict


class ThreadSummarizer:
    """
    Lightweight thread summarizer. 
    Production swap: call an LLM API (e.g. claude-haiku) with the full thread.
    """

    def summarize(self, email: Dict) -> str:
        subject = email.get("subject", "")
        body    = email.get("body", "")
        sender  = email.get("sender", "")
        depth   = email.get("thread_depth", 0)

        # Truncate body to first 120 chars for the summary
        snippet = body[:120].replace("\n", " ").strip()
        if len(body) > 120:
            snippet += "…"

        prefix = f"Thread ({depth} msgs) | " if depth > 0 else ""
        return f"{prefix}From {sender} re: '{subject}' — {snippet}"
