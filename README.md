---
title: SmartInbox-Pro
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

SmartInbox-Pro is a real-world OpenEnv environment for email triage. An agent receives one email at a time and must decide whether that message is `spam`, `normal`, or `urgent` through the standard `reset()`, `step()`, and `state()` interface.

Live links:

- Space: [https://huggingface.co/spaces/Vivaan13/smartinbox-pro](https://huggingface.co/spaces/Vivaan13/smartinbox-pro)
- Landing page: [https://vivaan13-smartinbox-pro.hf.space/](https://vivaan13-smartinbox-pro.hf.space/)
- Playground: [https://vivaan13-smartinbox-pro.hf.space/web/](https://vivaan13-smartinbox-pro.hf.space/web/)
- API docs: [https://vivaan13-smartinbox-pro.hf.space/docs](https://vivaan13-smartinbox-pro.hf.space/docs)

## Why This Is A Real Environment

This is not a toy game. It simulates a practical inbox-operations workflow:

- security alerts
- billing failures
- legal notices
- customer escalations
- internal newsletters and routine updates
- obvious spam and phishing-style promos

The environment gives the agent realistic observation signals such as spam likelihood, urgency, sender trust, attachment threat, thread depth, and AI summary confidence.

## What The Agent Must Do

The agent sends exactly one action per email:

```python
SmartInboxProAction(label=0)  # 0=spam, 1=normal, 2=urgent
```

The environment then returns:

- the next observation
- reward for the last action
- whether the episode is done
- metadata about the current task state

## Task Ladder

| Task | Difficulty | Emails | Goal |
|------|------------|--------|------|
| 1 | Easy | 5 | Basic classification |
| 2 | Medium | 10 | Classification plus priority ordering |
| 3 | Hard | 15 | Classification, ordering, and urgent reply drafting |

## Observation Design

Each observation includes both text fields and a structured feature vector.

Text fields:

- `subject`
- `sender`
- `body_preview`
- `thread_summary`

Structured features:

```text
[spam_score, importance, urgency, promo, response_needed,
 has_attachment, attachment_threat, pgp_signed,
 thread_depth, sender_trust, time_sensitivity, ai_category_conf]
```

## API Workflow

The standard interaction loop looks like this:

1. `reset(task_id=...)` starts a new episode and returns the first email.
2. `step(action)` applies one classification.
3. `state()` reports the current episode summary at any time.
4. The episode ends when all emails in that task have been processed.

### Example

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

## Reward Design

Per-step environment reward:

- `+1.0` for a correct classification
- `+0.25` for a near miss
- `-0.5` for a clearly wrong action

Task-level grading:

- Task 1: classification accuracy
- Task 2: `60%` classification + `40%` priority ordering
- Task 3: `40%` classification + `30%` ordering + `30%` urgent reply quality

To satisfy the hackathon validator, final task scores are clamped strictly inside `(0, 1)` rather than allowing exact `0.0` or `1.0`.

## Architecture

```text
OpenEnv Client / Playground
        |
        v
FastAPI Server (server/app.py)
        |
        v
SmartInboxProEnvironment Wrapper
        |
        v
SmartInboxEnv Core Simulator
   |        |         |
   |        |         +-- Task definitions and grading
   |        +------------ AI engine signals
   +--------------------- Security signals

Supporting scripts:
- inference.py
- evaluation_report.py
```

## Project Layout

```text
smartinbox-pro/
|-- baseline.py
|-- client.py
|-- evaluation_report.py
|-- inference.py
|-- models.py
|-- openenv.yaml
|-- pyproject.toml
|-- README.md
|-- smartinbox_env/
|   |-- env.py
|   `-- tasks.py
`-- server/
    |-- app.py
    `-- smartinbox_pro_environment.py
```

## Local Setup

### Option 1: pip

```bash
pip install -r requirements.txt
python inference.py
```

### Option 2: OpenEnv workflow

```bash
uv sync
uv run server
```

If `uv` is not on your `PATH` on Windows:

```powershell
& C:/Users/vivaa/AppData/Local/Python/pythoncore-3.14-64/Scripts/uv.exe sync
& C:/Users/vivaa/AppData/Local/Python/pythoncore-3.14-64/Scripts/uv.exe run server
```

## Validation And Benchmarking

Validate the environment:

```bash
openenv validate --verbose
```

Run the submission agent:

```bash
python inference.py
```

Generate a benchmark-style report:

```bash
python evaluation_report.py
```

Or print a machine-readable version:

```bash
python evaluation_report.py --json
```

The report includes:

- task-wise scores
- label distribution
- common confusion patterns
- average decision latency
- ordering output for multi-step tasks

## Hugging Face Deployment

Push the environment to Spaces with:

```bash
openenv push --repo-id your-username/smartinbox-pro
```

After deployment, the app serves:

- `/` for the landing page
- `/web/` for the interactive OpenEnv playground
- `/docs` for FastAPI docs
- `/health` for health checks
- `/ws` for persistent sessions

## Notes On The Playground

The default OpenEnv playground is still available, and this project also adds a cleaner visual operator view on top of it. If the embedded App tab on Hugging Face ever looks blank, use the direct `hf.space` links above; the actual environment endpoints remain the source of truth.
