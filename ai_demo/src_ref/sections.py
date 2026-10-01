from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Mapping, MutableMapping

import re
import warnings
from copy import deepcopy

from diot import Diot, OrderedDiot
from pipen.defaults import ProcInputType
from pipen.exceptions import ProcOutputTypeError

from .utils import (
    FORMAT_INDENT,
    dedent,
    end_of_sentence,
    cleanup_empty_lines,
    strip_template_syntax,
    replace_template_blocks,
)

ITEM_LINE_REGEX = re.compile(
    r"^(?P<name>[^\s]+)\s*(?:\((?P<attrs>.+?)\))?:(?P<help>.+)?$"
)
ITEM_ATTR_REGEX = re.compile(r"^(?P<name>[\w-]+)(?:\s*[:=]\s*(?P<value>.+))?$")


class MalFormattedAnnotationError(Exception):
    """Raised when the annotation is malformatted"""


class UnknownAnnotationItemWarning(Warning):
    """Raised when the annotation item is unknown"""


class Mixin:

    def _set_meta(self, key: str, value: Any) -> None:
        self.__diot__[f"_{key}"] = value  # type: ignore[assignment]

    def _get_meta(self, key: str) -> Any:
        return self.__diot__.get(f"_{key}")  # type: ignore[union-attr]

    def __iadd__(self, other: str) -> str:
        return f"{self}{other}"

    def to_markdown(
        self,
        show_hidden: bool = False,
    ) -> str:  # pragma: no cover
        return str(self)


class ItemAttrs(Mixin, OrderedDiot):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("diot_nest", False)
        super().__init__(*args, **kwargs)
        self._set_meta("origin", [])

    def __str__(self) -> str:
        out = []
        for key in self._get_meta("origin"):
            value = self[key]
            if value is True:
                out.append(key)
            else:
                out.append(f"{key}={value}")
        return ";".join(out)

    def to_markdown(self, show_hidden: bool = False) -> str:
        out = str(self)
        return f"*(`{out}`)*" if out else ""


def _ipython_to_markdown(lines: List[str]) -> List[str]:
    """Convert ipython style to markdown style.

    Examples:
        >>> _ipython_to_markdown([">>> print('hello')"])
        >>> # ```python\\nprint(\'hello\')\\n```
        >>> _ipython_to_markdown(["a", ">>> print('hello')", "b"])
        >>> # a\\n```python\\nprint(\'hello\')\\n```\\nb

    Args:
        lines: The lines to be converted.

    Returns:
        The converted lines.
    """
    out = []
    in_code = False
    for line in lines:
        if line.startswith(">>> "):
            if not in_code:
                out.append("")
                out.append("```python")
                in_code = True
            out.append(line[4:])
        else:
            if in_code:
                out.append("```")
                out.append("")
                in_code = False

            if line and line[-1] in (".", "?", ":", "!"):
                out.append(line + "<br />")
            else:
                out.append(line)

    if in_code:
        out.append("```")
        out.append("")
    return out


class ItemTerm(Mixin, Diot):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("diot_nest", False)
        super().__init__(*args, **kwargs)
        self._set_meta("raw_help", [])
        self._set_meta("prefix", None)

    def __str__(self) -> str:
        out = self._get_meta("prefix") or ""
        out += self.name
        if self.attrs._get_meta("origin"):
            out += f" ({self.attrs})"
        out += ":"

        raw_help = self._get_meta("raw_help")
        if raw_help:
            out += " " + raw_help[0]

        for line in raw_help[1:]:
            out += f"\n{FORMAT_INDENT}{line}"

        if self.terms:
            out += f"\n{self.terms}"

        return out

    def to_markdown(self, show_hidden: bool = False) -> str:
        out = self._get_meta("prefix") or "- "
        out += f"`{self.name}`"
        if self.attrs._get_meta("origin"):
            out += f" {self.attrs.to_markdown(show_hidden)}"
        out += ":"

        if (
            self.attrs.get("default", None) is not None
            and not self.attrs.get("ns", False)
        ):
            default = '""' if self.attrs.default == "" else self.attrs.default
            out += f" *Default: `{default}`*. <br />"

        raw_help = self._get_meta("raw_help")
        if raw_help and raw_help[0] == "|":
            raw_help = raw_help[1:]
        for line in _ipython_to_markdown(raw_help):
            out += f"\n{FORMAT_INDENT}{line}"

        if self.terms:
            out += f"\n{self.terms.to_markdown(show_hidden)}"

        return out


