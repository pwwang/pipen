import testly

from pyppl import Proc, ProcTree
from pyppl.exception import TemplatePyPPLSyntaxError, TemplatePyPPLRenderError, LoggerThemeError, ParameterNameError, ParameterTypeError, ParametersParseError, ParametersLoadError, ProcTreeProcExists, ProcTreeParseError, JobInputParseError, JobOutputParseError, RunnerSshError, ProcTagError, ProcAttributeError, ProcInputError, ProcOutputError, ProcScriptError, ProcRunCmdError, PyPPLProcFindError, PyPPLProcRelationError, PyPPLConfigError, AggrAttributeError, AggrCopyError

class TestException(testly.TestCase):

	def dataProvider_testInit(self):
		yield TemplatePyPPLSyntaxError('', ''), TemplatePyPPLSyntaxError
		yield TemplatePyPPLRenderError('', ''), TemplatePyPPLRenderError
		yield LoggerThemeError('', ''), LoggerThemeError
		yield ParameterNameError(''), ParameterNameError
		yield ParameterTypeError(''), ParameterTypeError
		yield ParametersParseError('', ''), ParametersParseError
		yield ParametersLoadError('', ''), ParametersLoadError
		p1 = Proc()
		p2 = Proc()
		yield ProcTreeProcExists(ProcTree.NODES[p1], ProcTree.NODES[p2]), ProcTreeProcExists
		yield ProcTreeParseError('', ''), ProcTreeParseError
		yield JobInputParseError('', ''), JobInputParseError
		yield JobOutputParseError('', ''), JobOutputParseError
		yield RunnerSshError(''), RunnerSshError
		yield ProcTagError(''), ProcTagError
		yield ProcAttributeError('', ''), ProcAttributeError
		yield ProcInputError('', ''), ProcInputError
		yield ProcOutputError('', ''), ProcOutputError
		yield ProcScriptError('', ''), ProcScriptError
		yield ProcRunCmdError('', ''), ProcRunCmdError
		yield PyPPLProcFindError('', ''), PyPPLProcFindError
		yield PyPPLProcRelationError('', ''), PyPPLProcRelationError
		yield PyPPLConfigError('', ''), PyPPLConfigError
		yield AggrAttributeError('', ''), AggrAttributeError
		yield AggrCopyError('', ''), AggrCopyError
		
	def testInit(self, exc, Exc, Super = Exception):
		self.assertIsInstance(exc, Exc)
		self.assertIsInstance(exc, Super)

if __name__ == '__main__':
	testly.main(verbosity=2)