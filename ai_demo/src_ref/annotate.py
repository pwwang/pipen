from __future__ import annotations

import textwrap
from abc import ABC
from typing import Any, Callable, Mapping, Type, MutableMapping

from diot import OrderedDiot
from liquid import Liquid
from pipen import Proc, ProcGroup
from pipen.utils import mark, get_marked

from .utils import indent as indent_text, FORMAT_INDENT, is_section
from .sections import (
    Section,
    SectionSummary,
    SectionInput,
    SectionOutput,
    SectionEnvs,
    SectionItems,
    SectionProcGroupArgs,
    SectionText,
)

SECTION_TYPES: MutableMapping[str, Type[Section]] = {
    "Summary": SectionSummary,
    "Input": SectionInput,
    "Output": SectionOutput,
    "Envs": SectionEnvs,
    "Args": SectionItems,
    "Returns": SectionItems,
    "Raises": SectionItems,
    "Warns": SectionItems,
    "See Also": SectionText,
    "Notes": SectionText,
    "References": SectionText,
    "Examples": SectionText,
    "Todo": SectionText,
    "Text": SectionText,
    "Items": SectionItems,
}


def _annotate_uninherited(cls: type) -> OrderedDiot:
    """Annotate a Proc class with docstring, without inheriting from base.

    Args:
        cls: The class to be annotated.

    Returns:
        The annotated dict.
    """
    annotated = OrderedDiot(diot_nest=False)
    docstring = cls.__doc__

    if docstring:
        if docstring[0] in (" ", "\t"):
            docstring = textwrap.dedent(docstring)
        else:
            parts = docstring.split("\n", 1)
            if len(parts) == 1:
                first, rest = parts[0], ""
            else:
                first, rest = parts
            docstring = f"{first}\n{textwrap.dedent(rest)}"

        section_name = "Summary"
        section = SectionSummary(cls, section_name)
        for line in docstring.splitlines():
            line = line.rstrip()
            if line and line[-1] == ":":
                if line[:-1] in SECTION_TYPES:
                    annotated[section_name] = section.parse()
                    section_name = line[:-1]
                    if section_name == "Args" and issubclass(cls, ProcGroup):
                        section = SectionProcGroupArgs(cls, section_name)
                    else:
                        section = SECTION_TYPES[section_name](
                            cls,
                            section_name,
                        )
                elif is_section(line[:-1]):
                    annotated[section_name] = section.parse()
                    section_name = line[:-1]
                    section = SectionText(cls, section_name)
                else:
                    section.consume(line)
            else:
                section.consume(line)

        annotated[section_name] = section.parse()

    if issubclass(cls, Proc):
        if "Summary" not in annotated:
            annotated.Summary = SectionSummary(cls, "Summary").parse()
        if "Input" not in annotated:
            annotated.Input = SectionInput(cls, "Input").parse()
        if "Output" not in annotated:
            annotated.Output = SectionOutput(cls, "Output").parse()
        if "Envs" not in annotated:
            annotated.Envs = SectionEnvs(cls, "Envs").parse()

    if issubclass(cls, ProcGroup):
        if "Args" not in annotated:
            annotated.Args = SectionProcGroupArgs(cls, "Args").parse()

    return annotated  # type: ignore[return-value]


def _update_annotation(
    base: OrderedDiot | None,  # type: ignore[annotation-unchecked]
    other: OrderedDiot,
) -> OrderedDiot:
    """Update the annotation with another annotation."""
    if base is None:
        return other

    base: OrderedDiot = other.__class__(  # type: ignore[assignment]
        base,
        diot_nest=False,
    )

    for key, value in other.items():
        section_class = SECTION_TYPES.get(key)
        if key not in base or section_class is None:
            base[key] = value
        else:
            base[key] = section_class.update_parsed(base[key], value)

    return base


