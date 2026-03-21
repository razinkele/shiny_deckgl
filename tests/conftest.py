"""Shared test fixtures and stubs for shiny_deckgl tests."""
from __future__ import annotations


class _FakeSession:
    """Test double for Shiny Session — captures send_custom_message calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    async def send_custom_message(self, handler: str, payload: dict) -> None:
        self.messages.append((handler, payload))

    def clear(self) -> None:
        self.messages.clear()
