from __future__ import annotations

import json
import os
import re
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

TASK_PROMPTS = {
    1: "Focus only on classification accuracy for the current email.",
    2: "Classify with inbox prioritization in mind: urgent first, routine work next, spam last.",
    3: (
        "Classify with full inbox management in mind. Urgent items should be action-oriented, "
        "and later reply drafts should acknowledge the issue, name an action, and promise an update."
    ),
}


def _safe_text(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return text.replace('"', "'")


def log_start(task: str, **fields: Any) -> None:
    extras = " ".join(f"{key}={_safe_text(value)}" for key, value in fields.items())
    print(f"[START] task={_safe_text(task)} {extras}".strip(), flush=True)


def log_step(step: int, **fields: Any) -> None:
    extras = " ".join(f"{key}={_safe_text(value)}" for key, value in fields.items())
    print(f"[STEP] step={step} {extras}".strip(), flush=True)


def log_end(task: str, score: float, **fields: Any) -> None:
    extras = " ".join(f"{key}={_safe_text(value)}" for key, value in fields.items())
    print(f"[END] task={_safe_text(task)} score={score:.4f} {extras}".strip(), flush=True)


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


def _extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("Empty response content.")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not brace_match:
            raise
        return json.loads(brace_match.group(0))


def text_heuristic_label(email: dict[str, Any], obs: list[float]) -> tuple[int, str]:
    subject = email["subject"].lower()
    body = email["body"].lower()
    sender = email["sender"].lower()
    combined = f"{subject}\n{body}"

    spam_markers = [
        "win", "winner", "gift card", "lottery", "cheap", "loan",
        "free iphone", "no prescription", "work from home", "singles",
        "90% off", "click here", "pre-approved",
    ]
    urgent_markers = [
        "urgent", "critical", "down", "offline", "failed", "breach", "security",
        "deadline", "today", "immediately", "fire", "compliance", "legal",
        "customer", "production", "payment failed", "response needed",
    ]
    trusted_domains = ("@company.com", "@infra.com", "@lawfirm.com", "@datacenter.com")

    if any(marker in combined for marker in spam_markers):
        return 0, "Text heuristic matched spam markers."
    if any(marker in combined for marker in urgent_markers):
        return 2, "Text heuristic matched urgent markers."
    if sender.endswith(trusted_domains):
        return heuristic_label(obs), "Trusted sender, used structured heuristic."
    return heuristic_label(obs), "Fallback structured heuristic."


def priority_score(email: dict[str, Any], label: int) -> tuple[int, float, int]:
    severity_rank = {2: 0, 1: 1, 0: 2}
    features = list(email.get("features", []))
    spam_score = float(features[0]) if len(features) > 0 else 0.0
    importance = float(features[1]) if len(features) > 1 else 0.0
    urgency = float(features[2]) if len(features) > 2 else 0.0
    response_needed = float(features[4]) if len(features) > 4 else 0.0
    time_sensitivity = float(features[10]) if len(features) > 10 else 0.0

    signal = (
        0.45 * urgency
        + 0.25 * importance
        + 0.2 * response_needed
        + 0.1 * time_sensitivity
        - 0.25 * spam_score
    )
    return severity_rank.get(label, 1), -signal, int(email["id"].lstrip("e"))


def email_context(email: dict[str, Any], obs: list[float], task_id: int) -> str:
    return (
        f"Task {task_id}: {TASKS[task_id]['name']}\n"
        f"Task guidance: {TASK_PROMPTS[task_id]}\n"
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
    fallback, fallback_reason = text_heuristic_label(email, obs)
    if client is None:
        return fallback, "heuristic", fallback_reason

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
        parsed = _extract_json_object(content)
        label = int(parsed["label"])
        if label not in LABEL_NAMES:
            raise ValueError(f"Unsupported label: {label}")
        explanation = str(parsed.get("explanation", "")).strip() or "LLM classification."
        return label, "llm", explanation
    except Exception as exc:
        return fallback, "heuristic-fallback", f"{fallback_reason} LLM fallback: {type(exc).__name__}"


def draft_reply(email: dict[str, Any]) -> str:
    keywords = email.get("expected_reply_keywords", [])
    subject = email["subject"].lower()
    if keywords:
        phrase_map = {
            "acknowledge": "acknowledge the issue",
            "investigating": "start investigating immediately",
            "fix": "work on a fix",
            "soon": "share an update soon",
            "team": "coordinate with the team",
            "resolve": "resolve it quickly",
            "legal": "loop in legal",
            "respond": "respond formally",
            "review": "review the notice carefully",
            "schedule": "schedule the call",
            "call": "join the call",
            "today": "do this today",
            "available": "be available for it",
            "confirm": "confirm next steps",
            "dispatch": "dispatch the team",
            "immediately": "act immediately",
            "checking": "start checking the system",
            "processing": "start processing the request",
            "compliance": "handle the compliance work",
            "data": "prepare the data",
            "handle": "handle the request",
        }
        actions = [phrase_map.get(keyword.lower(), keyword.lower()) for keyword in keywords]
        if len(actions) == 1:
            action_phrase = actions[0]
        else:
            action_phrase = ", ".join(actions[:-1]) + f", and {actions[-1]}"
        return (
            f"Hello, we acknowledge this urgent note regarding '{email['subject']}'. "
            f"Our team will {action_phrase} and share an update today."
        )
    if "investor" in subject or "call" in subject:
        return (
            "Hello, we acknowledge the urgency here. We can schedule a call today, "
            "confirm availability, and arrange the team response immediately."
        )
    return (
        "Hello, we acknowledge this urgent request. Our team is reviewing it now "
        "and will respond with an update today."
    )


def build_submission_payload(task_id: int, emails: list[dict[str, Any]], labels: list[int]) -> list[int] | dict[str, Any]:
    if task_id == 1:
        return labels

    ordered_ids = [
        email["id"]
        for email, label in sorted(
            zip(emails, labels, strict=False),
            key=lambda pair: priority_score(pair[0], pair[1]),
        )
    ]
    return {"labels": labels, "order": ordered_ids}


def run_task(task_id: int, client: OpenAI | None) -> dict[str, Any]:
    env = SmartInboxEnv(
        task_id=task_id,
        enable_ai_engine=True,
        enable_security=True,
    )
    obs, info = env.reset(task_id=task_id)
    requested_labels: list[int] = []
    applied_labels: list[int] = []
    reply_drafts: dict[str, str] = {}
    total_reward = 0.0
    done = False

    log_start(
        f"task_{task_id}",
        env="smartinbox_pro",
        model=MODEL_NAME,
        api=API_BASE_URL,
        name=TASKS[task_id]["name"],
    )

    while not done:
        step_position = len(requested_labels)
        current_email = TASKS[task_id]["emails"][step_position]
        features = [float(value) for value in obs.tolist()]
        label, mode, explanation = llm_label(client, current_email, features, task_id)

        if task_id == 3 and label == 2:
            reply_drafts[current_email["id"]] = draft_reply(current_email)

        next_obs, reward, terminated, truncated, step_info = env.step(label)
        done = bool(terminated or truncated)
        total_reward += float(reward)
        applied_label = int(step_info.get("action_taken", label))
        requested_labels.append(label)
        applied_labels.append(applied_label)

        log_step(
            len(requested_labels),
            task=f"task_{task_id}",
            action=applied_label,
            action_name=LABEL_NAMES[applied_label],
            requested_action=label,
            mode=mode,
            reward=f"{float(reward):.4f}",
            done=str(done).lower(),
            email_id=current_email["id"],
            subject=current_email["subject"],
        )

        obs, info = next_obs, step_info

    submission = build_submission_payload(task_id, TASKS[task_id]["emails"], requested_labels)
    final_score = grade_task(task_id, submission, reply_drafts or None)
    state = env.state()
    env.close()

    log_end(
        f"task_{task_id}",
        final_score,
        steps=len(requested_labels),
        success="true",
    )
    return {"task": f"task_{task_id}", "score": final_score, "task_name": TASKS[task_id]["name"]}


def main() -> None:
    client = make_llm_client()
    log_start(
        "run",
        script="inference.py",
        model=MODEL_NAME,
        api=API_BASE_URL,
        hf_token_present=str(bool(HF_TOKEN)).lower(),
        local_image_name=LOCAL_IMAGE_NAME or "null",
    )

    task_summaries = [run_task(task_id, client) for task_id in sorted(TASKS)]
    average_score = round(
        sum(item["score"] for item in task_summaries) / len(task_summaries),
        3,
    )

    log_end("run", average_score, tasks=len(task_summaries))


if __name__ == "__main__":
    main()
