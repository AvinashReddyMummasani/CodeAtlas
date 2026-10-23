"""
task_manager.py — Core task management logic for TaskFlow.
Handles CRUD operations, filtering, and priority queues.
"""

from utils import generate_id, get_timestamp
from typing import Optional


class Task:
    """Represents a single task with metadata."""

    def __init__(self, title: str, priority: str = "MEDIUM", tags: list = None):
        self.id = generate_id()
        self.title = title
        self.priority = priority.upper()
        self.status = "PENDING"
        self.tags = tags or []
        self.created_at = get_timestamp()
        self.completed_at = None
        self.subtasks = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "tags": self.tags,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "subtasks": [s.to_dict() for s in self.subtasks],
        }

    def add_subtask(self, title: str) -> "Task":
        sub = Task(title, priority=self.priority)
        self.subtasks.append(sub)
        return sub


class TaskManager:
    """
    Central task manager.
    Stores tasks in memory and provides filtering, search, and statistics.
    """

    PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def add_task(self, title: str, priority: str = "MEDIUM", tags: list = None) -> str:
        """Create a new task and return its ID."""
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty.")
        task = Task(title.strip(), priority=priority, tags=tags)
        self._tasks[task.id] = task
        return task.id

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed. Returns False if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = "DONE"
        task.completed_at = get_timestamp()
        return True

    def delete_task(self, task_id: str) -> bool:
        """Remove a task by ID."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[dict]:
        """Retrieve a task by ID as a dict."""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def get_all_tasks(self) -> list[dict]:
        """Return all tasks sorted by priority then created_at."""
        tasks = [t.to_dict() for t in self._tasks.values()]
        tasks.sort(key=lambda t: (self.PRIORITY_ORDER.get(t["priority"], 99), t["created_at"]))
        return tasks

    def filter_tasks(self, priority: str = None, status: str = None, tag: str = None) -> list[dict]:
        """Filter tasks by one or more criteria."""
        results = []
        for task in self._tasks.values():
            td = task.to_dict()
            if priority and td["priority"] != priority.upper():
                continue
            if status and td["status"] != status.upper():
                continue
            if tag and tag not in td["tags"]:
                continue
            results.append(td)
        results.sort(key=lambda t: self.PRIORITY_ORDER.get(t["priority"], 99))
        return results

    def search_tasks(self, query: str) -> list[dict]:
        """Full-text search over task titles and tags."""
        q = query.lower()
        matches = []
        for task in self._tasks.values():
            td = task.to_dict()
            if q in td["title"].lower() or any(q in tag.lower() for tag in td["tags"]):
                matches.append(td)
        return matches

    def bulk_complete(self, task_ids: list[str]) -> dict:
        """Complete multiple tasks at once. Returns summary."""
        succeeded, failed = [], []
        for tid in task_ids:
            if self.complete_task(tid):
                succeeded.append(tid)
            else:
                failed.append(tid)
        return {"completed": succeeded, "not_found": failed}

    def get_stats(self) -> dict:
        """Return a summary statistics dict."""
        all_tasks = list(self._tasks.values())
        total = len(all_tasks)
        done = sum(1 for t in all_tasks if t.status == "DONE")
        pending = total - done
        by_priority = {}
        for task in all_tasks:
            p = task.priority
            by_priority[p] = by_priority.get(p, 0) + 1
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "by_priority": by_priority,
            "completion_rate": round(done / total * 100, 1) if total else 0,
        }
