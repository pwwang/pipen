"""Template adaptor for pipen"""
from abc import ABC, abstractmethod
from typing import Any, Mapping, Type, Union
from liquid import Liquid

from .utils import load_entrypoints, is_subclass
from .defaults import TEMPLATE_ENTRY_GROUP
from .exceptions import NoSuchTemplateEngineError, WrongTemplateEnginTypeError

__all__ = ["Template", "TemplateLiquid", "TemplateJinja2", "get_template_engine"]


class Template(ABC):
    """Base class wrapper to wrap template for pipen"""

    def __init__(  # pylint: disable=unused-argument
        self,
        source: Any,
        envs: Mapping[str, Any] = None,
        **kwargs: Any,
    ):
        """Template construct"""
        self.envs = envs or {}
        self.engine = None

    def update_envs(self, envs):
        """@API
        Register extra environment
        @params:
            envs: The environment
        """
        self.envs.update(envs)

    def render(self, data: Mapping[str, Any] = None) -> str:
        """@API
        Render the template
        @parmas:
            data (dict): The data used to render
        """
        return self._render(data or {})

    @abstractmethod
    def _render(self, data: Mapping[str, Any]) -> str:
        """Implement rendering"""


class TemplateLiquid(Template):
    """Liquidpy template wrapper."""

    name = "liquid"

    def __init__(
        self,
        source: Any,
        envs: Mapping[str, Any] = None,
        **kwargs: Any,
    ):
        """Initiate the engine with source and envs

        Args:
            source: The souce text
            envs: The env data
            **kwargs: Other arguments for Liquid
        """
        super().__init__(source, envs)
        self.engine = Liquid(
            source, from_file=False, mode="wild", globals=envs, **kwargs
        )

    def _render(self, data: Mapping[str, Any]) -> str:
        """Render the template

        Args:
            data: The data used for rendering

        Returns
            The rendered string
        """
        return self.engine.render(data)


class TemplateJinja2(Template):
    """Jinja2 template wrapper"""

    name = "jinja2"

    def __init__(
        self,
        source: Any,
        envs: Mapping[str, Any] = None,
        **kwargs: Any,
    ):
        """Initiate the engine with source and envs

        Args:
            source: The souce text
            envs: The env data
            **kwargs: Other arguments for jinja2.Template
        """
        import jinja2

        super().__init__(source, envs)
        filters = kwargs.pop("filters", {})
        self.engine = jinja2.Template(source, **kwargs)
        self.engine.globals.update(self.envs)
        self.engine.environment.filters.update(filters)

    def _render(self, data: Mapping[str, Any]) -> str:
        """Render the template

        Args:
            data: The data used for rendering

        Retuens:
            The rendered string
        """
        return self.engine.render(data)


def get_template_engine(template: Union[str, Type[Template]]) -> Type[Template]:
    """Get the template engine by name or the template engine itself

    Args:
        template: The name of the template engine or the template engine itself

    Returns:
        The template engine
    """
    if is_subclass(template, Template):
        return template

    if template == "liquid":
        return TemplateLiquid

    if template == "jinja2":
        return TemplateJinja2

    for name, obj in load_entrypoints(TEMPLATE_ENTRY_GROUP):  # pragma: no cover
        if name == template:
            if not is_subclass(obj, Template):
                raise WrongTemplateEnginTypeError(
                    "Template engine should be a subclass of "
                    "pipen.templates.Template."
                )
            return obj

    raise NoSuchTemplateEngineError(str(template))
