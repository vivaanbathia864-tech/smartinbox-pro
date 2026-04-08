from __future__ import annotations

import argparse
import json
import time
from collections import Counter

from smartinbox_env.tasks import TASKS, grade_task
from inference import build_submission_payload, draft_reply, llm_label, make_llm_client


def _label_name(label: int) -> str:
    return {0: "spam", 1: "normal", 2: "urgent"}.get(label, str(label))


def _common_mistakes(confusion: Counter[tuple[int, int]]) -> list[str]:
    mistakes = []
    for (truth, pred), count in sorted(confusion.items(), key=lambda item: item[1], reverse=True):
        if truth == pred:
            continue
        mistakes.append(f"{count}x {_label_name(truth)} predicted as {_label_name(pred)}")
    return mistakes or ["No mistakes in this run."]


def build_report() -> dict:
    client = make_llm_client()
    overall_scores: list[float] = []
    overall_latencies: list[float] = []
    tasks_summary = []

    for task_id, task in TASKS.items():
        labels = []
        confusion = Counter()
        reply_drafts = {}
        per_email_latencies_ms = []

        for email in task["emails"]:
            started = time.perf_counter()
            label, mode, reason = llm_label(client, email, email["features"], task_id)
            elapsed_ms = (time.perf_counter() - started) * 1000
            labels.append(label)
            confusion[(email["label"], label)] += 1
            per_email_latencies_ms.append(elapsed_ms)
            if task_id == 3 and label == 2:
                reply_drafts[email["id"]] = draft_reply(email)

        submission = build_submission_payload(task_id, task["emails"], labels)
        score = grade_task(task_id, submission, reply_drafts or None)
        avg_latency_ms = sum(per_email_latencies_ms) / len(per_email_latencies_ms)
        overall_scores.append(score)
        overall_latencies.extend(per_email_latencies_ms)

        label_counts = {
            _label_name(label): count
            for label, count in sorted(Counter(labels).items())
        }
        task_summary = {
            "task_id": task_id,
            "task_name": task["name"],
            "difficulty": task["difficulty"],
            "score": score,
            "average_latency_ms": round(avg_latency_ms, 2),
            "predicted_label_counts": label_counts,
            "common_mistakes": _common_mistakes(confusion),
            "priority_order": submission["order"] if isinstance(submission, dict) else None,
            "urgent_reply_count": len(reply_drafts),
            "sample_reply": next(iter(reply_drafts.values()), None),
        }
        tasks_summary.append(task_summary)

    average_score = sum(overall_scores) / len(overall_scores)
    average_latency = sum(overall_latencies) / len(overall_latencies)
    return {
        "project": "SmartInbox-Pro",
        "tasks": tasks_summary,
        "summary": {
            "task_scores": overall_scores,
            "average_score": round(average_score, 3),
            "average_latency_ms": round(average_latency, 2),
        },
    }


def print_report(report: dict) -> None:
    print("SmartInbox-Pro Evaluation Report")
    print("=" * 40)

    for task_summary in report["tasks"]:
        print(f"\nTask {task_summary['task_id']}: {task_summary['task_name']}")
        print(f"Difficulty: {task_summary['difficulty']}")
        print(f"Score: {task_summary['score']}")
        print(f"Average decision latency: {task_summary['average_latency_ms']:.2f} ms")
        print(f"Predicted label counts: {json.dumps(task_summary['predicted_label_counts'], indent=2)}")
        print("Common mistakes:")
        for line in task_summary["common_mistakes"]:
            print(f"  - {line}")
        if task_summary["urgent_reply_count"]:
            print(f"Urgent replies drafted: {task_summary['urgent_reply_count']}")
        if task_summary["sample_reply"]:
            print(f"Sample reply: {task_summary['sample_reply']}")
        if task_summary["priority_order"]:
            print(f"Priority order: {task_summary['priority_order']}")

    print("\nFinal Benchmark Summary")
    print("-" * 40)
    print(f"Task-wise scores: {report['summary']['task_scores']}")
    print(f"Average score: {report['summary']['average_score']:.3f}")
    print(f"Average decision latency: {report['summary']['average_latency_ms']:.2f} ms")


def run_report(json_output: bool = False) -> None:
    report = build_report()
    if json_output:
        print(json.dumps(report, indent=2))
        return

    print_report(report)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a benchmark-style evaluation for SmartInbox-Pro.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON instead of human-readable text.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_report(json_output=args.json)


if __name__ == "__main__":
    main()
