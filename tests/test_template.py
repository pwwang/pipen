import pytest

from pipen.template import *
from pipen.template import NoSuchTemplateEngineError

def test_update_envs():
    jinja = get_template_engine('jinja2')
    jinja2 = get_template_engine(jinja)
    assert jinja is jinja2
    jinja_tpl = jinja('abc')
    jinja_tpl.update_envs(dict(a=1))
    assert jinja_tpl.envs['a'] == 1
    assert jinja_tpl.render() == 'abc'

    with pytest.raises(NoSuchTemplateEngineError):
        get_template_engine('nosuchtemplate')
