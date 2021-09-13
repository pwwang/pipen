"""An example showing how to use mako template engine"""

from mako.template import Template as Mako
from pipen.template import Template
from pipen import Proc, Pipen

class TemplateMako(Template):

    name = "mako"

    def __init__(self, source, **kwargs):
        super().__init__(source)
        self.engine = Mako(source, **kwargs)

    def _render(self, data):
        return self.engine.render(**data)


class MakoProcess(Proc):
    """A process using mako templating"""
    template = TemplateMako
    input = "a"
    input_data = [1]
    output = "outfile:file:${in_['a']}.txt"
    script = "touch ${out['outfile']}"

Pipen().run(MakoProcess)
