"""
main.py — Entry point for TaskFlow, the test Python project.
A small task management CLI application to test CodeAtlas.
"""

from task_manager import TaskManager
from analytics import analyze_tasks
from utils import format_table, generate_id

def main():
    """Main entry point. Runs the TaskFlow CLI."""
    manager = TaskManager()

    # Seed some sample data
    t1 = manager.add_task("Build login page", priority="HIGH", tags=["frontend", "auth"])
    t2 = manager.add_task("Write unit tests", priority="MEDIUM", tags=["testing"])
    t3 = manager.add_task("Setup CI/CD pipeline", priority="HIGH", tags=["devops"])
    t4 = manager.add_task("Code review session", priority="LOW", tags=["team"])
    t5 = manager.add_task("Fix pagination bug", priority="HIGH", tags=["frontend", "bug"])

    manager.complete_task(t1)
    manager.complete_task(t4)

    print("=== TaskFlow Dashboard ===\n")
    all_tasks = manager.get_all_tasks()
    rows = [(t["id"][:8], t["title"], t["priority"], t["status"]) for t in all_tasks]
    print(format_table(["ID", "Title", "Priority", "Status"], rows))

    print("\n=== Analytics ===")
    stats = analyze_tasks(all_tasks)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n=== High Priority Pending ===")
    urgent = manager.filter_tasks(priority="HIGH", status="PENDING")
    for task in urgent:
        print(f"  [{task['id'][:8]}] {task['title']}")


if __name__ == "__main__":
    main()
