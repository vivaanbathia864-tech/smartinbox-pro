---
title: SmartInbox-Pro
emoji: "📧"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /
tags:
  - openenv
  - email-triage
  - reinforcement-learning
---

# SmartInbox-Pro

SmartInbox-Pro is a real-world OpenEnv environment for email triage. An agent receives one email at a time and must classify it as `spam`, `normal`, or `urgent` through the standard `reset()`, `step()`, and `state()` API.

Direct live links:

- App landing page: [https://vivaan13-smartinbox-pro.hf.space/](https://vivaan13-smartinbox-pro.hf.space/)
- Playground: [https://vivaan13-smartinbox-pro.hf.space/web/](https://vivaan13-smartinbox-pro.hf.space/web/)
- API docs: [https://vivaan13-smartinbox-pro.hf.space/docs](https://vivaan13-smartinbox-pro.hf.space/docs)
- Demo video: [https://youtu.be/wlyQTeDSbRY?si=Fm_6MxIwwEVK-TPu](https://youtu.be/wlyQTeDSbRY?si=Fm_6MxIwwEVK-TPu)

This project wraps the existing `smartinbox_env` simulation in the OpenEnv server scaffold expected by the Meta PyTorch OpenEnv hackathon and Hugging Face Spaces.

## What This Environment Simulates

- Inbox triage for realistic email operations instead of a toy game
- Three tasks with increasing difficulty
- AI-assisted signals such as confidence and thread summaries
- Security signals such as attachment threat scoring and PGP verification
- Meaningful rewards with partial credit for near-miss classifications

## Action Space

The agent sends a typed action:

```python
SmartInboxProAction(label=0)  # 0=spam, 1=normal, 2=urgent
```

## Observation Space

Each observation contains:

- `features`: 12-dimensional float vector
- `subject`, `sender`, `body_preview`
- `thread_summary`
- task metadata such as `task_id`, `difficulty`, and remaining emails
- standard OpenEnv fields: `done`, `reward`, `metadata`

Feature order:

```text
[spam_score, importance, urgency, promo, response_needed,
 has_attachment, attachment_threat, pgp_signed,
 thread_depth, sender_trust, time_sensitivity, ai_category_conf]
```

## Tasks

| Task | Difficulty | Emails | Goal |
|------|------------|--------|------|
| 1 | Easy | 5 | Basic classification |
| 2 | Medium | 10 | Classification plus prioritization context |
| 3 | Hard | 15 | Full inbox management scenario |

Select a task by passing `task_id` to `reset()`:

```python
result = await env.reset(task_id=2)
```

## Reward Design

- `+1.0` for a correct classification
- `+0.25` for a near miss
- `-0.5` for a clearly wrong classification

## Local Setup

### Option 1: pip

```bash
pip install -r requirements.txt
python inference.py
```

### Option 2: OpenEnv-native workflow

```bash
uv sync
uv run server
```

If `uv` is not on your `PATH` on Windows, use the installed script directly:

```powershell
& C:/Users/vivaa/AppData/Local/Python/pythoncore-3.14-64/Scripts/uv.exe sync
& C:/Users/vivaa/AppData/Local/Python/pythoncore-3.14-64/Scripts/uv.exe run server
```

## Validate for OpenEnv

```bash
openenv validate --verbose
```

## Deploy to Hugging Face Spaces

```bash
openenv push --repo-id your-username/smartinbox-pro
```

After deployment, the Space provides:

- `/web` for the OpenEnv web interface
- `/docs` for the FastAPI/OpenAPI docs
- `/health` for health checks
- `/ws` for persistent WebSocket sessions

## Example Client Usage

```python
import asyncio

from smartinbox_pro import SmartInboxProAction, SmartInboxProEnv


async def main():
    async with SmartInboxProEnv(base_url="http://localhost:8000") as env:
        result = await env.reset(task_id=1)
        print(result.observation.subject)

        result = await env.step(SmartInboxProAction(label=1))
        print(result.reward, result.done)


asyncio.run(main())
```

## Project Structure

```text
smartinbox-pro/
|-- baseline.py
|-- client.py
|-- inference.py
|-- models.py
|-- openenv.yaml
|-- pyproject.toml
|-- smartinbox_env/
`-- server/
    |-- app.py
    `-- smartinbox_pro_environment.py
```
