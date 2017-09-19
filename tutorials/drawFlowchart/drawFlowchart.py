from pyppl import PyPPL, Proc

p1 = Proc()
p2 = Proc()
p3 = Proc()
p4 = Proc()
p5 = Proc()
p6 = Proc()
p7 = Proc()
p8 = Proc()
p9 = Proc()
"""
		   p1         p8
		/      \      /
	 p2           p3
		\      /
		   p4         p9
		/      \      /
	 p5          p6 (export)
		\      /
		  p7 (expart)
"""
p2.depends = p1
p3.depends = p1, p8
p4.depends = p2, p3
p4.exdir   = "./export"
p5.depends = p4
p6.depends = p4, p9
p6.exdir   = "./export"
p7.depends = p5, p6
p7.exdir   = "./export"

# make sure at least one job is created.
p1.input = {"in": [0]}
p8.input = {"in": [0]}
p9.input = {"in": [0]}

PyPPL().start(p1, p8, p9).flowchart().run()