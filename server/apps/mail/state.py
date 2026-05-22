"""Mail app store — MailState + Email.

This is the Mail app's "database". It is wholly separate from the shop's
``GymState``; nothing here references the shop. Timestamps are FIXED (not
``datetime.now()``) so a reset for a given seed reproduces an identical
inbox — the environment-correctness gate requires deterministic episodes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# A fixed "today" so seeded inboxes are byte-for-byte reproducible.
SEED_DATE = "2026-05-21"


@dataclass
class Email:
    id: str
    sender: str                       # display address of the sender ("from")
    to: str
    subject: str
    body: str
    received_at: str                  # ISO-ish, sortable
    received_label: str = ""          # friendly label shown in the UI
    read: bool = False
    labels: list[str] = field(default_factory=list)
    folder: str = "inbox"             # inbox | sent | drafts
    # Structured hooks used by cross-app tasks (order confirmations /
    # receipts). Plain display emails leave these None.
    order_id: str | None = None
    tracking_url: str | None = None
    amount_total: float | None = None
    eta: str | None = None


@dataclass
class MailState:
    inbox: dict[str, Email] = field(default_factory=dict)
    sent: dict[str, Email] = field(default_factory=dict)
    drafts: dict[str, Email] = field(default_factory=dict)
    account_email: str = "alice@example.com"
    account_name: str = "Alice Anderson"
    _next: int = 1

    # ----- helpers -------------------------------------------------------- #
    def new_id(self) -> str:
        eid = f"em_{self._next}"
        self._next += 1
        return eid

    def unread_count(self) -> int:
        return sum(1 for e in self.inbox.values() if not e.read)

    def ordered_inbox(self) -> list[Email]:
        """Newest first — the order a mail client shows."""
        return sorted(
            self.inbox.values(), key=lambda e: e.received_at, reverse=True,
        )

    def get(self, email_id: str) -> Email | None:
        return self.inbox.get(email_id) or self.sent.get(email_id) \
            or self.drafts.get(email_id)

    # ----- snapshot ------------------------------------------------------- #
    def to_json(self) -> dict[str, Any]:
        return {
            "account_email": self.account_email,
            "inbox": {k: asdict(v) for k, v in self.inbox.items()},
            "sent": {k: asdict(v) for k, v in self.sent.items()},
            "drafts": {k: asdict(v) for k, v in self.drafts.items()},
            "unread_count": self.unread_count(),
        }


def make_mailstate(seed: int = 0) -> MailState:
    """A default inbox so the mail app renders non-empty in any episode.

    Cross-app tasks add task-specific emails (order confirmations,
    receipts) on top of this — either in the task factory or, at runtime,
    via the event-bus subscriber. The "Dinner this week?" note from Alex is
    a deliberate seed for the calendar-gated reply task (Phase 2).
    """
    m = MailState()
    for e in [
        Email(
            id=m.new_id(), sender="welcome@shopgym.com", to=m.account_email,
            subject="Welcome to ShopGym",
            body=(
                "Thanks for joining ShopGym!\n\n"
                "Browse today's deals and enjoy free shipping on orders "
                "over $50."
            ),
            received_at=f"{SEED_DATE}T08:00:00", received_label="8:00 AM",
            read=True, labels=["updates"],
        ),
        Email(
            id=m.new_id(), sender="deals@shopgym.com", to=m.account_email,
            subject="Your weekend deals are here",
            body=(
                "Up to 40% off electronics this weekend only. "
                "Don't miss out!"
            ),
            received_at=f"{SEED_DATE}T09:30:00", received_label="9:30 AM",
            read=False, labels=["promotions"],
        ),
        Email(
            id=m.new_id(), sender="alex@example.com", to=m.account_email,
            subject="Dinner this week?",
            body=(
                "Hey! Are you free for dinner one evening this week? "
                "Let me know what works.\n\n- Alex"
            ),
            received_at=f"{SEED_DATE}T10:15:00", received_label="10:15 AM",
            read=False, labels=[],
        ),
    ]:
        m.inbox[e.id] = e
    return m
