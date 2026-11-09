"""Deterministic history compaction using tiktoken's cl100k accounting.

Token counts are estimates for the selected tiktoken encoding and can differ
from the native tokenizer used by a remote provider.
"""
from __future__ import annotations

import re
import tiktoken


class ContextEngine:
    """Keep useful recent history and diagnostics within a strict token cap."""

    CRITICAL_HEADING = "--- CRITICAL HISTORY TELEMETRY ---\n"
    RECENT_HEADING = "\n--- RECENT WORKING HISTORY ---\n"
    _CRITICAL = re.compile(r"\b(fail(?:ed|ure)?|error|exception|traceback|syntax)\b", re.I)

    def __init__(self, token_limit: int = 3500, model_name: str = "gpt-4") -> None:
        if token_limit < 0:
            raise ValueError("token_limit must be non-negative")
        self.token_limit = token_limit
        self.history: list[dict[str, str]] = []
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except (KeyError, ValueError):
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def add_interaction(self, role: str, content: str) -> None:
        self.history.append({"role": str(role), "content": str(content)})

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def _render(self, diagnostics: list[str], recent: list[str]) -> str:
        output = ""
        if diagnostics:
            output += self.CRITICAL_HEADING + "".join(diagnostics)
        if recent:
            output += self.RECENT_HEADING + "".join(recent)
        return output

    def _bounded(self, text: str, limit: int) -> str:
        """Return a deterministic prefix no longer than limit tokens."""
        if self.count_tokens(text) <= limit:
            return text
        marker = " ...[truncated]"
        lo, hi = 0, len(text)
        best = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = text[:mid].rstrip() + marker
            if self.count_tokens(candidate) <= limit:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        if best:
            return best
        # A tiny budget may not fit the marker; retain only the largest fitting prefix.
        lo, hi = 0, len(text)
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = text[:mid]
            if self.count_tokens(candidate) <= limit:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _bounded_entry(self, text: str, diagnostics: list[str], recent: list[str]) -> str:
        """Compact a history entry against the complete rendered output."""
        lo, hi = 0, len(text)
        best = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = text[:mid].rstrip() + " ...[truncated]"
            if self.count_tokens(self._render(diagnostics, recent + [candidate])) <= self.token_limit:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        if best:
            return best
        lo, hi = 0, len(text)
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = text[:mid]
            if self.count_tokens(self._render(diagnostics, recent + [candidate])) <= self.token_limit:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _bounded_diagnostic(self, text: str, limit: int) -> str:
        """Keep a diagnostic's identifying prefix and most useful tail."""
        if self.count_tokens(text) <= limit:
            return text
        marker = "\n...[diagnostic truncated]...\n"
        prefix = text[: min(120, len(text))]
        lo, hi = 0, len(text)
        best = ""
        while lo <= hi:
            size = (lo + hi) // 2
            suffix = text[len(text) - size:] if size else ""
            candidate = prefix.rstrip() + marker + suffix
            if self.count_tokens(candidate) <= limit:
                best = candidate
                lo = size + 1
            else:
                hi = size - 1
        return best or self._bounded(text, limit)

    def compress_context(self) -> str:
        """Prioritize recent unique diagnostics, then backfill recent history."""
        diagnostics: list[str] = []
        recent: list[str] = []
        seen: set[str] = set()

        diagnostic_entries = []
        for item in reversed(self.history):
            content = item["content"].strip()
            key = content.casefold()
            if content and self._CRITICAL.search(content) and key not in seen:
                seen.add(key)
                diagnostic_entries.append(
                    f"[{item['role'].upper()} ERROR]: {content}\n"
                )

        for entry in diagnostic_entries:
            # Per-message bound prevents one traceback from crowding out others.
            snippet = self._bounded_diagnostic(entry, min(500, self.token_limit))
            candidate = diagnostics + [snippet]
            if self.count_tokens(self._render(candidate, [])) <= self.token_limit:
                diagnostics = candidate

        for item in reversed(self.history):
            content = item["content"].strip()
            if not content:
                continue
            key = content.casefold()
            if key in seen:
                continue
            entry = f"{item['role']}: {content}\n"
            # If the whole entry does not fit, compact it and keep searching older history.
            candidate = recent + [entry]
            if self.count_tokens(self._render(diagnostics, candidate)) > self.token_limit:
                entry = self._bounded_entry(entry, diagnostics, recent)
                if not entry:
                    continue
                candidate = recent + [entry]
            if self.count_tokens(self._render(diagnostics, candidate)) <= self.token_limit:
                recent = candidate

        result = self._render(diagnostics, recent)
        # Headings themselves may exceed a very small configured budget.
        if self.count_tokens(result) > self.token_limit:
            return self._bounded(result, self.token_limit)
        return result
