"""
Utilities for generating configuration diffs.

This module is intentionally framework-agnostic and safe to use
from services, API views, Celery workers, and UI rendering layers.
"""

from difflib import SequenceMatcher, unified_diff
from typing import Iterable, List, Dict, Optional


# =========================
# Normalization helpers
# =========================

def _normalized_lines(value: Optional[str]) -> List[str]:
    """
    Split text into lines preserving line endings for accurate diffs.
    """
    if not value:
        return []
    return value.splitlines(keepends=True)


def _normalized_text(value: Optional[str]) -> str:
    """
    Normalize configuration text before diffing.

    Future extensions:
    - strip timestamps
    - ignore banners
    - ignore volatile counters
    """
    return value or ""


# =========================
# Unified diff (text)
# =========================

def generate_diff(old_config: Optional[str], new_config: Optional[str]) -> str:
    """
    Return a unified diff between two configuration snippets.

    Suitable for:
    - API responses
    - <pre> rendering
    - storing in audit logs
    """
    diff_lines = unified_diff(
        _normalized_lines(_normalized_text(old_config)),
        _normalized_lines(_normalized_text(new_config)),
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "\n".join(diff_lines)


# =========================
# Visual diff (side-by-side)
# =========================

def generate_visual_diff(
    old_config: Optional[str],
    new_config: Optional[str],
) -> Dict[str, List[str]]:
    """
    Return structured data for a side-by-side visual diff.
    """
    old_lines = _normalized_text(old_config).splitlines()
    new_lines = _normalized_text(new_config).splitlines()

    matcher = SequenceMatcher(None, old_lines, new_lines)

    left_lines: List[str] = []
    right_lines: List[str] = []
    left_classes: List[str] = []
    right_classes: List[str] = []

    def append_pair(left: str, right: str, left_class: str, right_class: str):
        left_lines.append(left)
        right_lines.append(right)
        left_classes.append(left_class)
        right_classes.append(right_class)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i2 - i1):
                append_pair(
                    old_lines[i1 + idx],
                    new_lines[j1 + idx],
                    "diff-context",
                    "diff-context",
                )

        elif tag == "replace":
            old_block = old_lines[i1:i2]
            new_block = new_lines[j1:j2]
            padding = max(len(old_block), len(new_block))

            for idx in range(padding):
                left = old_block[idx] if idx < len(old_block) else ""
                right = new_block[idx] if idx < len(new_block) else ""
                append_pair(
                    left,
                    right,
                    "diff-changed" if left else "diff-context",
                    "diff-changed" if right else "diff-context",
                )

        elif tag == "delete":
            for line in old_lines[i1:i2]:
                append_pair(line, "", "diff-removed", "diff-context")

        elif tag == "insert":
            for line in new_lines[j1:j2]:
                append_pair("", line, "diff-context", "diff-added")

    return {
        "left_lines": left_lines,
        "right_lines": right_lines,
        "left_classes": left_classes,
        "right_classes": right_classes,
    }


# =========================
# Domain-level service
# =========================

class ConfigDiffService:
    """
    High-level diff service for DeviceConfiguration objects.
    """

    @staticmethod
    def diff(latest) -> str:
        """
        Return unified diff for a DeviceConfiguration instance.
        """
        if not latest or not getattr(latest, "previous", None):
            return ""
        return generate_diff(
            latest.previous.config_text,
            latest.config_text,
        )

    @staticmethod
    def visual_diff(latest) -> Dict[str, List[str]]:
        """
        Return visual diff structure for UI rendering.
        """
        if not latest or not getattr(latest, "previous", None):
            return {
                "left_lines": [],
                "right_lines": [],
                "left_classes": [],
                "right_classes": [],
            }

        return generate_visual_diff(
            latest.previous.config_text,
            latest.config_text,
        )
