import unittest
import sys
import os
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import strtpl

class TestStrtpl (unittest.TestCase):

	def testSplit (self):
		data = [
			("a|b|c", ["a", "b", "c"]),
			('a|b\|c', ["a", "b\\|c"]),
			('a|b\|c|(|)', ["a", "b\\|c", "(|)"]),
			('a|b\|c|(\)|)', ["a", "b\\|c", "(\\)|)"]),
			('a|b\|c|(\)\\\'|)', ["a", "b\\|c", "(\\)\\'|)"]),
		]
		for d in data:
			self.assertEqual (strtpl.split(d[0], "|"), d[1])

	def testFormat (self):
		data = [
			("The directory is: {{path | __import__('os').path.dirname(_)}}", "The directory is: /a/b", {"path": "/a/b/c.txt"}),
			("The directory is: {{path | __import__('os').path.dirname(_)}}", "The directory is: ../c/d", {"path": "../c/d/x.txt"}),
			("{{v | .upper()}}", "HELLO", {"v": "hello"}),
			("{{v | .find('|')}}", '3', {"v": "hel|lo"}),
			("{{v | len(_)}}", '5', {"v": "world"}),
			("{{v | (lambda x: x[0].upper() + x[1:])(_)}}", "World", {"v": "world"}),
			("{{v | .upper() | (lambda x: x+'_suffix')(_)}}", "HELLO_suffix", {"v": "hello"}),
			("{{v | .upper() | [2:]}}", "LLO", {"v": "hello"}),
			("{{c2 | __import__('math').pow(_, 2.0) }}", '4.0', {"c2": 2}),
			("{{genefile.fn | .split('_') | [1] }}", '4', {"genefile.fn": "gene_4"}),
			("{{genefile.fn | .split('_')[0] }}", 'gene', {"genefile.fn": "gene_4"}),
			("{{v | sum(_)}}", "10", {"v": [1,2,3,4]}),
			("{{v | map(str, _) | (lambda x: '_'.join(x))(_)}}", "1_2_3_4", {"v": [1,2,3,4]}),
			("{{v | (lambda x: x['a'] if x.has_key('a') else '')(_)}}", '1', {"v": {"a": 1, "b": 2}}),
			("{{v | __import__('json').dumps(_)}}", '{"a": 1, "b": 2}', {"v": {"a": 1, "b": 2}}),
		]
		for d in data:
			self.assertEqual (strtpl.format(d[0], d[2]), d[1])


if __name__ == '__main__':
	unittest.main()
