import pytest
import colorama
from pyppl.parameters2 import HelpAssembler, MAXPAGEWIDTH, MAXOPTWIDTH

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