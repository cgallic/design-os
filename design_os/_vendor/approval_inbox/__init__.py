"""Approval Inbox — a universal gated action queue for autonomous agents."""

from .store import ApprovalStore, StateError, stub_executor

__all__ = ["ApprovalStore", "StateError", "stub_executor"]
__version__ = "0.1.0"