class ItemTerms(Mixin, OrderedDiot):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("diot_nest", False)
        super().__init__(*args, **kwargs)
        self._set_meta("name", None)
        self._set_meta("level", 0)

    def __str__(self) -> str:
        name = self._get_meta("name")
        level = self._get_meta("level")
        out = []
        if name:
            out.append(f"{FORMAT_INDENT * level}{name}:")

        for term in self.values():
            out.extend(
                (f"{FORMAT_INDENT * (level + 1)}{line}")
                for line in str(term).splitlines()
            )
        return "\n".join(out)

    def to_markdown(self, show_hidden: bool = False) -> str:
        level = self._get_meta("level")
        out = []
        # if name:
        #     out.append(f"{FORMAT_INDENT * level}{name}:")
        indent = "" if level == 0 else FORMAT_INDENT
        for term in self.values():
            if term.attrs.get("hidden", False) and not show_hidden:
                continue
            out.extend(
                (f"{indent}{line}")
                for line in term.to_markdown(show_hidden).splitlines()
            )
        return "\n".join(out)


class SummaryParsed(Mixin, Diot):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("diot_nest", False)
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.short}\n\n{self.long}"

    def to_markdown(self, show_hidden: bool = False) -> str:
        long = "\n".join(_ipython_to_markdown(self.long.splitlines()))
        return f"{self.short}\n\n{long}"


class TextLines(list):

    def __str__(self) -> str:  # pragma: no cover
        return "\n".join(self)

    # For jinja2/Liquid to work
    def splitlines(self):
        return cleanup_empty_lines(self)

    def to_markdown(
        self,
        show_hidden: bool = False,
    ) -> str:  # pragma: no cover
        out = _ipython_to_markdown(self)
        return "\n".join(out)


class TextParsed(Mixin, Diot):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("diot_nest", False)
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        name = self._get_meta("name")
        out = f"{name}:\n" if name else ""
        out += "\n".join(f"{FORMAT_INDENT}{line}" for line in self.lines)
        return out

    def to_markdown(self, show_hidden: bool = False) -> str:
        lines = _ipython_to_markdown(self.lines)
        return "\n".join(f"{FORMAT_INDENT}{line}" for line in lines)


def _parse_terms(
    lines: List[str],
    prefix: str | None = None,
    level: int = 0,
    name: str | None = None,
) -> ItemTerms:
    """Parse a list of lines as terms.
    """
    terms = ItemTerms()
    terms._set_meta("name", name)
    terms._set_meta("level", level)
    lines = dedent(lines)
    sublines = []
    item = None
    just_matched = False
    help_continuing = False
    for line in lines:
        if prefix:
            matched = ITEM_LINE_REGEX.match(line[len(prefix):])
        else:
            matched = ITEM_LINE_REGEX.match(line)

        lstripped_line = line.lstrip()
        if matched:
            if item:
                # See if we have sub-terms
                item.terms = _parse_terms(sublines, "- ", level + 1)
                sublines.clear()

            # Create a new item
            name = matched.group("name")
            attrs = matched.group("attrs")
            help = matched.group("help")
            terms[name] = ItemTerm(  # type: ignore[assignment]
                name=name,
                attrs=ItemAttrs(),
                terms=ItemTerms(),
                help="",
            )
            terms[name]._set_meta("prefix", prefix)  # type: ignore[assignment]

            if attrs:
                for attr in attrs.split(";"):
                    attr = attr.strip()
                    attr_matched = ITEM_ATTR_REGEX.match(attr)
                    if not attr_matched:
                        raise MalFormattedAnnotationError(
                            f"\nInvalid item attribute: {attr}"
                            "\nExpecting: <name>[:=]<value>"
                            f"\nFull attributes: {attrs}"
                        )
                    attr_name = attr_matched.group("name")
                    attr_value = attr_matched.group("value")
                    terms[name].attrs._get_meta(  # type: ignore[assignment]
                        "origin"
                    ).append(attr_name)
                    terms[name].attrs[attr_name] = (  # type: ignore[assignment]
                        True if attr_value is None else attr_value
                    )

            if help is not None:
                terms[name].help = help.strip()  # type: ignore[assignment]
                terms[name]._get_meta("raw_help").append(  # type: ignore[assignment]
                    terms[name].help  # type: ignore[assignment]
                )
                if terms[name].help == "|":  # type: ignore[assignment]
                    help_continuing = True

            item = terms[name]  # type: ignore[assignment]
            just_matched = True
        elif item is None:
            raise MalFormattedAnnotationError(
                f"\nInvalid item line: {line}"
                "\nExpecting: <name>[ (<attrs>)]: <help>"
            )
        elif just_matched and not lstripped_line.startswith("- "):
            if help_continuing and item.help == "|":
                sep = item.help = ""
            else:
                sep = (
                    "\n"
                    if help_continuing
                    or end_of_sentence(item.help)
                    or lstripped_line.startswith(">>>")
                    or (
                        item.help
                        and item.help.splitlines()[-1].startswith(">>>")
                    )
                    else " "
                )
            item._get_meta("raw_help").append(lstripped_line)
            item.help = f"{item.help}{sep}{lstripped_line}"
        elif lstripped_line.startswith("- "):
            sublines.append(line)
            just_matched = False
            help_continuing = False
        else:
            sublines.append(line)

    if item:
        # See if we have sub-terms
        item.terms = _parse_terms(sublines, prefix="- ", level=level + 1)

    return terms  # type: ignore[assignment]


