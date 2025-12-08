"""
Utilities for generating configuration diffs.
"""
from difflib import SequenceMatcher, unified_diff
from typing import Iterable, List, Dict


def _normalized_lines(value: str) -> Iterable[str]:
    """
    Split text into lines preserving line endings for accurate diffs.
    """
    if value is None:
        return []
    return value.splitlines(keepends=True)


def generate_diff(old_config: str, new_config: str) -> str:
    """
    Return a unified diff between two configuration snippets.

    The diff is suitable for rendering inside a <pre> block or returning
    via the API.
    """
    diff_lines = unified_diff(
        _normalized_lines(old_config or ""),
        _normalized_lines(new_config or ""),
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "\n".join(diff_lines)


def generate_visual_diff(old_config: str, new_config: str) -> Dict[str, List[str]]:
    """
    Return structured data for a side-by-side visual diff.
    """
    old_lines = (old_config or "").splitlines()
    new_lines = (new_config or "").splitlines()
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
                left_class = "diff-changed" if left else "diff-context"
                right_class = "diff-changed" if right else "diff-context"
                append_pair(left, right, left_class, right_class)
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
