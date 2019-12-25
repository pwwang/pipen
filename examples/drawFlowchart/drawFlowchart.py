from sys import argv
from pyppl import PyPPL, Proc

p1 = Proc(input = {"in": [0]}, output = "out:var:1")
p2 = Proc(input = {"in": [0]}, output = "out:var:1")
p3 = Proc(input = {"in": [0]}, output = "out:var:1")
p4 = Proc(input = {"in": [0]}, output = "out:var:1")
p5 = Proc(input = {"in": [0]}, output = "out:var:1")
p6 = Proc(input = {"in": [0]}, output = "out:var:1")
p7 = Proc(input = {"in": [0]}, output = "out:var:1")
p8 = Proc(input = {"in": [0]}, output = "out:var:1")
p9 = Proc(input = {"in": [0]}, output = "out:var:1")
"""
		   p1         p8
		/      \      /
	 p2        (  p3 : hide )
		\      /
		   p4         p9
		/      \      /
	 p5          p6 (export)
		\      /
		  p7 (expart)
"""
p2.depends = p1
p3.depends = p1, p8
p3.plugin_config.flowchart_hide = True
p4.depends = p2, p3
p5.depends = p4
p6.depends = p4, p9
p7.depends = p5, p6

if len(argv) > 1:
	PyPPL(flowchart_theme = 'dark').start(p1, p8, p9).flowchart().run()
else:
	PyPPL().start(p1, p8, p9).flowchart().run()