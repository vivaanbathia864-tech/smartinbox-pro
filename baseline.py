from __future__ import annotations

import numpy as np

from smartinbox_env.env import SmartInboxEnv
from smartinbox_env.tasks import grade_task


def rule_based_agent(obs: np.ndarray) -> int:
    spam_score = obs[0]
    urgency_score = obs[2]
    if spam_score > 0.7:
        return 0
    if urgency_score > 0.7:
        return 2
    return 1


def enhanced_agent(obs: np.ndarray) -> int:
    """
    Uses the full 12-dim observation including:
    - attachment_threat (idx 6)
    - pgp_signed        (idx 7)
    - sender_trust      (idx 9)
    - ai_category_conf  (idx 11)
    """
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


def run_episode(task_id: int, agent_fn, label: str, render: bool = False) -> dict:
    env = SmartInboxEnv(
        task_id=task_id,
        render_mode="human" if render else None,
        enable_ai_engine=True,
        enable_security=True,
    )
    obs, _ = env.reset()
    predictions = []
    total_reward = 0.0
    done = False

    while not done:
        action = agent_fn(obs)
        obs, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward
        predictions.append(action)
        done = terminated or truncated

    final_score = grade_task(task_id, predictions)
    state = env.state()
    env.close()

    return {
        "agent": label,
        "task_id": task_id,
        "score": final_score,
        "reward": total_reward,
        "ai_overrides": state["ai_overrides"],
        "security_blocks": state["security_blocks"],
        "avg_latency_ms": state["avg_step_latency_ms"],
    }


def main():
    task_names = {
        1: "Easy - Basic Classification (5 emails)",
        2: "Medium - Classification + Priority (10 emails)",
        3: "Hard - Full Inbox Management (15 emails)",
    }
    agents = [
        (rule_based_agent, "RuleBased-v1  (original)"),
        (enhanced_agent, "Enhanced-v2   (12-dim obs)"),
    ]

    all_results = []

    print("\n" + "=" * 65)
    print("  SmartInbox-Pro  |  Baseline Evaluation Suite")
    print("=" * 65)

    for task_id, task_name in task_names.items():
        print(f"\n[Task] {task_name}")
        print("-" * 55)
        for agent_fn, agent_label in agents:
            result = run_episode(task_id, agent_fn, agent_label, render=False)
            all_results.append(result)
            filled = int(result["score"] * 20)
            bar = "#" * filled + "." * (20 - filled)
            print(
                f"  {agent_label:<30} "
                f"[{bar}] {result['score']:.3f}  "
                f"reward={result['reward']:+.1f}  "
                f"AI={result['ai_overrides']}  "
                f"sec={result['security_blocks']}  "
                f"lat={result['avg_latency_ms']:.1f}ms"
            )

    print("\n" + "=" * 65)
    print("  OVERALL LEADERBOARD")
    print("=" * 65)
    for agent_label in {result["agent"] for result in all_results}:
        agent_scores = [result["score"] for result in all_results if result["agent"] == agent_label]
        avg = sum(agent_scores) / len(agent_scores)
        print(f"  {agent_label:<30} avg={avg:.3f}")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
