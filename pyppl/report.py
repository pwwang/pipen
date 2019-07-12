"""Report generating system using pandoc"""
import re
from cmdy import pandoc
from pathlib import Path

RESOURCE_DIR     = Path(__file__).resolve().parent / 'report_resource'
DEFAULT_FILTERS  = ['filetable']
DEFAULT_TEMPLATE = 'bootstrap'

def _replaceAll(regex, callback, string):
	matches = re.findall(regex, string)
	for match in matches:
		rep = callback(match)
		if rep is not None:
			string = string.replace(match, rep)
	return string

class ProcReport:

	def __init__(self, rptfile):
		self.rptfile   = Path(rptfile)
		self.source, self.appendix = self._analysis()

	def _analysis(self):
		"""Get the citations and appendix"""
		lines = self.rptfile.read_text().splitlines()
		# get the references first
		# references should be placed at the bottom
		source   = None
		appendix = None
		citations = {}
		for line in lines:
			line = line.rstrip('\n')
			if line.startswith('## Appendix'):
				appendix = []
			else:
				matched = re.match(r'\[(\d+)\]: (.+)', line)
				if matched:
					citations[matched.group(1)] = matched.group(2).strip()
				elif appendix is None:
					source = source or []
					source.append(line)
				else:
					appendix.append(line)

		# replace all citation marks with real references
		def replace(m):
			index = m[1:-1]
			if index not in citations:
				return None
			return '[#REF: %s #]' % citations[index]

		source = source and '\n'.join(source) or ''
		source = _replaceAll(r'\[\d+\]', replace, source)

		appendix = appendix and '\n'.join(appendix) or ''
		appendix = _replaceAll(r'\[\d+\]', replace, appendix)

		return source, appendix

class Report:

	def __init__(self, rptfiles, outfile, title):
		self.reports = [ProcReport(rptfile) for rptfile in rptfiles]
		self.outfile = Path(outfile)
		self.mdfile  = self.outfile.with_suffix('.md')
		self.title   = title
		self.cleanup()

	def cleanup(self):
		citations = {}
		def replace(m):
			cite = m[7:-3]
			if cite not in citations:
				citations[cite] = len(citations) + 1
			return '<sup><a href="#REF_{i}">[{i}]</a></sup>'.format(i = citations[cite])

		with self.mdfile.open('w') as fmd:
			fmd.write('# %s\n\n' % self.title)
			appendix = ''
			for report in self.reports:
				# replace reference to citation indexes
				source = _replaceAll(r'\[#REF: .+? #\]', replace, report.source)
				if report.appendix:
					appendix += _replaceAll(r'\[#REF: .+? #\]', replace, report.appendix)

				fmd.write(source + '\n\n')

			if appendix:
				fmd.write('## Appendix\n')
				fmd.write(appendix + '\n\n')

			if citations:
				fmd.write('## Reference\n')
				for cite, index in sorted(citations.items(), key = lambda item: item[1]):
					fmd.write('<a name="REF_{i}" class="reference">**[{i}]** {cite}</a>'.format(
						i=index, cite=cite))

	def generate(self, standalone, template, filters):
		template = template or DEFAULT_TEMPLATE
		if template and '/' not in template:
			template = RESOURCE_DIR / 'templates' / template / 'standalone.html'
		return pandoc(
			self.mdfile,
			metadata = 'pagetitle="%s"' % self.title,
			read     = 'markdown',
			write    = 'html',
			template = template,
			filter   = [RESOURCE_DIR / 'filters' / (filt + '.py')
				for filt in DEFAULT_FILTERS] + (filters or []),
			toc      = True,
			output   = self.outfile,
			_sep     = 'auto',
			**{ 'toc-depth': 2,
				'self-contained': standalone,
				'tab-stop': 4,
				'resource-path': Path(template).parent})
