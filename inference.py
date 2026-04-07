from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from smartinbox_env.env import SmartInboxEnv
from smartinbox_env.tasks import TASKS, grade_task

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - if you use from_docker_image().
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

LABEL_NAMES = {0: "spam", 1: "normal", 2: "urgent"}

SYSTEM_PROMPT = """
You classify emails into exactly one label.
Return strict JSON with this schema:
{"label": 0 or 1 or 2, "explanation": "short reason"}

Label rules:
- 0 = spam
- 1 = normal
- 2 = urgent

Spam is scams, fake prizes, shady promotions, or suspicious senders.
Urgent is outages, legal/compliance deadlines, billing failures, security incidents,
angry customer escalations, or anything that clearly needs fast action.
Normal is routine work mail, newsletters, reminders, and informational updates.
""".strip()


def log_event(stage: str, payload: dict[str, Any]) -> None:
    print(f"[{stage}] {json.dumps(payload, sort_keys=True)}", flush=True)


def make_llm_client() -> OpenAI | None:
    if not HF_TOKEN:
        return None
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


def heuristic_label(obs: list[float]) -> int:
    spam_score = obs[0]
    importance = obs[1]
    urgency = obs[2]
    attachment_threat = obs[6] if len(obs) > 6 else 0.0
    pgp_signed = obs[7] if len(obs) > 7 else 0.0
    sender_trust = obs[9] if len(obs) > 9 else 0.5
    ai_conf = obs[11] if len(obs) > 11 else 0.5

    if attachment_threat > 0.5:
        return 0
    if pgp_signed and importance > 0.85:
        return 2
    if sender_trust < 0.3 and spam_score > 0.5:
        return 0

    weighted_urgency = 0.6 * urgency + 0.4 * ai_conf * urgency
    weighted_spam = 0.6 * spam_score + 0.4 * (1 - sender_trust) * spam_score

    if weighted_spam > 0.65:
        return 0
    if weighted_urgency > 0.65:
        return 2
    return 1


def email_context(email: dict[str, Any], obs: list[float], task_id: int) -> str:
    return (
        f"Task {task_id}: {TASKS[task_id]['name']}\n"
        f"Subject: {email['subject']}\n"
        f"Sender: {email['sender']}\n"
        f"Body: {email['body']}\n"
        f"Features: {obs}\n"
        f"Choose the best label."
    )


def llm_label(
    client: OpenAI | None,
    email: dict[str, Any],
    obs: list[float],
    task_id: int,
) -> tuple[int, str, str]:
    fallback = heuristic_label(obs)
    if client is None:
        return fallback, "heuristic", "No HF_TOKEN set; used deterministic heuristic."

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": email_context(email, obs, task_id)},
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = json.loads(content)
        label = int(parsed["label"])
        if label not in LABEL_NAMES:
            raise ValueError(f"Unsupported label: {label}")
        explanation = str(parsed.get("explanation", "")).strip() or "LLM classification."
        return label, "llm", explanation
    except Exception as exc:
        return fallback, "heuristic-fallback", f"LLM fallback: {type(exc).__name__}"


def draft_reply(email: dict[str, Any]) -> str:
    subject = email["subject"].lower()
    if "investor" in subject or "call" in subject:
        return (
            "Hello, we acknowledge the urgency here. We can schedule a call today, "
            "confirm availability, and arrange the team response immediately."
        )
    if "legal" in subject or "copyright" in subject:
        return (
            "Hello, we acknowledge your notice. Our legal team will review this today "
            "and respond after internal review."
        )
    if "data export" in subject or "compliance" in subject:
        return (
            "Hello, we are processing the compliance data request today and our team "
            "will handle the export before the deadline."
        )
    if "fire" in subject or "offline" in subject or "critical" in subject:
        return (
            "Hello, we acknowledge the urgent issue. Our team is investigating "
            "immediately and will resolve it as soon as possible."
        )
    return (
        "Hello, we acknowledge this urgent request. Our team is reviewing it now "
        "and will respond with an update today."
    )


def run_task(task_id: int, client: OpenAI | None) -> dict[str, Any]:
    env = SmartInboxEnv(
        task_id=task_id,
        enable_ai_engine=True,
        enable_security=True,
    )
    obs, info = env.reset(task_id=task_id)
    predictions: list[int] = []
    reply_drafts: dict[str, str] = {}
    total_reward = 0.0
    done = False

    log_event(
        "START",
        {
            "task_description": TASKS[task_id]["description"],
            "task_id": task_id,
            "task_name": TASKS[task_id]["name"],
        },
    )

    while not done:
        step_position = len(predictions)
        current_email = TASKS[task_id]["emails"][step_position]
        features = [float(value) for value in obs.tolist()]
        label, mode, explanation = llm_label(client, current_email, features, task_id)

        if task_id == 3 and label == 2:
            reply_drafts[current_email["id"]] = draft_reply(current_email)

        next_obs, reward, terminated, truncated, step_info = env.step(label)
        done = bool(terminated or truncated)
        total_reward += float(reward)
        predictions.append(label)

        log_event(
            "STEP",
            {
                "action": label,
                "action_name": LABEL_NAMES[label],
                "done": done,
                "email_id": current_email["id"],
                "explanation": explanation,
                "mode": mode,
                "reward": reward,
                "step_index": len(predictions),
                "subject": current_email["subject"],
                "task_id": task_id,
            },
        )

        obs, info = next_obs, step_info

    final_score = grade_task(task_id, predictions, reply_drafts or None)
    state = env.state()
    env.close()

    summary = {
        "avg_step_latency_ms": state["avg_step_latency_ms"],
        "predictions": predictions,
        "reply_drafts": len(reply_drafts),
        "reward": round(total_reward, 3),
        "score": final_score,
        "task_id": task_id,
        "task_name": TASKS[task_id]["name"],
    }
    log_event("END", summary)
    return summary


def main() -> None:
    client = make_llm_client()
    log_event(
        "START",
        {
            "api_base_url": API_BASE_URL,
            "hf_token_present": bool(HF_TOKEN),
            "local_image_name": LOCAL_IMAGE_NAME,
            "model_name": MODEL_NAME,
            "script": "inference.py",
        },
    )

    task_summaries = [run_task(task_id, client) for task_id in sorted(TASKS)]
    average_score = round(
        sum(item["score"] for item in task_summaries) / len(task_summaries),
        3,
    )

    log_event(
        "END",
        {
            "average_score": average_score,
            "tasks": task_summaries,
        },
    )


if __name__ == "__main__":
    main()
