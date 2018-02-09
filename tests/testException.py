import helpers, unittest

from pyppl.exception import TemplatePyPPLSyntaxMalformKeyword, TemplatePyPPLSyntaxDotError, TemplatePyPPLSyntaxNameError, TemplatePyPPLSyntaxUnclosedTag, TemplatePyPPLSyntaxNewline, TemplatePyPPLRenderError

class TestException(helpers.TestCase):

	def dataProvider_testInit(self):
		yield TemplatePyPPLSyntaxMalformKeyword('', ''), TemplatePyPPLSyntaxMalformKeyword
		yield TemplatePyPPLSyntaxDotError('', ''), TemplatePyPPLSyntaxDotError
		yield TemplatePyPPLSyntaxNameError('', ''), TemplatePyPPLSyntaxNameError
		yield TemplatePyPPLSyntaxUnclosedTag(''), TemplatePyPPLSyntaxUnclosedTag
		yield TemplatePyPPLSyntaxNewline(''), TemplatePyPPLSyntaxNewline
		yield TemplatePyPPLRenderError('', ''), TemplatePyPPLRenderError

	def testInit(self, exc, Exc, Super = Exception):
		self.assertIsInstance(exc, Exc)
		self.assertIsInstance(exc, Super)

	def dataProvider_testRaise(self):
		yield TemplatePyPPLSyntaxMalformKeyword('a', 'b'), TemplatePyPPLSyntaxMalformKeyword, 'Cannot understand "a" in b'
		yield TemplatePyPPLSyntaxDotError('a', 'b'), TemplatePyPPLSyntaxDotError, 'Cannot find an attribute/subscribe/index named "b" for "a"'
		yield TemplatePyPPLSyntaxNameError('a', 'b'), TemplatePyPPLSyntaxNameError, 'Invalid variable name "a" in "b"'
		yield TemplatePyPPLSyntaxUnclosedTag('a'), TemplatePyPPLSyntaxUnclosedTag, 'Unclosed template tag: a'
		yield TemplatePyPPLSyntaxNewline('a'), TemplatePyPPLSyntaxNewline, 'No newline is allowed in block: a'
		yield TemplatePyPPLRenderError('a', 'b'), TemplatePyPPLRenderError, 'a, b'

	def testRaise(self, exc, Exc, msg):
		def raise_exc():
			raise exc
		self.assertRaisesRegex(Exc, msg, raise_exc)

if __name__ == '__main__':
	unittest.main(verbosity=2)