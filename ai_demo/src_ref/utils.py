import re
import textwrap
from typing import List


# One indent level for docstring formatting
FORMAT_INDENT = "    "


def is_section(s: str) -> bool:
    return re.sub(r"(?!^) ", "", s).isidentifier()


def dedent(lines: List[str]) -> List[str]:
    """Dedent a list of lines."""
    return textwrap.dedent("\n".join(lines)).splitlines()


def indent(text: str, indentation: str) -> str:
    """Indent a text."""
    lines = text.splitlines()
    summary_lines = []
    rest_lines = []
    hit_section = False
    for line in lines:
        if line.endswith(":") and is_section(line[:-1].lstrip()):
            hit_section = True

        if hit_section:
            rest_lines.append(line)
        else:
            summary_lines.append(line.lstrip())

    lines = [*summary_lines, *dedent(rest_lines)]
    return "\n".join(
        f"{indentation}{line}"
        if line and i > 0
        else line
        for i, line in enumerate(lines)
    ) + "\n"


def end_of_sentence(line: str) -> bool:
    """Check if a line ends with a sentence.
    """
    return (
        line.endswith(".")
        or line.endswith("?")
        or line.endswith("!")
        or line.endswith(":")
    )


def cleanup_empty_lines(lines: List[str]) -> List[str]:
    """Remove duplicate empty lines and empty line at the end."""
    out = []
    for line in lines:
        if line == "\n":
            continue
        if line or not out or out[-1]:
            out.append(line)

    if out and not out[-1]:
        out.pop()

    return out


def strip_template_syntax(s: str) -> str:
    """Strip all paired '{{'/'}}', '{#'/'#'}', '{%'/'%}' and the content in between."""
    s = re.sub(r"\{\{.*?\}\}", "", s)
    s = re.sub(r"\{#.*?#\}", "", s)
    s = re.sub(r"\{%.*?%\}", "", s)
    return s.strip()


def replace_template_blocks(s: str) -> tuple[str, dict[str, str]]:
    """Replace all paired '{{'/'}}', '{#'/'#'}', '{%'/'%}' with placeholders
    and return the mapping."""
    mapping = {}
    idx = 0

    def replacer(match):
        nonlocal idx
        placeholder = f"<template#{idx}>"
        mapping[placeholder] = match.group(0)
        idx += 1
        return placeholder

    s = re.sub(r"\{\{.*?\}\}", replacer, s)
    s = re.sub(r"\{#.*?#\}", replacer, s)
    s = re.sub(r"\{%.*?%\}", replacer, s)
    return s.strip(), mapping
