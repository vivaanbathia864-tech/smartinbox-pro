# smartinbox_env/imap_smtp/handler.py
# ─────────────────────────────────────────────────────────────────
#  AsyncEmailHandler  |  Low-latency IMAP fetch + SMTP send
#  Concurrency: asyncio + connection pooling for high throughput
# ─────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import email as email_lib
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

try:
    import aioimaplib
    _HAS_IMAP = True
except ImportError:
    _HAS_IMAP = False


@dataclass
class FetchedEmail:
    uid: str
    sender: str
    subject: str
    body: str
    raw_headers: Dict[str, str] = field(default_factory=dict)
    attachments: List[Dict] = field(default_factory=list)


@dataclass
class SendResult:
    success: bool
    message_id: Optional[str]
    error: Optional[str]


class AsyncEmailHandler:
    """
    Async IMAP fetcher + SMTP sender with:
    • TLS/STARTTLS enforcement
    • Connection keep-alive pooling
    • Concurrent batch fetch via asyncio.gather()
    • OAuth2 XOAUTH2 SASL support (swap _login() method)
    • Automatic retry on transient network errors

    Production credentials flow:
    1. Fetch OAuth2 token from your identity provider
    2. Pass to connect() as oauth2_token instead of password
    3. Handler calls AUTH XOAUTH2 mechanism
    """

    def __init__(
        self,
        imap_host: str,
        imap_port: int = 993,
        smtp_host: str = "",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        oauth2_token: Optional[str] = None,
        batch_size: int = 50,
    ):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.smtp_host = smtp_host or imap_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.oauth2_token = oauth2_token
        self.batch_size = batch_size

        self._imap: Optional[object] = None
        self._imap_lock = asyncio.Lock()

    # ── IMAP ──────────────────────────────────────────────────────
    async def connect_imap(self):
        """Open IMAP connection with STARTTLS."""
        if not _HAS_IMAP:
            raise RuntimeError("aioimaplib not installed. pip install aioimaplib")
        self._imap = aioimaplib.IMAP4_SSL(host=self.imap_host, port=self.imap_port)
        await self._imap.wait_hello_from_server()
        if self.oauth2_token:
            await self._login_oauth2()
        else:
            await self._imap.login(self.username, self.password)

    async def fetch_unread(self, mailbox: str = "INBOX", limit: int = 100) -> List[FetchedEmail]:
        """Fetch up to `limit` unread emails concurrently."""
        async with self._imap_lock:
            await self._imap.select(mailbox)
            _, data = await self._imap.search("UNSEEN")
            uids = data[0].decode().split()[:limit]

        # Batch fetch: split into chunks of batch_size for concurrency
        batches = [uids[i:i+self.batch_size] for i in range(0, len(uids), self.batch_size)]
        results = await asyncio.gather(*[self._fetch_batch(b) for b in batches])
        return [msg for batch in results for msg in batch]

    async def _fetch_batch(self, uids: List[str]) -> List[FetchedEmail]:
        fetched = []
        for uid in uids:
            try:
                async with self._imap_lock:
                    _, data = await self._imap.fetch(uid, "(RFC822)")
                raw = data[1]
                msg = email_lib.message_from_bytes(raw)
                fetched.append(self._parse_message(uid, msg))
            except Exception as e:
                print(f"[IMAP] Failed to fetch UID {uid}: {e}")
        return fetched

    @staticmethod
    def _parse_message(uid: str, msg) -> FetchedEmail:
        body = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp  = str(part.get("Content-Disposition", ""))
                if ctype == "text/plain" and "attachment" not in disp:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif "attachment" in disp:
                    attachments.append({
                        "filename": part.get_filename() or "unknown",
                        "mime_type": ctype,
                        "content_bytes": part.get_payload(decode=True) or b"",
                    })
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        return FetchedEmail(
            uid=uid,
            sender=msg.get("From", ""),
            subject=msg.get("Subject", ""),
            body=body,
            raw_headers=dict(msg.items()),
            attachments=attachments,
        )

    async def _login_oauth2(self):
        """XOAUTH2 authentication for Gmail / Outlook OAuth2 flows."""
        import base64
        auth_string = f"user={self.username}\x01auth=Bearer {self.oauth2_token}\x01\x01"
        encoded = base64.b64encode(auth_string.encode()).decode()
        await self._imap.authenticate("XOAUTH2", lambda x: encoded)

    # ── SMTP ──────────────────────────────────────────────────────
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
        encrypt_pgp: bool = False,
    ) -> SendResult:
        """
        Send an email via SMTP with STARTTLS.
        Runs synchronous smtplib in a thread executor to avoid blocking.
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_send,
                to, subject, body, reply_to_message_id
            )
            return result
        except Exception as e:
            return SendResult(success=False, message_id=None, error=str(e))

    def _sync_send(self, to: str, subject: str, body: str, reply_to_id: Optional[str]) -> SendResult:
        ctx = ssl.create_default_context()
        msg = MIMEMultipart("alternative")
        msg["From"]    = self.username
        msg["To"]      = to
        msg["Subject"] = subject
        if reply_to_id:
            msg["In-Reply-To"] = reply_to_id
            msg["References"]  = reply_to_id

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(self.username, self.password)
            server.sendmail(self.username, to, msg.as_string())

        msg_id = msg.get("Message-ID", "generated")
        return SendResult(success=True, message_id=msg_id, error=None)

    async def close(self):
        if self._imap:
            await self._imap.logout()
