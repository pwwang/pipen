"""Schema introspection for Proc and ProcGroup classes."""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class FieldDef:
    name: str        # Python identifier used as parameter name
    cli_arg: str     # CLI flag, e.g. "--in.infile", "--GroupName.input"
    type_: Any       # Python type annotation
    default: Any     # inspect.Parameter.empty means required
    description: str


_STANDARD_FIELDS: list[FieldDef] = [
    FieldDef("outdir", "--outdir", str, None,
             "Output directory of the pipeline"),
    FieldDef("forks", "--forks", int, None,
             "Number of jobs to run simultaneously"),
    FieldDef("scheduler", "--scheduler", str, None,
             "Scheduler to run the jobs"),
    FieldDef("profile", "--profile", str, None,
             "Configuration profile to use"),
    FieldDef("cache", "--cache", str, None,
             "Cache strategy: true/false/force"),
]


def _parse_input_channels(input_spec: str | list | None) -> list[tuple[str, str]]:
    """Parse proc.input into (channel_name, channel_type) pairs."""
    if not input_spec:
        return []
    if isinstance(input_spec, (list, tuple)):
        spec_str = ",".join(input_spec)
    else:
        spec_str = str(input_spec)
    channels = []
    for part in spec_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, ch_type = part.split(":", 1)
        else:
            name, ch_type = part, "var"
        channels.append((name.strip(), ch_type.strip()))
    return channels


_SAFE_TYPES = (int, float, bool, str, list, dict)


def _normalize_default(default: Any) -> Any:
    """Coerce non-JSON-serializable defaults to a plain Python equivalent."""
    if default is inspect.Parameter.empty or default is None:
        return default
    if isinstance(default, dict):
        return dict(default)
    if isinstance(default, list):
        return list(default)
    if isinstance(default, (int, float, bool, str)):
        return default
    # Anything else (custom objects, etc.) — drop the default
    return None


def _anno_type_to_python(attrs: dict, default: Any) -> Any:
    """Derive a Python type from pipen_annotate attrs and a default value."""
    type_map = {"int": int, "float": float, "bool": bool, "str": str}
    raw_type = attrs.get("type")
    if raw_type:
        py_type = type_map.get(str(raw_type), str)
    elif default is not inspect.Parameter.empty and default is not None:
        raw = type(default)
        if raw in _SAFE_TYPES:
            py_type = raw
        elif isinstance(default, dict):
            py_type = dict
        elif isinstance(default, list):
            py_type = list
        else:
            py_type = str
    else:
        py_type = str

    if attrs.get("array") or attrs.get("list") or isinstance(default, list):
        return list[str]
    return py_type


def get_proc_schema(proc_cls: type) -> list[FieldDef]:
    """Return FieldDefs for an eligible Proc class."""
    try:
        from pipen_annotate import annotate
        anno = annotate(proc_cls)
        input_anno = getattr(anno, "Input", {})
        envs_anno = getattr(anno, "Envs", {})
    except Exception:
        input_anno = {}
        envs_anno = {}

    fields: list[FieldDef] = []

    # Input channels — one parameter per channel, all required
    for ch_name, ch_type in _parse_input_channels(proc_cls.input):
        help_text = ""
        if ch_name in input_anno:
            help_text = getattr(input_anno[ch_name], "help", "") or ""
        if not help_text:
            help_text = f"Input channel '{ch_name}' (type: {ch_type})"
        field_name = re.sub(r"[^a-zA-Z0-9_]", "_", f"in_{ch_name}")
        fields.append(FieldDef(
            name=field_name,
            cli_arg=f"--in.{ch_name}",
            type_=str,
            default=inspect.Parameter.empty,
            description=help_text,
        ))

    # Documented envs only (avoids polluting the schema)
    for env_name, env_val in envs_anno.items():
        env_default = _normalize_default((proc_cls.envs or {}).get(env_name))
        help_text = getattr(env_val, "help", "") or f"Env var: {env_name}"
        attrs = getattr(env_val, "attrs", {})
        py_type = _anno_type_to_python(attrs, env_default)
        field_name = re.sub(r"[^a-zA-Z0-9_]", "_", f"envs_{env_name}")
        fields.append(FieldDef(
            name=field_name,
            cli_arg=f"--envs.{env_name}",
            type_=py_type,
            default=env_default,
            description=help_text,
        ))

    fields.extend(_STANDARD_FIELDS)
    return fields