def annotate(cls: Type[Any]) -> OrderedDiot:
    """Annotate a Proc class with docstring.

    Args:
        cls: The class to be annotated.

    Returns:
        The annotated dict.
    """
    annotated = get_marked(cls, "annotate_annotated")
    inherit = get_marked(cls, "annotate_inherit", True)
    is_proc_or_pg = issubclass(cls, Proc) or issubclass(cls, ProcGroup)

    if not annotated or not is_proc_or_pg:
        annotated = _annotate_uninherited(cls)
        base = [
            mro
            for mro in cls.__mro__
            if (
                mro is not cls
                and mro is not object
                and mro is not Proc
                and mro is not ProcGroup
                and mro is not ABC
            )
        ]

        base = base[0] if base else None
        annotated_base = annotate(base) if inherit and base else None
        annotated = _update_annotation(annotated_base, annotated)
        mark(annotate_annotated=annotated)(cls)

    return annotated


def _register_section(
    section: str,
    section_class: Type[Section] | str | None = None,
) -> Callable[[Type[Section]], Type[Section]] | Type[Section]:
    """Register a section to be parsed.

    Args:
        section: The section name.
        section_class: The section class or a shortcut string to
            builtin section class.
            summary: SectionSummary
            input: SectionInput
            output: SectionOutput
            envs: SectionEnvs
            items: SectionItems
            text: SectionText
    """
    # When used as a decorator
    if section_class is None:
        return lambda cls: _register_section(section, cls)  # type: ignore[return-value]

    if isinstance(section_class, str):
        section_class = section_class.title()
        if section_class not in SECTION_TYPES:
            raise ValueError(
                f"Invalid section class shortcut: {section_class}\n"
                f"Valid shortcuts: {', '.join(SECTION_TYPES)}",
            ) from None
        section_class = SECTION_TYPES[section_class]

    SECTION_TYPES[section] = section_class
    return section_class


def _unregister_section(section: str) -> None:
    """Unregister a section.

    Args:
        section: The section name.
    """
    SECTION_TYPES.pop(section, None)


def _format_doc(
    cls: type | None = None,
    /,
    *,
    base: type | None = None,
    indent: int | str = 1,
    vars: Mapping[str, Any] | None = None,
) -> type | Callable[[type], type]:
    """Inherit docstring from base class.

    Args:
        cls: The class to be inherited.
        base: The base class to inherit from.
            if None, inherit from the first base class that is not object,
            Proc, or ProcGroup.
        indent: The indent level of the docstring.
            Either an integer, indicating the number of `FORMAT_INDENT`
            (4 spaces by default) to indent, or a string, indicating the string
            to indent.
        vars: The extra variables to be rendered in the docstring.

    Returns:
        When cls is None, return a decorator.
        When cls is not None, return the class with docstring inherited.
    """
    if cls is None:
        return lambda c: _format_doc(  # type: ignore[return-value]
            c,
            base=base,
            indent=indent,
            vars=vars,
        )

    if base is None:
        base = [  # type: ignore[assignment]
            mro
            for mro in cls.__mro__
            if mro is not cls
            and mro is not object
            and mro is not Proc
            and mro is not ProcGroup
        ]

        base = base[0] if base else None  # type: ignore[assignment]

    if base is None:
        return cls

    if isinstance(indent, int):
        indent = FORMAT_INDENT * indent

    docstr = cls.__doc__
    if docstr is None or not docstr.strip():
        if not base.__doc__ or not base.__doc__.strip():
            return cls

        # If the class has no docstring, inherit from base class
        cls.__doc__ = indent_text(base.__doc__, indent)
        return cls

    base_annotated = annotate(base)
    vars = vars or {}
    docstr = Liquid(docstr, from_file=False).render(**base_annotated, **vars)
    cls.__doc__ = indent_text(docstr, indent)

    return cls


annotate.register_section = _register_section  # type: ignore[attr-defined]
annotate.unregister_section = _unregister_section  # type: ignore[attr-defined]
annotate.format_doc = _format_doc  # type: ignore[attr-defined]