def _parse_one_output(out: str) -> List[str] | None:
    """Parse one output item, such as `out:file:<outfile>`"""
    parts = out.split(":")
    if not parts[0].isidentifier():
        return None
    if len(parts) < 3:
        return [parts[0], ProcInputType.VAR, parts[1]]
    return parts


def _update_attrs_with_cls(
    parsed: Diot,
    envs: dict | None,
    prev_key: str | None = None,
) -> None:
    """Update the attrs of parsed terms with the class envs."""
    envs = envs or {}
    for key, value in envs.items():
        whole_key = f"{prev_key}.{key}" if prev_key else key

        if key not in parsed:
            parsed[key] = ItemTerm(
                name=key,
                attrs=ItemAttrs(),
                terms=ItemTerms(),
                help="",
            )

        if (
            parsed[key].attrs.get("ns", False)
            or parsed[key].attrs.get("namespace", False)
            or parsed[key].attrs.get("action", "") in ("ns", "namespace")
            or (isinstance(value, dict) and parsed[key].terms)
        ):
            parsed[key].attrs.setdefault("ns", True)
            _update_attrs_with_cls(
                parsed[key].terms,
                value,
                prev_key=whole_key,
            )
            # continue

        if "default" not in parsed[key].attrs:
            parsed[key].attrs["default"] = value


def _update_terms(base: Mapping, other: Mapping) -> Mapping:
    """Update the terms of base with the other terms."""
    base = deepcopy(base)
    for key, value in other.items():
        if key not in base:
            base[key] = value  # type: ignore[assignment]
        else:
            if value.help:
                base[key].help = value.help
                base[key]._set_meta(
                    "raw_help",
                    value._get_meta("raw_help").copy()
                )
            base[key].attrs.update(value.attrs)
            origin = base[key].attrs._get_meta("origin")
            for org in value.attrs._get_meta("origin"):
                if org not in origin:
                    origin.append(org)
            _update_terms(base[key].terms, value.terms)

    return base


class Section(ABC):

    def __init__(self, cls, name) -> None:
        self.name = name
        self._cls = cls
        self._lines: List[str] = []

    def consume(self, line: str) -> None:
        self._lines.append(line)

    @abstractmethod
    def parse(self) -> Diot:  # pragma: no cover
        pass

    @classmethod
    def update_parsed(
        cls,
        base: str | List[str] | MutableMapping,
        other: str | List[str] | MutableMapping,
    ) -> str | List[str] | MutableMapping:
        """Update the parsed result with the other result."""
        if isinstance(other, str):  # pragma: no cover
            return other
        if isinstance(other, list):
            return base + other  # type: ignore[operator]

        base = deepcopy(base)
        base.update(other)  # type: ignore[union-attr]
        return base


class SectionSummary(Mixin, Section):

    def parse(self) -> Diot:
        """Parse the summary section."""
        lines = self._lines
        if lines:
            if lines[0] and lines[0][0] in (" ", "\t"):
                lines = dedent(self._lines)
            else:
                lines = [lines[0]] + dedent(lines[1:])

        short = long = ""
        for i, line in enumerate(lines):
            if not line:
                long = "\n".join(lines[i + 1:])
                break
            short += line + " "

        return SummaryParsed(short=short.rstrip(), long=long)

    @classmethod
    def update_parsed(
        cls,
        base: str | List[str] | MutableMapping,
        other: str | List[str] | MutableMapping,
    ) -> str | List[str] | MutableMapping:
        """Update the parsed result with the other result."""
        base = deepcopy(base)
        if other.short:  # type: ignore[assignment]
            base.short = other.short  # type: ignore[assignment]
        if other.long:  # type: ignore[assignment]
            base.long = other.long  # type: ignore[assignment]
        return base


