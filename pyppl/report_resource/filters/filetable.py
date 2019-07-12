"""
Panflute filter to parse CSV in fenced YAML code blocks

```table
---
caption    : An awesome table
file       : /path/to/csv/tsv/file
header     : True
width      : 1
total_width: .8
align      : default
rows       : 10
cols       : 0
csvargs    :
	dialect: unix
	delimiter: "\t"
	quotechar: null
---
```
"""

import io
import csv
import panflute as pf

def fenced_action(options, data, element, doc):
	# We'll only run this for CodeBlock elements of class 'table'
	caption     = options.get('caption', 'Untitled Table')
	caption     = [pf.Str(caption)]
	filepath    = options['file']
	has_header  = options.get('header', True)
	width       = options.get('width', 1)
	total_width = float(options.get('total_width', .8))
	align       = options.get('align', 'default')
	nrows       = options.get('rows', 0)
	ncols       = options.get('cols', 0)
	csvargs     = options.get('csvargs', {})

	csvargs['dialect'] = csvargs.get('dialect', "unix")
	csvargs['delimiter'] = csvargs.get('delimiter', "\t")

	with open(filepath) as f:
		reader = csv.reader(f, **csvargs)
		body = []
		for i, row in enumerate(reader):
			if nrows and i > nrows + 1:
				continue
			cells = [pf.TableCell(pf.Plain(pf.Str(x)))
				for k, x in enumerate(row) if not ncols or k < ncols]
			body.append(pf.TableRow(*cells))

	ncols = len(row)
	if has_header:
		header = body.pop(0)
	elif nrows:
		body = body[:nrows]

	if not isinstance(width, list):
		width = [width]
	if len(width) == 1 and ncols:
		width = width * ncols
	sumwidth    = float(sum(width))
	total_width = min(total_width, 1)
	width       = [float(wid)*float(total_width)/sumwidth for wid in width]

	if not isinstance(align, list):
		align = [align]
	if len(align) == 1 and ncols:
		align = align * ncols
	align = ['Align' + al.capitalize() for al in align]

	table = pf.Table(*body,
		header=header, caption=caption, width=width, alignment = align)
	return pf.Div(table, classes = ['table-responsive'])

def main(doc=None):
	return pf.run_filter(pf.yaml_filter, tag='table', function=fenced_action, doc=doc)

if __name__ == '__main__':
	main()