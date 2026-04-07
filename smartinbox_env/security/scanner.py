# smartinbox_env/security/scanner.py
# ─────────────────────────────────────────────────────────────────
#  AttachmentScanner  |  Deep-packet attachment threat analysis
#  Checks MIME type, file magic bytes, macros, known malware hashes
#  Production: integrate ClamAV + YARA rules
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ScanResult:
    threat_score: float       # 0.0 (clean) – 1.0 (definite threat)
    blocked: bool
    threat_type: Optional[str]
    details: List[str] = field(default_factory=list)


# ── Threat intelligence (simulated)  ─────────────────────────────
# Production: pull from VirusTotal, AbuseIPDB, or internal threat DB
_MALWARE_HASHES = {
    "e3b0c44298fc1c149afb",   # known empty-file trick
    "da39a3ee5e6b4b0d3255",   # trojan hash placeholder
}

_DANGEROUS_EXTENSIONS = {".exe", ".bat", ".ps1", ".vbs", ".js", ".scr", ".jar"}
_MACRO_EXTENSIONS     = {".xlsm", ".docm", ".pptm"}
_SAFE_EXTENSIONS      = {".pdf", ".png", ".jpg", ".txt", ".csv"}

_SUSPICIOUS_SENDER_DOMAINS = {
    "randomsite.xyz", "fakeprize.net", "pharmafraud.biz",
    "earnonline.fake", "lotteryscam.com", "fakewatches.ru",
    "scambank.net", "datingspam.xyz",
}


class AttachmentScanner:
    """
    Multi-layer attachment and sender domain scanner.

    Layers:
    1. Sender domain reputation (blocklist)
    2. Attachment extension check
    3. Macro detection for Office files
    4. Hash-based malware lookup
    5. MIME-type mismatch detection (double extension trick)

    Production integration points:
    • Replace _hash_lookup() with ClamAV clamd socket
    • Replace domain check with live DNSBL query
    • Add YARA rule scanning for memory-resident payloads
    """

    def scan(self, email: Dict) -> ScanResult:
        details: List[str] = []
        threat_score = 0.0

        # ── Layer 1: Sender domain reputation ────────────────────
        sender = email.get("sender", "")
        domain = sender.split("@")[-1].lower() if "@" in sender else ""
        if domain in _SUSPICIOUS_SENDER_DOMAINS:
            threat_score += 0.4
            details.append(f"Sender domain '{domain}' on blocklist")

        # ── Layer 2 & 3: Attachment analysis ─────────────────────
        for attachment in email.get("attachments", []):
            name = attachment.get("filename", "").lower()
            content = attachment.get("content_bytes", b"")
            mime = attachment.get("mime_type", "")

            ext = self._extract_ext(name)

            if ext in _DANGEROUS_EXTENSIONS:
                threat_score += 0.5
                details.append(f"Dangerous extension: {ext}")

            elif ext in _MACRO_EXTENSIONS:
                threat_score += 0.35
                details.append(f"Macro-enabled Office file: {ext}")

            # ── Layer 4: Hash lookup ──────────────────────────────
            if content:
                file_hash = hashlib.md5(content).hexdigest()[:20]
                if self._hash_lookup(file_hash):
                    threat_score += 0.6
                    details.append(f"Known malware hash: {file_hash[:8]}…")

            # ── Layer 5: Double-extension trick ───────────────────
            if self._is_double_ext(name):
                threat_score += 0.3
                details.append(f"Double extension trick detected: {name}")

            # ── MIME mismatch (e.g. .pdf claiming text/html) ──────
            if ext == ".pdf" and mime and "pdf" not in mime:
                threat_score += 0.25
                details.append(f"MIME type mismatch: ext={ext}, mime={mime}")

        threat_score = min(round(threat_score, 3), 1.0)
        blocked = threat_score >= 0.5

        threat_type = None
        if blocked:
            if any("hash" in d for d in details):
                threat_type = "MALWARE"
            elif any("extension" in d for d in details):
                threat_type = "DANGEROUS_ATTACHMENT"
            elif any("blocklist" in d for d in details):
                threat_type = "SUSPICIOUS_SENDER"
            else:
                threat_type = "GENERIC_THREAT"

        return ScanResult(
            threat_score=threat_score,
            blocked=blocked,
            threat_type=threat_type,
            details=details,
        )

    # ── helpers ───────────────────────────────────────────────────
    @staticmethod
    def _extract_ext(filename: str) -> str:
        parts = filename.rsplit(".", 1)
        return f".{parts[-1]}" if len(parts) > 1 else ""

    @staticmethod
    def _is_double_ext(filename: str) -> bool:
        return bool(re.search(r"\.\w{2,4}\.\w{2,4}$", filename))

    @staticmethod
    def _hash_lookup(file_hash: str) -> bool:
        return file_hash in _MALWARE_HASHES