class SectionItems(Mixin, Section):

    def parse(self) -> Diot:
        try:
            return _parse_terms(self._lines, name=self.name)
        except MalFormattedAnnotationError as e:
            raise MalFormattedAnnotationError(
                f"[{self._cls.__name__}/{self.name}] {e}"
            ) from None

    @classmethod
    def update_parsed(
        cls,
        base: str | List[str] | MutableMapping,
        other: str | List[str] | MutableMapping,
    ) -> str | List[str] | MutableMapping:
        """Update the parsed result with the other result."""
        return _update_terms(base, other)  # type: ignore[return-value]


class SectionInput(SectionItems):

    def parse(self) -> Diot:
        parsed = super().parse()
        input_keys = self._cls.input

        if isinstance(input_keys, str):
            input_keys = [
                input_key.strip() for input_key in input_keys.split(",")
            ]

        input_key_names = set()
        for input_key_type in input_keys or []:
            if ":" not in input_key_type:
                input_key_type = f"{input_key_type}:{ProcInputType.VAR}"

            input_key, input_type = input_key_type.split(":", 1)
            input_key_names.add(input_key)
            if input_key not in parsed:
                parsed[input_key] = ItemTerm(
                    name=input_key,
                    attrs=ItemAttrs(itype=input_type),
                    terms=ItemTerms(),
                    help="",
                )
            else:
                parsed[input_key].attrs["itype"] = input_type

            parsed[input_key].attrs["nargs"] = "+"
            if input_type in (ProcInputType.FILES, ProcInputType.DIRS):
                parsed[input_key].attrs["action"] = "append"
            else:
                parsed[input_key].attrs["action"] = "extend"

        if set(parsed) - input_key_names:
            warnings.warn(
                f"[{self._cls.__name__}] Unknown input keys "
                f"{set(parsed) - input_key_names}",
                UnknownAnnotationItemWarning,
            )

        return parsed


class SectionOutput(SectionItems):

    def parse(self) -> Diot:
        output = self._cls.output
        if not output:
            out = ItemTerms()
            out._set_meta("name", self.name)
            return out

        parsed = super().parse()
        if isinstance(output, str):
            # Strip all paired '{{'/'}}', '{#'/'#'}', '{%'/'%}' in the output string,
            # which are used for jinja2/Liquid template syntax
            output = output.strip()
            if output.startswith("{"):
                # It is an entire template string, we can't infer the values
                output = [
                    out.strip()
                    for out in strip_template_syntax(output).split(",")
                    if out.strip()
                ]
            else:
                # Replace the template blocks in the output string with <template#id>
                # then split by comma to get the output items
                # after that we get the values of the template blocks
                # from the original output string by the id
                output, blocks = replace_template_blocks(output.strip())
                output = [out.strip() for out in output.split(",") if out.strip()]
                for j, out in enumerate(output):
                    for key, value in blocks.items():
                        if key in out:
                            output[j] = out = out.replace(key, value.strip())

        elif isinstance(output, (list, tuple)):
            output = [out.strip() for out in output]
        elif isinstance(output, dict):
            output = [f"{key}:{value}" for key, value in output.items()]
        else:
            raise ProcOutputTypeError(
                f"[{self._cls.__name__}] Invalid output type: {type(output).__name__}"
                "\nExpecting a string or a list of strings."
            )

        out_names = set()
        for out in output:
            parts = _parse_one_output(out)
            if not parts:
                continue

            out_names.add(parts[0])
            if parts[0] not in parsed:
                parsed[parts[0]] = ItemTerm(
                    name=parts[0],
                    attrs=ItemAttrs(otype=parts[1], default=parts[2] or "<templated>"),
                    terms=ItemTerms(),
                    help="",
                )
            else:
                parsed[parts[0]].attrs["otype"] = parts[1]
                parsed[parts[0]].attrs["default"] = parts[2] or "<templated>"

        if set(parsed) - out_names:
            warnings.warn(
                f"[{self._cls.__name__}] Unknown output keys "
                f"{set(parsed) - out_names}",
                UnknownAnnotationItemWarning,
            )

        return parsed


class SectionEnvs(SectionItems):

    def parse(self) -> Diot:
        parsed = super().parse()
        _update_attrs_with_cls(parsed, self._cls.envs)
        return parsed


class SectionProcGroupArgs(SectionItems):

    def parse(self) -> Diot:
        parsed = super().parse()
        _update_attrs_with_cls(parsed, self._cls.DEFAULTS)
        return parsed


class SectionText(Section):

    def parse(self) -> Diot:
        lines = dedent(self._lines)
        lines = cleanup_empty_lines(lines)
        out = TextParsed(lines=TextLines(lines))
        out._set_meta("name", self.name)
        return out
