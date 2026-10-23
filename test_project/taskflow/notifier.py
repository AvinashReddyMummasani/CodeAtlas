"""
notifier.py — Notification system for TaskFlow.
Sends task reminders and completion alerts via multiple channels (mock).
"""

import logging
from utils import get_timestamp, truncate

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Base class for notification delivery channels."""

    def send(self, title: str, message: str, priority: str = "MEDIUM") -> bool:
        raise NotImplementedError


class ConsoleNotifier(NotificationChannel):
    """Prints notifications to the console (for dev/testing)."""

    def send(self, title: str, message: str, priority: str = "MEDIUM") -> bool:
        prefix = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "ℹ")
        print(f"{prefix} [{priority}] {title}: {message}")
        return True


class MockEmailNotifier(NotificationChannel):
    """Simulates sending email notifications (mock, no real email sent)."""

    def __init__(self, smtp_host: str = "localhost", port: int = 25):
        self.smtp_host = smtp_host
        self.port = port
        self._sent: list[dict] = []

    def send(self, title: str, message: str, priority: str = "MEDIUM") -> bool:
        record = {
            "to": "user@example.com",
            "subject": f"[TaskFlow] {priority}: {truncate(title, 40)}",
            "body": message,
            "timestamp": get_timestamp(),
        }
        self._sent.append(record)
        logger.info("MockEmail: sent '%s'", record["subject"])
        return True

    def get_sent(self) -> list[dict]:
        return list(self._sent)


class NotificationDispatcher:
    """
    Dispatches notifications to multiple channels.
    Only sends HIGH priority to all channels; MEDIUM/LOW to console only.
    """

    def __init__(self):
        self._channels: list[NotificationChannel] = [ConsoleNotifier()]
        self._email = MockEmailNotifier()

    def add_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    def notify(self, title: str, message: str, priority: str = "MEDIUM") -> None:
        for channel in self._channels:
            try:
                channel.send(title, message, priority)
            except Exception as exc:
                logger.warning("Notification channel failed: %s", exc)

        if priority == "HIGH":
            try:
                self._email.send(title, message, priority)
            except Exception as exc:
                logger.warning("Email notification failed: %s", exc)

    def notify_task_completed(self, task: dict) -> None:
        title = f"Task Completed"
        msg = f"'{task.get('title', 'Unknown')}' has been marked as done."
        self.notify(title, msg, priority=task.get("priority", "LOW"))

    def notify_overdue(self, tasks: list[dict]) -> None:
        if not tasks:
            return
        for task in tasks:
            self.notify(
                title="Overdue Task",
                message=f"'{task.get('title')}' is still pending.",
                priority="HIGH",
            )
