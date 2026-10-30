"""
Tier 1: Working Memory (In-Context Scratchpad).
Maintains the immediate context slice with sliding-window compaction to prevent context drift.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: int = 0


class WorkingMemory:
    def __init__(self, window_size: int = 10, compaction_threshold: int = 8000):
        self.window_size = window_size
        self.compaction_threshold = compaction_threshold
        self.entries: List[MemoryEntry] = []
        self.compacted_summary: Optional[str] = None

    def add_entry(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        # Rough token approximation: 1 token ~ 4 characters
        est_tokens = max(1, len(content) // 4)
        entry = MemoryEntry(
            role=role, content=content, metadata=metadata or {}, estimated_tokens=est_tokens
        )
        self.entries.append(entry)

        # Trigger compaction if limits exceeded
        if (
            len(self.entries) > self.window_size
            or self.get_total_tokens() > self.compaction_threshold
        ):
            self.compact()

    def get_total_tokens(self) -> int:
        return sum(e.estimated_tokens for e in self.entries)

    def compact(self) -> None:
        """
        Compacts the oldest entries into a consolidated summary, keeping the most recent items.
        """
        if len(self.entries) <= 3:
            return

        keep_count = min(3, len(self.entries))
        to_compact = self.entries[:-keep_count]
        self.entries = self.entries[-keep_count:]

        summaries = [
            f"[{e.role}] {e.content[:150]}..."
            if len(e.content) > 150
            else f"[{e.role}] {e.content}"
            for e in to_compact
        ]
        new_summary = "Compacted Prior Steps:\n" + "\n".join(summaries)

        if self.compacted_summary:
            self.compacted_summary += "\n" + new_summary
        else:
            self.compacted_summary = new_summary

    def get_context(self) -> str:
        """Returns the full active prompt context including compacted history."""
        lines = []
        if self.compacted_summary:
            lines.append(f"--- [Working Memory: Compacted History] ---\n{self.compacted_summary}\n")
        lines.append("--- [Working Memory: Active Scratchpad] ---")
        for e in self.entries:
            lines.append(f"[{e.role}]: {e.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.entries.clear()
        self.compacted_summary = None