def get_group_schema(group_cls: type) -> list[FieldDef]:
    """Return FieldDefs for an eligible ProcGroup class."""
    group_name = getattr(group_cls, "name", None) or group_cls.__name__
    defaults = getattr(group_cls, "DEFAULTS", None) or {}

    try:
        from pipen_annotate import annotate
        anno = annotate(group_cls)
        args_anno = getattr(anno, "Args", {})
    except Exception:
        args_anno = {}

    fields: list[FieldDef] = []

    for key, val in args_anno.items():
        help_text = getattr(val, "help", "") or ""
        attrs = getattr(val, "attrs", {})
        default = _normalize_default(defaults.get(key, inspect.Parameter.empty))
        py_type = _anno_type_to_python(attrs, default)
        field_name = re.sub(r"[^a-zA-Z0-9_]", "_", key)
        fields.append(FieldDef(
            name=field_name,
            cli_arg=f"--{group_name}.{key}",
            type_=py_type,
            default=default,
            description=help_text,
        ))

    fields.extend(_STANDARD_FIELDS)
    return fields


# ---------------------------------------------------------------------------
# Progressive-disclosure helpers
# ---------------------------------------------------------------------------

def _type_label(t: Any) -> str:
    """Return a short human-readable type label."""
    if hasattr(t, "__name__"):
        return t.__name__
    # e.g. list[str]
    return str(t).replace("typing.", "")


def get_eligible_items(nsmod: Any) -> list[tuple[str, type, str]]:
    """Return (proc_name, cls, kind) for all eligible Proc/ProcGroup in *nsmod*.

    *proc_name* is the name used when calling ``pipen run ns proc_name``:
    - For Proc: ``cls.name``
    - For ProcGroup: the attribute name in the module
    *kind* is ``"proc"`` or ``"group"``.
    """
    from pipen import Proc, ProcGroup
    from pipen_args import ProcGroup as ArgsProcGroup

    items: list[tuple[str, type, str]] = []
    for attrname in dir(nsmod):
        try:
            attrval = getattr(nsmod, attrname)
        except Exception:
            continue
        if not isinstance(attrval, type):
            continue
        if (
            issubclass(attrval, ProcGroup)
            and attrval is not ProcGroup
            and attrval is not ArgsProcGroup
        ):
            items.append((attrname, attrval, "group"))
        elif issubclass(attrval, Proc) and getattr(attrval, "input", None):
            items.append((getattr(attrval, "name", attrname), attrval, "proc"))
    return items


def format_process_listing(ns: str, nsmod: Any) -> str:
    """Return a human-readable listing of all eligible processes in a namespace."""
    from pipen_cli_run.entry import get_short_summary

    items = get_eligible_items(nsmod)
    if not items:
        return f"No eligible processes found in namespace '{ns}'."

    ns_desc = (
        get_short_summary(getattr(nsmod, "__doc__", None)) or f"Namespace {ns}"
    )
    lines = [
        f"Namespace: {ns}",
        f"Description: {ns_desc}",
        "",
        "Available processes:",
    ]
    for name, cls, kind in items:
        desc = get_short_summary(cls.__doc__) or "No description"
        lines.append(f"  {name} ({kind}): {desc}")
    lines += [
        "",
        f"Use get_process('{ns}', '<process_name>') to see detailed arguments.",
    ]
    return "\n".join(lines)


def format_process_detail(ns: str, name: str, cls: type) -> str:
    """Return a human-readable argument schema for a Proc or ProcGroup class."""
    from pipen import Proc
    from pipen_cli_run.entry import get_short_summary

    if issubclass(cls, Proc):
        fields = get_proc_schema(cls)
    else:
        fields = get_group_schema(cls)

    desc = get_short_summary(cls.__doc__) or "No description"
    lines = [
        f"Process: {name}  (namespace: {ns})",
        f"Description: {desc}",
        "",
        "Arguments:",
    ]

    required = [f for f in fields if f.default is inspect.Parameter.empty]
    optional = [f for f in fields if f.default is not inspect.Parameter.empty]

    if required:
        lines.append("  Required:")
        for f in required:
            lines.append(
                f"    {f.cli_arg} <{_type_label(f.type_)}>  {f.description}"
            )

    if optional:
        lines.append("  Optional:")
        for f in optional:
            default_str = "" if f.default is None else f" (default: {f.default!r})"
            lines.append(
                f"    {f.cli_arg} <{_type_label(f.type_)}>{default_str}"
                f"  {f.description}"
            )

    # Build a minimal example using only the first required arg (if any)
    lines.append("")
    lines.append("Example:")
    example_parts = []
    for f in required[:1]:
        example_parts += [f'"{f.cli_arg}"', '"<value>"']
    args_repr = "[" + ", ".join(example_parts) + "]" if example_parts else "[]"
    lines.append(f'  run_process("{ns}", "{name}", {args_repr})')

    return "\n".join(lines)
