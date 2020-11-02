"""Template adaptor for pipen"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union
from liquid import Liquid

__all__ = ['Template', 'TemplateLiquid', 'TemplateJinja2']

class Template(ABC):
    """@API
    Base class wrapper to wrap template for PyPPL
    """
    def __init__(self, source: Any, **envs):
        """@API
        Template construct
        """
        self.envs = envs

    def update_envs(self, **envs):
        """@API
        Register extra environment
        @params:
            **envs: The environment
        """
        self.envs.update(envs)

    def render(self, data: Optional[Dict[str, Any]] = None) -> str:
        """@API
        Render the template
        @parmas:
            data (dict): The data used to render
        """
        return self._render(data or {})

    @abstractmethod
    def _render(self, data: Dict[str, Any]) -> str:
        """Implement rendering"""


class TemplateLiquid(Template):
    """Liquidpy template wrapper."""
    name = 'liquid'

    def __init__(self, source: Any, **envs):
        """Initiate the engine with source and envs

        Args:
            source: The souce text
            envs: The env data
        """
        super().__init__(source, **envs)
        self.engine = Liquid(
            source,
            liquid_config={'strict': False, 'mode': 'python'},
            **self.envs
        )

    def _render(self, data: Dict[str, Any]) -> str:
        """Render the template

        Args:
            data: The data used for rendering

        Returns
            The rendered string
        """
        return self.engine.render(**data)


class TemplateJinja2(Template):
    """Jinja2 template wrapper"""
    name = 'jinja2'

    def __init__(self, source: Any, **envs):
        """Initiate the engine with source and envs

        Args:
            source: The souce text
            envs: The env data
        """
        import jinja2
        super().__init__(source, **envs)
        self.engine = jinja2.Template(source)
        self.engine.globals = self.envs

    def _render(self, data: Dict[str, Any]) -> str:
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
    if template == 'liquid':
        return TemplateLiquid

    if template == 'jinja2':
        return TemplateJinja2

    # // TODO: otherwise load from entrypoints ?
    return template