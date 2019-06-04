import pytest
import colorama
from pyppl.parameters2 import HelpAssembler, MAX_PAGE_WIDTH, MAX_OPT_WIDTH, \
	Parameter, Parameters, params
from pyppl.exceptions import ParameterNameError, ParameterTypeError, \
	ParametersParseError, ParametersLoadError

pytest_plugins = ["tests.fixt_parameters"]

class TestHelpAssembler:

	@classmethod
	def setup_class(cls):
		import sys
		sys.argv = ['program']
		cls.assembler = HelpAssembler()

	def test_init(self):
		assert self.assembler.progname == 'program'
		assert self.assembler.theme['error'] == colorama.Fore.RED

	@pytest.mark.parametrize('msg, with_prefix, expt', [
		('', True, '{f.RED}Error: {s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('', False, '{f.RED}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('{prog}', False, '{f.RED}{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('1{prog}2', True, '{f.RED}Error: 1{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}2{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
	])
	def test_error(self, msg, with_prefix, expt):
		assert self.assembler.error(msg, with_prefix) == expt

	@pytest.mark.parametrize('msg, with_prefix, expt', [
		('', True, '{f.YELLOW}Warning: {s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('', False, '{f.YELLOW}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('{prog}', False, '{f.YELLOW}{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('1{prog}2', True, '{f.YELLOW}Warning: 1{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}2{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
	])
	def test_warning(self, msg, with_prefix, expt):
		assert self.assembler.warning(msg, with_prefix) == expt

	@pytest.mark.parametrize('title, with_colon, expt', [
		('', True, '{s.BRIGHT}{f.CYAN}{s.RESET_ALL}:'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('title', False, '{s.BRIGHT}{f.CYAN}TITLE{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('title', True, '{s.BRIGHT}{f.CYAN}TITLE{s.RESET_ALL}:'.format(
			f = colorama.Fore,
			s = colorama.Style)),
	])
	def test_title(self, title, with_colon, expt):
		assert self.assembler.title(title, with_colon) == expt

	@pytest.mark.parametrize('prog, expt', [
		(None, '{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('another', '{s.BRIGHT}{f.GREEN}another{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
	])
	def test_prog(self, prog, expt):
		assert self.assembler.prog(prog) == expt

	@pytest.mark.parametrize('msg, expt', [
		('', ''),
		('a', 'a'),
		('a{prog}', 'a{s.BRIGHT}{f.GREEN}program{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style
		)),
	])
	def test_plain(self, msg, expt):
		assert self.assembler.plain(msg) == expt

	@pytest.mark.parametrize('msg, prefix, expt', [
		('optname', '', '{s.BRIGHT}{f.GREEN}optname{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('optname', '  ', '{s.BRIGHT}{f.GREEN}  optname{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
	])
	def test_optname(self, msg, prefix, expt):
		assert self.assembler.optname(msg, prefix) == expt

	@pytest.mark.parametrize('msg, expt', [
		('opttype', '{f.BLUE}<OPTTYPE>{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('opttype   ', '{f.BLUE}<OPTTYPE>{s.RESET_ALL}   '.format(
			f = colorama.Fore,
			s = colorama.Style)),
		('', '')
	])
	def test_opttype(self, msg, expt):
		assert self.assembler.opttype(msg) == expt

	@pytest.mark.parametrize('msg, first, expt', [
		('', False, '  {s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style
		)),
		('DEfault: 1', True, '- DEfault: 1{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style
		)),
		('Default: 1', False, '  {f.MAGENTA}Default: 1{s.RESET_ALL}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style
		)),
		('XDEFAULT: 1', True, '- X{f.MAGENTA}DEFAULT: 1{s.RESET_ALL}{s.RESET_ALL}'.format(
			f = colorama.Fore,
			s = colorama.Style
		)),
	])
	def test_optdesc(self, msg, first, expt):
		assert self.assembler.optdesc(msg, first) == expt

	@pytest.mark.parametrize('helps, expt', [
		({}, ['']),
		({'description': ['some description about the program']}, [
			'{s.BRIGHT}{f.CYAN}DESCRIPTION{s.RESET_ALL}:'.format(
				f = colorama.Fore, s = colorama.Style),
			'  some description about the program',
			'']),
		({'description': ['some very very very very very very very very very very very very '
			'very very very very description about the program']}, [
			'{s.BRIGHT}{f.CYAN}DESCRIPTION{s.RESET_ALL}:'.format(
				f = colorama.Fore, s = colorama.Style),
			'  some very very very very very very very very very very very very very very '
			'very very description',
			'  about the program',
			'']),
		({'options': [('-nthreads', 'int', ['Number of threads to use. Default: 1'])]}, [
			'{s.BRIGHT}{f.CYAN}OPTIONS{s.RESET_ALL}:'.format(
				f = colorama.Fore, s = colorama.Style),
			'{s.BRIGHT}{f.GREEN}  -nthreads{s.RESET_ALL} '
			'{f.BLUE}<INT>{s.RESET_ALL}     - Number of threads to use. '
			'{f.MAGENTA}Default: 1{s.RESET_ALL}{s.RESET_ALL}'.format(
				f = colorama.Fore, s = colorama.Style),
			'']),
		({'options': [
			('-nthreads', 'int', ['Number of threads to use. Default: 1']),
			('-opt1', 'str', ['String options.', 'DEFAULT: "Hello world!"']),
			('-option, --very-very-long-option-name', 'int', [
				'Option descript without default value. And this is a long long long '
				'long description'])]}, [
			'{s.BRIGHT}{f.CYAN}OPTIONS{s.RESET_ALL}:'.format(
				f = colorama.Fore, s = colorama.Style),
			'{s.BRIGHT}{f.GREEN}  -nthreads{s.RESET_ALL} '
			'{f.BLUE}<INT>{s.RESET_ALL}     - Number of threads to use. '
			'{f.MAGENTA}Default: 1{s.RESET_ALL}{s.RESET_ALL}'.format(
				f = colorama.Fore, s = colorama.Style),
			'{s.BRIGHT}{f.GREEN}  -opt1{s.RESET_ALL} {f.BLUE}<STR>{s.RESET_ALL}'
			'         - String options.{s.RESET_ALL}'.format(f = colorama.Fore, s = colorama.Style),
			'                        {f.MAGENTA}DEFAULT: "Hello world!"{s.RESET_ALL}{s.RESET_ALL}'.format(
				f = colorama.Fore, s = colorama.Style),
			'{s.BRIGHT}{f.GREEN}  -option, --very-very-long-option-name{s.RESET_ALL} '
			'{f.BLUE}<INT>{s.RESET_ALL}'.format(f = colorama.Fore, s = colorama.Style),
			'                      - Option descript without default value. '
			'And this is a long long long long{s.RESET_ALL}'.format(
				f = colorama.Fore, s = colorama.Style),
			'                        description{s.RESET_ALL}'.format(
				f = colorama.Fore, s = colorama.Style),
			'']),
	])
	def test_assemble(self, helps, expt):
		assert self.assembler.assemble(helps) == expt

# region: test Parameter
def test_parameter_init():
	with pytest.raises(ParameterNameError):
		Parameter(None, 'value')
	with pytest.raises(ParameterNameError):
		Parameter('@1234', 'value')
	with pytest.raises(ParameterTypeError):
		Parameter('name', object())

	param = Parameter('name', None)
	assert param._props == dict(
		desc     = [],
		required = False,
		show     = True,
		type     = None,
		name     = 'name',
		value    = None,
		callback = None
	)

	param = Parameter('name', 'value')
	assert param._props == dict(
		desc     = [],
		required = False,
		show     = True,
		type     = 'str',
		name     = 'name',
		value    = 'value',
		callback = None
	)

	param = Parameter('name', {'value'})
	assert param._props == dict(
		desc     = [],
		required = False,
		show     = True,
		type     = 'list',
		name     = 'name',
		value    = ['value'],
		callback = None
	)
	assert param.name == 'name'

def test_parameter_value():
	param = Parameter('name', None)
	assert param.value is None
	assert param.type is None
	param.value = 1
	assert param.value == 1
	assert param.type is None
	assert param.setValue(2) is param
	assert param.value == 2

def test_parameter_desc():
	param = Parameter('name', None)
	assert param.desc == []

	param.desc = []
	assert param.desc == ['Default: None']

	param.value = 1
	param.setDesc('option description.')
	assert param.desc == ['option description. Default: 1']

def test_parameter_required():
	param = Parameter('name', 'value')
	assert param.required is False
	param.required = True
	assert param.required is True
	param.setRequired(False)
	assert param.required is False
	param.setRequired()
	assert param.required is True
	param.value = 1
	param.type = 'bool'
	with pytest.raises(ParameterTypeError):
		param.setRequired()

def test_parameter_show():
	param = Parameter('name', 'value')
	assert param.show is True
	param.show = False
	assert param.show is False
	param.setShow()
	assert param.show is True
	assert param.setShow(False) is param
	assert param.show is False

def test_parameter_callback():
	param = Parameter('name', 'value')
	assert param.callback is None
	param.callback = lambda: None
	assert callable(param.callback)
	assert param.setCallback(lambda: None) is param
	with pytest.raises(TypeError):
		param.setCallback(1)

def test_parameter_type():
	param = Parameter('name', '1')
	assert param.type == 'str'
	param.type = int
	assert param.type == 'int'
	assert param.value == 1
	assert param.setType(int) is param
	with pytest.raises(ParameterTypeError):
		param.type = tuple

@pytest.mark.parametrize('value, typename, expt', [
	('whatever', None, 'whatever'),
	('1', 'int', 1),
	('1.1', 'float', 1.1),
	('1.0', 'str', '1.0'),
	('1', 'bool', True),
	('0', 'bool', False),
	('none', 'none', None),
	('py:None', 'py', None),
	('repr:None', 'py', None),
	('None', 'py', None),
	('{"a":1}', 'py', {"a":1}),
	('none', 'auto', None),
	('1', 'auto', 1),
	('1.1', 'auto', 1.1),
	('t', 'auto', True),
	('py:1.23', 'auto', 1.23),
	('xyz', 'auto', 'xyz'),
	(1, 'auto', 1),
	('xyz', 'list', ['xyz']),
	({'xyz'}, 'list', ['xyz']),
	(1, 'list', [1]),
	('1', 'list:str', ['1']),
	('1', 'list:one', [['1']]),
	([1,2,3], 'list:one', [[1,2,3]]),
	('', 'dict', {}),
])
def test_parameter_forcetype(value, typename, expt):
	assert Parameter.forceType(value, typename) == expt

@pytest.mark.parametrize('value, typename, exception', [
	('x', 'bool', ParameterTypeError),
	('x', 'none', ParameterTypeError),
	('x', 'x', ParameterTypeError),
	(1, 'dict', ParameterTypeError),
])
def test_parameter_forcetype_exc(value, typename, exception):
	with pytest.raises(exception):
		Parameter.forceType(value, typename)

def test_parameter_repr():
	param = Parameter('name', 'value')
	assert repr(param).startswith(
		"<Parameter(callback=None,desc=[],name='name',required=False,show=True,type='str',value='value') @ ")
# endregion

# region: Parameters
def test_parameters_init():
	import sys
	sys.argv = ['program']
	params = Parameters()
	assert params._prog == 'program'
	assert params._usage == []
	assert params._desc == []
	assert params._hopts == ['-h', '--help', '-H']
	assert params._prefix == '-'
	assert params._hbald == True
	assert params._params == {}
	assert params._assembler.theme['error'] == colorama.Fore.RED
	assert params._helpx == None

	params = Parameters(command = 'list')
	assert params._prog == 'program list'

def test_parameters_props():
	params = Parameters()
	# theme
	params._setTheme('plain')
	assert params._assembler.theme['error'] == ''
	params._theme = 'default'
	assert params._assembler.theme['error'] == colorama.Fore.RED

	# usage
	params._setUsage('a\nb')
	assert params._usage == ['a', 'b']
	params._usage = ['1', '2']
	assert params._usage == ['1', '2']

	# desc
	params._setDesc('a\nb')
	assert params._desc == ['a', 'b']
	params._desc = ['1', '2']
	assert params._desc == ['1', '2']

	# hopts
	params._setHopts('-h, --help')
	assert params._hopts == ['-h', '--help']
	params._hopts = ['-H']
	assert params._hopts == ['-H']

	# prefix
	params._setPrefix('--')
	assert params._prefix == '--'
	params._prefix = '-'
	assert params._prefix == '-'
	with pytest.raises(ParametersParseError):
		params._prefix = ''

	# hbald
	params._setHbald()
	assert params._hbald is True
	params._hbald = False
	assert params._hbald is False

def test_parameters_attr():
	# use singleton
	params.__file__ = None
	assert params.__file__ is None
	params.b = Parameter('b', None)
	assert isinstance(params.b, Parameter)
	params.b = 1
	assert params.b.value == 1
	params.a = 1
	assert isinstance(params.a, Parameter)
	params['c'] = 1
	assert isinstance(params['c'], Parameter)

def test_parameters_repr():
	params = Parameters()
	params.a = 1
	params.b = 2
	assert repr(params).startswith('<Parameters(a:int,b:int) @ ')

# endregion