# SmartInbox-Pro — Technical Blueprint
## Peak-Advanced Production Architecture

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SMARTINBOX-PRO                               │
│                                                                     │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────────────┐   │
│  │  Agent   │───▶│  OpenEnv    │───▶│     AI Engine Layer      │   │
│  │ (RL/LLM) │    │  FastAPI    │    │  Categorizer │ Summarizer │   │
│  └──────────┘    │  Server     │    │  TriggerEngine            │   │
│                  └──────┬──────┘    └──────────────────────────┘   │
│                         │                                           │
│            ┌────────────┼────────────────┐                         │
│            ▼            ▼                ▼                          │
│     ┌────────────┐ ┌─────────┐  ┌──────────────┐                  │
│     │ PostgreSQL │ │ Security│  │  IMAP/SMTP   │                   │
│     │ (asyncpg)  │ │  Layer  │  │   Handler    │                   │
│     │ Episodes   │ │ PGP+JWT │  │  (async)     │                   │
│     │ Emails     │ │ Scanner │  └──────────────┘                   │
│     └────────────┘ └─────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Reference

| Module | File | Purpose |
|--------|------|---------|
| Core Env | `smartinbox_env/env.py` | 12-dim obs, async step, episode metrics |
| AI Categorizer | `ai_engine/categorizer.py` | Keyword + feature-based classification |
| Thread Summarizer | `ai_engine/summarizer.py` | Per-email context summary |
| Trigger Engine | `ai_engine/trigger_engine.py` | Rule-based auto-action overrides |
| PGP Handler | `security/pgp.py` | Signature verify + envelope encrypt |
| Attachment Scanner | `security/scanner.py` | Multi-layer threat detection (5 layers) |
| DB Models | `db/models.py` | SQLAlchemy ORM — EmailRecord, EpisodeLog |
| DB Session | `db/session.py` | Async PostgreSQL pool, episode logging |
| IMAP/SMTP | `imap_smtp/handler.py` | Async fetch + STARTTLS send + OAuth2 |
| Auth | `server/auth.py` | JWT issuance, Bearer verification, rate limiter |
| Baseline | `baseline.py` | Rule-based v1 + Enhanced v2 comparison |

---

## 3. Observation Space Upgrade

| Index | Feature | Source | Range |
|-------|---------|--------|-------|
| 0 | spam_score | task features | 0–1 |
| 1 | importance_score | task features | 0–1 |
| 2 | urgency_score | task features | 0–1 |
| 3 | promo_score | task features | 0–1 |
| 4 | response_needed | task features | 0–1 |
| 5 | has_attachment | scanner | 0 or 1 |
| **6** | **attachment_threat** | **scanner (5-layer)** | 0–1 |
| **7** | **pgp_signed** | **PGP verifier** | 0 or 1 |
| **8** | **thread_depth** | **email metadata** | 0–1 |
| **9** | **sender_trust** | **reputation DB** | 0–1 |
| **10** | **time_sensitivity** | **email metadata** | 0–1 |
| **11** | **ai_category_conf** | **AI categorizer** | 0–1 |

Bold = new in Pro. Original env had 5 dims; Pro has 12.

---

## 4. AI Engine — Automation Layer

### 4.1 AICategorizer
- Input: email dict (subject, body, sender, features)
- Output: `AICategorizerResult(label, confidence, category, reasoning)`
- Categories: `billing | security | infra | legal | hr | sales | general`
- Production swap: replace `_heuristic_predict()` with `model.predict(tokenizer(text))`

### 4.2 SmartTriggerEngine — Auto-Action Rules

| Rule | Condition | Auto-Action |
|------|-----------|-------------|
| HIGH_SPAM | AI confidence ≥ 0.9, label=spam | Force 0 (spam) |
| CRITICAL_INFRA | category=infra AND urgency ≥ 0.95 | Force 2 (urgent) |
| KNOWN_SENDER | sender_trust ≥ 0.95 | Force 1 (normal) |
| MALICIOUS_LINK | phishing keywords in body | Force 0 (spam) |

Rules are evaluated in priority order. First match wins.

### 4.3 ThreadSummarizer
- Returns a one-line string: `"Thread (N msgs) | From X re: 'Subject' — snippet…"`
- Injected into `info["thread_summary"]` every step
- Production: call Claude Haiku API with full thread context

---

## 5. Security Architecture

### 5.1 AttachmentScanner — 5 Layers

```
Email arrives
     │
     ▼
[Layer 1] Sender domain reputation check (blocklist)
     │ threat += 0.4 if blocked domain
     ▼
[Layer 2] Attachment extension check
     │ threat += 0.5 for .exe/.bat/.ps1/.vbs/.js/.scr/.jar
     ▼
[Layer 3] Macro-enabled Office file detection
     │ threat += 0.35 for .xlsm/.docm/.pptm
     ▼
[Layer 4] MD5 hash lookup against known malware DB
     │ threat += 0.6 on hash match
     ▼
[Layer 5] Double-extension trick + MIME mismatch
     │ threat += 0.3/.25 respectively
     ▼
threat_score ≥ 0.5 → BLOCKED, action forced to 0 (spam)
```

### 5.2 PGP Handler
- verify(): checks sender against trusted key store (GPG keyring in prod)
- encrypt(): HMAC-SHA256 placeholder → swap with `gnupg.GPG().encrypt()` in prod
- PGP valid status surfaced as obs[7]

### 5.3 JWT Auth Flow
```
Agent → POST /auth/token {client_id, client_secret}
Server → returns signed JWT (HS256, 1hr TTL)
Agent → GET /env/step  Authorization: Bearer <token>
Server → JWTAuthenticator.verify_token() → 401 if expired/invalid
```

---

