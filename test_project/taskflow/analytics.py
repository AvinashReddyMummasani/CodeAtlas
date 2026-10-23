"""
analytics.py — Statistical analysis and reporting for TaskFlow.
Generates insights from task data including trends and performance metrics.
"""

from collections import Counter
from typing import Any


def analyze_tasks(tasks: list[dict]) -> dict[str, Any]:
    """
    Compute aggregate statistics from a list of task dicts.

    Args:
        tasks: List of task dicts (from TaskManager.get_all_tasks()).

    Returns:
        Dict with keys: total, completion_rate, by_priority, by_status,
        top_tags, average_tags_per_task.
    """
    if not tasks:
        return {"total": 0, "error": "No tasks to analyze."}

    total = len(tasks)
    done_count = sum(1 for t in tasks if t.get("status") == "DONE")
    completion_rate = round(done_count / total * 100, 1)

    priority_counts = Counter(t.get("priority", "UNKNOWN") for t in tasks)
    status_counts = Counter(t.get("status", "UNKNOWN") for t in tasks)

    all_tags = []
    for task in tasks:
        all_tags.extend(task.get("tags", []))
    tag_counts = Counter(all_tags)
    top_tags = tag_counts.most_common(5)

    avg_tags = round(len(all_tags) / total, 2)

    return {
        "total": total,
        "completion_rate": f"{completion_rate}%",
        "by_priority": dict(priority_counts),
        "by_status": dict(status_counts),
        "top_tags": top_tags,
        "average_tags_per_task": avg_tags,
    }


def compute_velocity(completed_tasks: list[dict], period_days: int = 7) -> dict:
    """
    Calculate task completion velocity over a time period.

    Args:
        completed_tasks: Tasks with status DONE and completed_at timestamps.
        period_days: Rolling window for velocity calculation.

    Returns:
        Dict with tasks_per_day, trend (UP/DOWN/STABLE).
    """
    if not completed_tasks or period_days <= 0:
        return {"tasks_per_day": 0.0, "trend": "STABLE"}

    done = [t for t in completed_tasks if t.get("status") == "DONE" and t.get("completed_at")]
    if not done:
        return {"tasks_per_day": 0.0, "trend": "STABLE"}

    velocity = round(len(done) / period_days, 2)
    trend = "UP" if velocity > 1.0 else ("STABLE" if velocity == 1.0 else "DOWN")
    return {"tasks_per_day": velocity, "trend": trend}


def find_bottlenecks(tasks: list[dict]) -> list[dict]:
    """
    Identify HIGH priority tasks that are still PENDING — potential bottlenecks.

    Returns:
        Sorted list of high-priority pending tasks.
    """
    bottlenecks = [
        t for t in tasks
        if t.get("priority") == "HIGH" and t.get("status") == "PENDING"
    ]
    return sorted(bottlenecks, key=lambda t: t.get("created_at", ""))


def tag_cooccurrence(tasks: list[dict]) -> dict[str, list[str]]:
    """
    Build a tag co-occurrence map: for each tag, which other tags appear with it?
    Useful for understanding task clustering.
    """
    cooccur: dict[str, set] = {}
    for task in tasks:
        tags = task.get("tags", [])
        for tag in tags:
            if tag not in cooccur:
                cooccur[tag] = set()
            cooccur[tag].update(t for t in tags if t != tag)
    return {k: sorted(v) for k, v in cooccur.items()}
