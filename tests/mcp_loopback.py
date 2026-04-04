"""Deterministic local fixtures for resource-access loopback tests."""

from __future__ import annotations


class LoopbackResourceStore:
    """In-memory resource store used for local resource-access tests."""

    def __init__(self, resources: dict[str, str]) -> None:
        self.resources = dict(resources)
        self.reads: list[str] = []

    def read(self, uri: str) -> str:
        self.reads.append(uri)
        return self.resources[uri]