## 6. Database Schema

### `email_records` table
Stores every individual email processed, with AI + security metadata.
Indexed on `(episode_id, task_id)` for fast episode replay.

### `episode_logs` table
One row per episode. Stores final_score, total_reward, latency P99, AI overrides, security blocks.
Indexed on `(task_id, final_score)` for leaderboard queries.

### PostgreSQL connection pool settings
- pool_size: 20 connections
- max_overflow: 10 burst connections
- pool_timeout: 30s
- pool_pre_ping: True (detect stale connections)
- Driver: asyncpg (fastest async PG driver for Python)

---

## 7. IMAP/SMTP Handler — Performance Design

| Feature | Implementation |
|---------|---------------|
| Concurrent fetch | `asyncio.gather()` over UID batches |
| Batch size | 50 UIDs per concurrent batch (configurable) |
| TLS | STARTTLS enforced, SSLContext via stdlib |
| Auth | Password or XOAUTH2 (Gmail/Outlook OAuth2) |
| SMTP blocking | `run_in_executor()` offloads sync smtplib |
| Thread references | `In-Reply-To` + `References` headers set on replies |
| Keep-alive | Single IMAP connection reused across fetches via lock |

---

## 8. Concurrency Model

```
uvicorn (4 workers, configurable via WORKERS env var)
    └── asyncio event loop per worker
          ├── step() / reset() / state() — all async-ready
          ├── DB writes → AsyncSession (non-blocking)
          ├── Attachment scan → synchronous but fast (<1ms)
          └── SMTP send → run_in_executor() (non-blocking)
```

Throughput target: **>200 concurrent agent step() calls** at P99 < 50ms
(with no actual LLM calls; add ~200–500ms per step if AI engine calls external API)

---

## 9. Deployment — HuggingFace Spaces

```bash
# 1. Init (already done)
openenv init smartinbox_env

# 2. Set HF secrets (never commit these)
#    DATABASE_URL, JWT_SECRET_KEY, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET

# 3. Push
openenv push --repo-id your-username/smartinbox-env

# 4. Verify health
curl https://your-username-smartinbox-env.hf.space/health
```

HF Spaces `README.md` header required:
```yaml
---
title: SmartInbox-Env
emoji: 📧
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
```

---

## 10. Security Hardening Checklist

### Authentication & Authorization
- [ ] Rotate `JWT_SECRET_KEY` — minimum 256-bit random value
- [ ] Set `JWT_TTL_SECONDS=3600` (1hr) or shorter for sensitive deployments
- [ ] Enable OAuth2 PKCE flow for browser-based agent UIs
- [ ] Scope JWT tokens: `env:step`, `env:reset`, `env:state` — never issue wildcards
- [ ] Rate limit per subject: 120 req/min (RateLimiter class, swap Redis in prod)

### Secrets Management
- [ ] Never commit `.env` file — use HF Spaces secrets or Vault
- [ ] Rotate DB credentials every 90 days
- [ ] Store PGP private keys in HSM or encrypted keyring, not in code
- [ ] Audit secret access with structured logs (structlog)

### Transport Security
- [ ] SMTP: enforce STARTTLS — reject plaintext connections
- [ ] IMAP: use port 993 (IMAPS) — not 143
- [ ] API: HTTPS only in production — HF Spaces handles this via nginx
- [ ] Disable TLS 1.0/1.1 in SSLContext — `ssl.TLSVersion.TLSv1_2` minimum

### Attachment & Content Security
- [ ] Scanner Layer 1–5 enabled by default (`enable_security=True`)
- [ ] Block double-extension files (e.g. `invoice.pdf.exe`)
- [ ] Quarantine (don't delete) blocked attachments for forensic review
- [ ] Set max attachment size (recommend 25MB limit)
- [ ] Production: integrate ClamAV via clamd socket for real AV scanning
- [ ] Production: add YARA rules for custom malware signatures

### Database Security
- [ ] Use least-privilege DB role (SELECT/INSERT only — no DROP/ALTER)
- [ ] Enable PostgreSQL SSL: `sslmode=require` in DATABASE_URL
- [ ] Encrypt PII columns (sender email, subject) with pgcrypto if required
- [ ] Set `statement_timeout=5000` to prevent long-running query DoS
- [ ] Enable pg_audit extension for access logging

### Container Security
- [ ] Non-root user enforced in Dockerfile (`USER appuser`)
- [ ] Multi-stage build — no build tools in runtime image
- [ ] Pin base image: `python:3.11-slim` with digest pinning in CI
- [ ] Scan image with `docker scout` or Trivy before push
- [ ] Set `read_only: true` on container filesystem (mount /app/logs as tmpfs)

### Monitoring & Incident Response
- [ ] Structured logging via structlog (JSON format for ELK/Loki ingestion)
- [ ] Alert on `security_blocks > 0` per episode (potential attack)
- [ ] Alert on JWT validation failure rate > 5% (credential stuffing)
- [ ] Alert on DB connection pool exhaustion (pool_size tuning needed)
- [ ] Set up HF Spaces uptime monitoring (UptimeRobot or similar)

---

## 11. Upgrade Roadmap (Post-Hackathon)

| Phase | Feature | Effort |
|-------|---------|--------|
| v1.1 | Swap heuristic categorizer with fine-tuned DistilBERT | Medium |
| v1.2 | Real ClamAV integration via clamd socket | Low |
| v1.3 | Redis-backed rate limiter + session store | Low |
| v1.4 | Live Gmail/Outlook OAuth2 IMAP/SMTP | Medium |
| v2.0 | LLM-powered reply drafting (Claude Haiku) graded by Claude Opus | High |
| v2.1 | Multi-tenant support with per-user inbox isolation | High |
